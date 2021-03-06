import math
import numpy as np
import os
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import random
import gym
import copy
import numpy as np


from common.past.utils import *
from common.ours.grid.utils import Goal_Space, Cost_Space

from common.past.multiprocessing_envs import SubprocVecEnv
from torchvision.transforms import ToTensor

from models.ours.grid_model import OneHotDQN, OneHotValueNetwork, OneHotCostAllocator

from common.past.schedules import LinearSchedule, ExponentialSchedule

# we define goal action space as follows: for each goal what are the corresponding values for all cost. Then goes on
#its like g1c1, g1c2, g1c3, g2c1, g2c2, g2c3
def get_cost(index, cost_dim, C, device, upper_cost):

    cost_index = index
    cost = C.get_cost_weight(cost_index)*upper_cost
    cost_weight = C.get_cost_weight(cost_index)


    cost = torch.LongTensor(np.array([cost])).unsqueeze(1).to(device)

    return cost, cost_weight


class HRL_Discrete_Safe_Lower_Cost_Allocation_Only(object):

    def __init__(self,
                 args,
                 env,
                 goal_space=None,
                 cost_space = None,
                 cost_mapping = None,
                 writer = None,
                 save_dir=None,
                 exp_no=None
                 ):
        """
        init the agent here
        """
        self.exp_no = exp_no
        self.save_dir = save_dir
        args.num_envs = 1
        if goal_space == None:
            goal_space = args.goal_space


        if cost_space == None:
            cost_space = args.cost_space


        if cost_mapping == None:
            cost_mapping = args.cost_mapping


        self.r_path = save_dir + "r" + exp_no
        self.c_path = save_dir + "c" + exp_no

        self.EVAL_REWARDS = []
        self.EVAL_CONSTRAINTS = []

        self.TRAIN_REWARDS = []
        self.TRAIN_CONSTRAINTS = []



        self.args = args

        #for the time being let's skip the vectorized environment's added complexity in HRL
        self.env = env

        self.G = Goal_Space(goal_space=goal_space, grid_size=self.env.size)
        self.C = Cost_Space(cost_space=cost_space, cost_mapping=cost_mapping)

        self.grid_size = self.env.size

        c = []
        for i in goal_space:
            c.append(self.G.convert_value_to_coordinates(i))
        print(c)

        self.eval_env = copy.deepcopy(env)


        s = env.reset()
        self.state_dim = s.shape
        self.action_dim = env.action_space.n

        self.goal_dim = self.G.action_shape[0]
        self.goal_state_dim = np.concatenate((s,s)).shape

        self.cost_dim = self.C.cost_shape[0]
        self.cost_goal_dim = self.cost_dim*self.goal_dim



        self.device = torch.device("cuda" if (torch.cuda.is_available() and  self.args.gpu) else "cpu")

        # set the same random seed in the main launcher
        random.seed(self.args.seed)
        torch.manual_seed(self.args.seed)
        np.random.seed(self.args.seed)
        if self.args.gpu:
            torch.cuda.manual_seed(self.args.seed )

        self.writer = writer

        if self.args.env_name == "grid" or self.args.env_name == "grid_key":
            self.dqn_meta = OneHotDQN(self.state_dim, self.cost_dim).to(self.device)

            self.dqn_lower = OneHotDQN(self.state_dim, self.action_dim).to(self.device)

            # create more networks for lower level
            self.cost_lower_model = OneHotDQN(self.state_dim, self.action_dim).to(self.device)
            self.review_lower_model = OneHotValueNetwork(self.state_dim).to(self.device)


        else:
            raise Exception("not implemented yet!")



        self.optimizer_meta = torch.optim.Adam(self.dqn_meta.parameters(), lr=self.args.lr)
        self.optimizer_lower = torch.optim.Adam(self.dqn_lower.parameters(), lr=self.args.lr)
        #for cost value function
        self.review_lower_optimizer = optim.Adam(self.review_lower_model.parameters(), lr=self.args.cost_reverse_lr)
        # for cost q function
        self.critic_lower_optimizer = optim.Adam(self.cost_lower_model.parameters(),lr=self.args.cost_q_lr)


        self.total_steps = 0
        self.total_lower_time_steps = 0
        self.total_meta_time_steps = 0
        self.num_episodes = 0
        #50000
        #different epsilon for different levels
        self.eps_u_decay = LinearSchedule(500000 * 200, 0.01, 1.0)
        self.eps_l_decay = LinearSchedule(500000 * 200, 0.01, 1.0)

        #decide on weather to use total step or just the meta steps for this annealing
        self.eps_u = self.eps_u_decay.value(self.total_steps)
        self.eps_l = self.eps_l_decay.value(self.total_lower_time_steps)

        # for storing resutls
        self.results_dict = {
            "train_rewards" : [],
            "train_constraints" : [],
            "eval_rewards" : [],
            "eval_constraints" : [],
        }

        self.cost_indicator = "none"
        if "grid" in self.args.env_name:
            self.cost_indicator = 'pit'
        else:
            raise Exception("not implemented yet")

    def pi_meta(self, state, greedy_eval=False):
        """
        choose goal based on the current policy
        """
        with torch.no_grad():

            self.eps_u = self.eps_u_decay.value(self.total_steps)
            # to choose random goal or not
            if (random.random() > self.eps_u) or greedy_eval:
                q_value = self.dqn_meta(state)

                # chose the max/greedy actions
                goal = np.array([q_value.max(0)[1].cpu().numpy()])
            else:
                goal = np.random.randint(0, high=self.cost_dim, size = (self.args.num_envs, ))

        return goal

    def pi_lower(self, state, greedy_eval=False):
        """
        take the action based on the current policy
        """


        self.eps_l = self.eps_l_decay.value(self.total_lower_time_steps)
        with torch.no_grad():
            # to take random action or not
            if (random.random() > self.eps_l) or greedy_eval:
                q_value = self.dqn_lower(state)
                # chose the max/greedy actions
                action = np.array([q_value.max(0)[1].cpu().numpy()])

                #print(action)
                #print("action_greedy")
            else:
                action = np.random.randint(0, high=self.action_dim, size = (self.args.num_envs, ))
                #print(action)
                #print("action_random")
        return action

    def safe_deterministic_pi_lower(self, state, d_low, current_cost=0.0, greedy_eval=False):
        """
        take the action based on the current policy
        d_low: cost allocated for the current low level episode
        """


        with torch.no_grad():
            # to take random action or not
            self.eps_l = self.eps_l_decay.value(self.total_lower_time_steps)
            if (random.random() > self.eps_l) or greedy_eval:
                # No random action
                q_value = self.dqn_lower(state)

                # Q_D(s,a)
                cost_q_val = self.cost_lower_model(state)
                cost_r_val = self.review_lower_model(state)

                # find the action set
                # create the filtered mask here
                constraint_mask = torch.le(cost_q_val + cost_r_val, d_low + current_cost).float().squeeze(0)

                filtered_Q = (q_value + 1000.0) * (constraint_mask)

                filtered_action = np.array([filtered_Q.max(0)[1].cpu().numpy()])
                # alt action to take if infeasible solution
                # minimize the cost
                alt_action = np.array([(-1. * cost_q_val).max(0)[1].cpu().numpy()])

                c_sum = constraint_mask.sum(0)
                action_mask = ( c_sum == torch.zeros_like(c_sum)).cpu().numpy()

                action = (1 - action_mask) * filtered_action + action_mask * alt_action

                return action

            else:
                # create an array of random indices, for all the environments
                action = np.random.randint(0, high=self.action_dim, size = (self.args.num_envs, ))

        return action

    def compute_n_step_returns(self, next_value, rewards, masks):
        """
        n-step SARSA returns
        """
        R = next_value
        returns = []
        for step in reversed(range(len(rewards))):
            R = rewards[step] + self.args.gamma * R * masks[step]
            returns.insert(0, R)

        return returns

    def compute_reverse_n_step_returns(self, prev_value, costs, begin_masks):
        """
        n-step SARSA returns (backward in time)
        """
        R = prev_value
        returns = []
        for step in range(len(costs)):
            R = costs[step] + self.args.gamma * R * begin_masks[step]
            returns.append(R)

        return returns

    def log_episode_stats(self, ep_reward, ep_constraint):
        """
        log the stats for environment performance
        """
        # log episode statistics
        self.TRAIN_REWARDS.append(ep_reward)
        self.TRAIN_CONSTRAINTS.append(ep_constraint)



        log(
            'Num Episode {}\t'.format(self.num_episodes) + \
            'avg_train_reward: {:.2f}\t'.format(np.mean(self.TRAIN_REWARDS[-100:])) +\
            'avg_train_constraint: {:.2f}\t'.format(np.mean(self.TRAIN_CONSTRAINTS[-100:]))
            )
        #'E[R]: {:.2f}\t'.format(ep_reward) +\
        #'E[C]: {:.2f}\t'.format(ep_constraint) +\

    def run(self):
        """
        Learning happens here
        """
        self.total_steps = 0
        self.total_lower_time_steps = 0
        self.total_meta_time_steps = 0
        self.eval_steps = 0

        # reset state and env
        # reset exploration porcess
        state = self.env.reset()
        state = torch.FloatTensor(state).to(device=self.device)
        previous_state = state





        #total episode reward, length for logging purposes
        self.ep_reward = 0
        self.ep_len = 0
        self.ep_constraint = 0
        start_time = time.time()


        while self.num_episodes < self.args.num_episodes:

            upper_cost_constraint = torch.zeros(self.args.num_envs).float().to(self.device)
            upper_cost_constraint[0] = self.args.d0
            lower_cost_constraint = torch.zeros(self.args.num_envs).float().to(self.device)
            current_cost = torch.zeros(self.args.num_envs, 1).float().to(self.device)


            #upper_cost_constraint[0] = self.args.d0

            next_state = None
            done = None

            states_u      = []
            actions_u     = []


            rewards     = []
            done_masks  = []
            constraints = []

            IR_t = []
            Goals_t = []
            Cost_Lower_t = []
            CS_t = []
            T_t = []
            Cost_Alloc = []

            t_upper = 0
            while not done:
                values_upper = []
                rewards_upper = []
                done_masks = []



                t_upper += 1


                #given the current top level constraint this should now allocate constraint weights accordingly
                #state_cost = torch.cat((state, upper_cost_constraint.detach()))

                #cost_weight = self.cost_allocator(state_cost)
                #lower_cost_constraint = cost_weight[1] * (upper_cost_constraint.detach())
                #upper_cost_constraint = cost_weight[0] * (upper_cost_constraint.detach())

                #Cost_Alloc.append((lower_cost_constraint.item(), upper_cost_constraint.item()))


                cost = self.pi_meta(state=state)
                lower_cost_constraint, cost_weight = get_cost(index=cost[0], cost_dim=self.cost_dim, C=self.C,
                                                            device=self.device, upper_cost=upper_cost_constraint.item())

                upper_cost_constraint = (1-cost_weight)*upper_cost_constraint

                Cost_Lower_t.append((lower_cost_constraint, cost_weight, upper_cost_constraint))

                cost = torch.LongTensor(cost).unsqueeze(1).to(self.device)

                q_values_upper = self.dqn_meta(state)
                Q_value_upper = q_values_upper.gather(0, cost[0])

                #an indicator that is used to terminate the lower level episode
                t_lower = 0

                eps_reward_lower = 0
                R = 0


                while t_lower <= self.args.max_ep_len_l-1:

                    instrinc_rewards = []  # for low level n-step
                    values_lower     = []
                    done_masks_lower = []
                    constraints_lower = []
                    begin_mask_lower = []
                    cost_q_lower = []
                    cost_r_lower = []
                    prev_states_l = []



                    for n_l in range(self.args.traj_len_l):
                        action = self.safe_deterministic_pi_lower(state=state, d_low=lower_cost_constraint.detach(), current_cost=current_cost)

                        next_state, reward, done, info = self.env.step(action=action.item())


                        if t_lower == 0:
                            begin_mask_l = True
                        else:
                            begin_mask_l = False



                        next_state = torch.FloatTensor(next_state).to(self.device)
                        done_l = self.G.validate_done(current_state=next_state)  #this is to validate the end of the lower level episode
                        instrinc_reward = self.G.find_shortest_goal_reward(next_state)
                        #print(action)
                        action = torch.LongTensor(action).unsqueeze(1).to(self.device)
                        #print(action, torch.LongTensor(action))
                        current_cost = torch.FloatTensor([info[self.cost_indicator] * (1.0 - done)]).unsqueeze(1).to(self.device)

                        R += reward

                        #for training logging purposes
                        self.ep_len += 1
                        self.ep_constraint += info[self.cost_indicator]
                        self.ep_reward += reward


                        q_values_lower = self.dqn_lower(state=state)
                        Q_value_lower = q_values_lower.gather(0, action[0])

                        cost_values_lower = self.cost_lower_model(state=state)
                        Cost_value = cost_values_lower.gather(0, action[0])
                        Review_value_lower = self.review_lower_model(state=state)


                        values_lower.append(Q_value_lower)
                        instrinc_rewards.append(instrinc_reward)
                        done_masks_lower.append((1 - done_l))
                        constraints_lower.append(info[self.cost_indicator])
                        begin_mask_lower.append((1-begin_mask_l))
                        cost_q_lower.append(Cost_value)
                        cost_r_lower.append(Review_value_lower)

                        t_lower += 1
                        self.total_steps += 1
                        self.total_lower_time_steps += 1

                        previous_state = state
                        state = next_state

                        prev_states_l.append(previous_state)

                        #break if goal is current_state or the if the main episode terminated
                        if done or done_l:
                            break

                        if t_lower > self.args.max_ep_len_l-1:
                            break



                    x_c, y_c = self.G.convert_value_to_coordinates(self.G.convert_hot_vec_to_value(next_state).item())



                    #next_state_goal_cost = torch.cat((torch.cat((next_state, goal_hot_vec)), lower_cost_constraint.detach()))

                    next_action = self.safe_deterministic_pi_lower(state=next_state, d_low=lower_cost_constraint.detach(), current_cost=current_cost)
                    next_action = torch.LongTensor(next_action).unsqueeze(1).to(self.device)

                    #update Reward Q value function

                    next_values = self.dqn_lower(next_state)
                    Next_Value = next_values.gather(0, next_action[0])

                    target_Q_values_lower = self.compute_n_step_returns(Next_Value, instrinc_rewards, done_masks_lower)
                    Q_targets_lower = torch.cat(target_Q_values_lower).detach()
                    Q_values_lower = torch.cat(values_lower)

                    loss_lower = F.mse_loss(Q_values_lower, Q_targets_lower)

                    self.optimizer_lower.zero_grad()
                    loss_lower.backward()
                    self.optimizer_lower.step()

                    #update cost Q value function
                    next_c_value = self.cost_lower_model(next_state)
                    Next_c_value = next_c_value.gather(0, next_action[0])

                    cq_targets = self.compute_n_step_returns(Next_c_value, constraints_lower, done_masks_lower)
                    C_q_targets = torch.cat(cq_targets).detach()
                    C_q_vals = torch.cat(cost_q_lower)

                    cost_critic_loss_lower = F.mse_loss(C_q_vals, C_q_targets)
                    self.critic_lower_optimizer.zero_grad()
                    cost_critic_loss_lower.backward()
                    self.critic_lower_optimizer.step()

                    # For the constraints (reverse)
                    previous_state = prev_states_l[0]
                    prev_value = self.review_lower_model(previous_state)


                    c_r_targets = self.compute_reverse_n_step_returns(prev_value, constraints_lower, begin_mask_lower)
                    C_r_targets = torch.cat(c_r_targets).detach()
                    C_r_vals = torch.cat(cost_r_lower)

                    cost_review_loss = F.mse_loss(C_r_vals, C_r_targets)
                    self.review_lower_optimizer.zero_grad()
                    cost_review_loss.backward()
                    self.review_lower_optimizer.step()



                    if done:
                        break




                #prev_states_u.append(previous_state)

                values_upper.append(Q_value_upper)
                rewards_upper.append(R)
                done_masks.append((1 - done))

                CS_t.append((x_c, y_c))
                T_t.append(t_lower)

                #next_state_cost = torch.cat((next_state, upper_cost_constraint.detach()))

                next_goal = self.pi_meta(next_state)
                next_goal = torch.LongTensor(next_goal).unsqueeze(1).to(self.device)
                next_values = self.dqn_meta(next_state)
                Next_Value = next_values.gather(0, next_goal[0])

                target_Q_values_upper = self.compute_n_step_returns(Next_Value, rewards_upper, done_masks)
                Q_targets_upper = torch.cat(target_Q_values_upper).detach()
                Q_values_upper = torch.cat(values_upper)

                loss_upper = F.mse_loss(Q_values_upper, Q_targets_upper)
                self.optimizer_meta.zero_grad()
                loss_upper.backward()
                self.optimizer_meta.step()

                """

                #NEED to optimze for cost allocator
                ###################################################################
                initial_state_cost = torch.cat((initial_state_for_CA, upper_cost_constraint))
                initial_state_goal_cost = torch.cat((torch.cat((initial_state_for_CA, goal_hot_vec)), lower_cost_constraint))

                q_upper = self.dqn_meta(initial_state_cost)
                q_lower = self.dqn_lower(initial_state_goal_cost)

                initial_action = self.safe_deterministic_pi_lower(initial_state_for_CA, goal_hot_vec, lower_cost_constraint, lower_cost_constraint)
                initial_action = torch.LongTensor(initial_action).unsqueeze(1).to(self.device)

                Q_upper = q_upper.gather(0, goal[0])
                Q_lower = q_lower.gather(0, initial_action[0])

                cost_allocator_loss = -(0.3*Q_upper + Q_lower)

                self.cost_allocator_optimizer.zero_grad()
                cost_allocator_loss.backward()
                self.cost_allocator_optimizer.step()
                """
                if done:



                    #training logging
                    if self.num_episodes % 100 == 0:
                        self.log_episode_stats(ep_reward=self.ep_reward, ep_constraint=self.ep_constraint)

                    if self.num_episodes % 500 == 0:
                        log("Goal State: "  + " " + str(Goals_t) + " Current State: " + str(CS_t) + " Lower Cost: " + str(Cost_Lower_t))
                        log("No of Higher Eps: " +  str(len(Goals_t)) + " No of lower eps: " + str(T_t)  + " Cost Allocation(future, lower) " + str(Cost_Alloc))

                    #evaluation logging
                    if self.num_episodes % self.args.eval_every == 0:
                        self.save() #save models

                        eval_reward, eval_constraint, IR, Goals, CS = self.eval()

                        print("Epsilon Upper and Lower:" + str(self.eps_u) +", " + str(self.eps_l))

                        self.EVAL_REWARDS.append(eval_reward)
                        self.EVAL_CONSTRAINTS.append(eval_constraint)

                        torch.save(self.EVAL_REWARDS, self.r_path)
                        torch.save(self.EVAL_CONSTRAINTS, self.c_path)

                        log('--------------------------------------------------------------------------------------------------------')
                        log("Intrisic Reward: " + str(IR) + " Goal: " + str(Goals) + " Current State: " + str(CS))
                        log(
                            'Episode: {}\t'.format(self.num_episodes) + \
                            'avg_eval_reward: {:.2f}\t'.format(np.mean(self.EVAL_REWARDS[-10:])) + \
                            'avg_eval_constraint: {:.2f}\t'.format(np.mean(self.EVAL_CONSTRAINTS[-10:]))
                            )
                        log('--------------------------------------------------------------------------------------------------------')
                    """
                    'Eval[R]: {:.2f}\t'.format(eval_reward) + \
                    'Eval[C]: {}\t'.format(eval_constraint) + \
                    """

                    self.num_episodes += 1

                    # resting episode rewards
                    self.ep_reward = 0
                    self.ep_len = 0
                    self.ep_constraint = 0

                    state = self.env.reset() #reset
                    state = torch.FloatTensor(state).to(device=self.device)
                    break #this break is to terminate the higher tier episode as the episode is now over




    def eval(self):
        """
                    evaluate the current policy and log it
                    """

        avg_reward = []
        avg_constraint  = []

        state = self.eval_env.reset()
        state = torch.FloatTensor(state).to(self.device)
        previous_state = state
        done = False
        ep_reward = 0
        ep_constraint = 0
        ep_len = 0
        start_time = time.time()

        IR = []
        Goals = []
        CS = []

        upper_cost_constraint = torch.zeros(self.args.num_envs).float().to(self.device)
        upper_cost_constraint[0] = self.args.d0
        lower_cost_constraint = torch.zeros(self.args.num_envs).float().to(self.device)
        current_cost = torch.zeros(self.args.num_envs, 1).float().to(self.device)

        while not done:

            # convert the state to tensor

            # get the goal
            cost = self.pi_meta(state=state, greedy_eval=True)
            lower_cost_constraint, cost_weight = get_cost(index=cost[0], cost_dim=self.cost_dim, C=self.C,
                                                        device=self.device, upper_cost=upper_cost_constraint)

            upper_cost_constraint = (1-cost_weight)*upper_cost_constraint

            cost = torch.LongTensor(cost).unsqueeze(1).to(self.device)



            t_lower = 0
            ir = 0
            while t_lower <= self.args.max_ep_len_l-1:

                action = self.safe_deterministic_pi_lower(state=state, d_low=lower_cost_constraint.detach(), current_cost=current_cost, greedy_eval=True)
                # print(torch.equal(state, previous_state), self.G.convert_hot_vec_to_value(state), self.G.convert_hot_vec_to_value(goal_hot_vec))
                # print(self.dqn_lower(torch.cat((state, goal_hot_vec))), t_lower)

                next_state, reward, done, info = self.eval_env.step(action.item())
                ep_reward += reward
                ep_len += 1
                ep_constraint += info[self.cost_indicator]

                """
                NS = []
                for i in range(4):
                    NS.append(self.eval_env.step(i)[0])

                T = []
                for ts in NS:
                    T.append(torch.equal(state, torch.FloatTensor(ts)))
                print(T)
                """
                next_state = torch.FloatTensor(next_state).to(self.device)

                # update the state
                previous_state = state
                state = next_state

                current_cost = torch.FloatTensor([info[self.cost_indicator] * (1.0 - done)]).unsqueeze(1).to(self.device)

                instrinc_reward = self.G.find_shortest_goal_reward(current_state=next_state)
                ir += instrinc_reward
                t_lower += 1

                done_l = self.G.validate_done(current_state=next_state)
                if done_l or done:
                    break

            IR.append(ir)

            x_c, y_c = self.G.convert_value_to_coordinates(self.G.convert_hot_vec_to_value(next_state).item())

            CS.append((x_c, y_c))

        avg_reward.append(ep_reward)
        avg_constraint.append(ep_constraint)

        #print(avg_reward, avg_constraint)
        return np.mean(avg_reward), np.mean(avg_constraint), IR, Goals, CS


    def save(self):
        path = self.save_dir + "z" + self.exp_no

        torch.save(self.dqn_meta.state_dict(), path + "_rq_meta")
        torch.save(self.dqn_lower.state_dict(), path + "_rq_lower")

        torch.save(self.cost_lower_model.state_dict(), path + "_cq_lower")
        torch.save(self.review_lower_model.state_dict(), path + "_cv_meta")


    def load(self):

        path = self.save_dir + "z" + self.exp_no
        print(path)
        self.dqn_meta.load_state_dict(torch.load(path + "_rq_meta"))
        self.dqn_lower.load_state_dict(torch.load( path + "_rq_lower"))

        self.cost_lower_model.load_state_dict(torch.load( path + "_cq_lower"))
        self.review_lower_model.load_state_dict(torch.load(path + "_cv_meta"))
