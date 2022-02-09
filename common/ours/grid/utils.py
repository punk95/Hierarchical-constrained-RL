import torch
import numpy as np
from math import sqrt


def convert_int_to_coordinates(value, grid_size):
    x = (value)%grid_size
    y = (value)//grid_size
    return x, y

def convert_coordinated_into_int(x, y, grid_size):
    value = y*grid_size + x
    return value

def convert_value_to_hot_vec(value, grid_size):
    hot_vector = [0 for _ in range(grid_size*grid_size)]
    hot_vector[value] = 1
    return np.array(hot_vector).flatten()

def euclidian_distance(value1, value2, grid_size):
    x1, y1 = convert_int_to_coordinates(value1, grid_size)
    x2, y2 = convert_int_to_coordinates(value2, grid_size)

    d = (x1-x2)**2 + (y1-y2)**2
    return sqrt(d)


#class that defines goal space
class Goal_Space():
    def __init__(self, goal_space, grid_size, intrinsic_reward_type="eculidian distance"):

        #goal_space: A list of indices which corresponds to the location on grid as indicated by one-hot vector
        self.grid_size = grid_size
        self.goal_space = goal_space
        self.intrinsic_reward_type = intrinsic_reward_type

        self.action_shape = (len(goal_space), 1)

    def intrisic_reward(self, current_state, goal_state):
        if type(current_state) != torch.Tensor:
            current_state = torch.Tensor(current_state)
        if type(goal_state) != torch.Tensor:
            goal_state = torch.Tensor(goal_state)

        current_value = torch.argmax(current_state).item()
        goal_value = torch.argmax(goal_state).item()

        print(current_value, goal_value)
        if self.intrinsic_reward_type == "eculidian distance":
            f = euclidian_distance(current_value, goal_value, self.grid_size)
            return f
        else:
            raise Exception("Not Implemented")

    def action_to_goal(self, action):
        #get the corresponding goal for the discrete action
        return convert_value_to_hot_vec(self.goal_space[action], self.grid_size)


"""
G = Goal_Space([1,10], 9)
print(convert_int_to_coordinates(34, 9))
print(convert_coordinated_into_int(6, 3, 9))
print(convert_value_to_hot_vec(35, 9))

S1 = convert_value_to_hot_vec(2,9)
S2 = convert_value_to_hot_vec(32,9)

print(G.intrisic_reward(S1, S2))
"""