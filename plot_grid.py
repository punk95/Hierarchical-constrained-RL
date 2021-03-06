import torch
import numpy as np
import matplotlib.pyplot as plt

no_eps = 200000
l = no_eps//1000
a = []
for i in range(8):
    a.append(torch.load("results/grid/sarsa/c" + str(i+1))[:l])
for i in a:
    #print(len(i))
    pass
""""""

no_experiments = 8
R = []
C = []
R_safe = []
C_safe = []
R_safe_SM = []
C_safe_SM = []

for i in range(no_experiments):
    R.append(torch.load("results/grid/sarsa/r" + str(i + 1))[:l])
    C.append(torch.load("results/grid/sarsa/c" + str(i + 1))[0:l])
    R_safe.append(torch.load("results/grid/safe_sarsa/r" + str(i+1))[:l])
    C_safe.append(torch.load("results/grid/safe_sarsa/c" + str(i+1))[0:l])

    if i < no_experiments-2:
        R_safe_SM.append(torch.load("results/grid/safe_sarsa_with_softmax/r" + str(i+1))[:l])
        C_safe_SM.append(torch.load("results/grid/safe_sarsa_with_softmax/c" + str(i + 1))[:l])

R_avg = []
C_avg = []
R_safe_avg = []
C_safe_avg = []
R_safe_SM_avg = []
C_safe_SM_avg = []

for j in range(len(R)):
    r_avg = []
    c_avg = []
    r_safe_avg = []
    c_safe_avg = []
    r_safe_sm_avg = []
    c_safe_sm_avg = []
    for i in range(10,len(R_safe[0])):
        r_avg.append(np.mean(R[j][i - 10:i]))
        c_avg.append(np.mean(C[j][i - 10:i]))
        r_safe_avg.append(np.mean(R_safe[j][i-10:i]))
        c_safe_avg.append(np.mean(C_safe[j][i-10:i]))
        if j < no_experiments-2:
            r_safe_sm_avg.append(np.mean(R_safe_SM[j][i - 10:i]))
            c_safe_sm_avg.append(np.mean(C_safe_SM[j][i - 10:i]))

    R_avg.append(r_avg)
    C_avg.append(c_avg)
    R_safe_avg.append(r_safe_avg)
    C_safe_avg.append(c_safe_avg)
    if j < no_experiments - 2:
        R_safe_SM_avg.append(r_safe_sm_avg)
        C_safe_SM_avg.append(c_safe_sm_avg)


R_avg = np.array(R_avg)
C_avg = np.array(C_avg)
R_safe_avg = np.array(R_safe_avg)
C_safe_avg = np.array(C_safe_avg)
R_safe_SM_avg = np.array(R_safe_SM_avg)
C_safe_SM_avg = np.array(C_safe_SM_avg)

R_mean = np.mean(R_avg, axis=0)
C_mean = np.mean(C_avg, axis=0)
R_safe_mean = np.mean(R_safe_avg, axis=0)
C_safe_mean = np.mean(C_safe_avg, axis=0)
R_safe_SM_mean = np.mean(R_safe_SM_avg, axis=0)
C_safe_SM_mean = np.mean(C_safe_SM_avg, axis=0)


R_std = np.std(R_avg, axis=0)
C_std = np.std(C_avg, axis=0)
R_safe_std = np.std(R_safe_avg, axis=0)
C_safe_std = np.std(C_safe_avg, axis=0)
R_safe_SM_std = np.std(R_safe_SM_avg, axis=0)
C_safe_SM_std = np.std(C_safe_SM_avg, axis=0)


x = [i for i in range(len(R_safe_mean))]
legend = ["sarsa", "bvf-safe-sarsa-eps", "bvf-safe-sarsa-softmax"]

fig, ax = plt.subplots(1, 1, figsize=(20, 10))
plt.tick_params(axis='both', which='major', labelsize=30)

plt.plot(x, R_mean, label=legend[0], linewidth=5)
plt.fill_between(x, R_mean + R_std, R_mean - R_std, alpha = 0.1)

plt.plot(x, R_safe_mean, label=legend[1], linewidth=5)
plt.fill_between(x, R_safe_mean + R_safe_std, R_safe_mean - R_safe_std, alpha = 0.1)

plt.plot(x, R_safe_SM_mean, label=legend[2], linewidth=5)
plt.fill_between(x, R_safe_SM_mean + R_safe_SM_std, R_safe_SM_mean - R_safe_SM_std, alpha = 0.1)

plt.legend( prop={'size':40})
plt.xlabel('No of episodes X1000', size=40)
plt.ylabel("Reward", size=40)
plt.title("Reward comparision for the Grid World Environment", size=40)
name = "figures/grid/Rewards"
plt.savefig(name)
plt.close(fig)

fig, ax = plt.subplots(1, 1, figsize=(20, 10))
plt.tick_params(axis='both', which='major', labelsize=30)


plt.plot(C_mean, label=legend[0], linewidth=3)
plt.fill_between(x, C_mean + C_std, C_mean - C_std, alpha = 0.3)

plt.plot(C_safe_mean, label=legend[1], linewidth=3)
plt.fill_between(x, C_safe_mean + C_safe_std, C_safe_mean - C_safe_std, alpha = 0.3)

plt.plot(C_safe_SM_mean, label=legend[2], linewidth=3)
plt.fill_between(x, C_safe_SM_mean + C_safe_SM_std, C_safe_SM_mean - C_safe_SM_std, alpha = 0.3)

plt.axhline(y=20, color='r', linestyle='--')
plt.legend(prop={'size':40})
plt.xlabel('No of episodes X1000', size=40)
plt.ylabel("Constraints", size=40)
plt.title("Constraint comparision for the Grid World Environment", size=40)
name = "figures/grid/Constraints"

ax.set_ylim(0, 150)
plt.savefig(name)
plt.close(fig)
