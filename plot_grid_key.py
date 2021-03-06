import torch
import numpy as np
import matplotlib.pyplot as plt

no_eps = 200000
l = no_eps//1000
a = []
for i in range(4):
    a.append(torch.load("results/grid/sarsa_key/c" + str(i+1))[:l])
for i in a:
    print(len(i))
""""""

no_experiments = 8
R = []
C = []
R_safe = []
C_safe = []
HRL_R_safe = []
HRL_C_safe = []
HRL_R_safe_2 = []
HRL_C_safe_2 = []
HRL_R_safe_3 = []
HRL_C_safe_3 = []
R_k = []
C_k = []


for i in range(no_experiments):
    R.append(torch.load("results/grid/sarsa_key/r" + str(i + 1))[:l])
    C.append(torch.load("results/grid/sarsa_key/c" + str(i + 1))[0:l])
    R_safe.append(torch.load("results/grid/safe_sarsa_key/r" + str(i+1))[:l])
    C_safe.append(torch.load("results/grid/safe_sarsa_key/c" + str(i+1))[0:l])
    R_k.append(torch.load("results/grid/hrl_sarsa_key/r" + str(i + 1))[:l])
    C_k.append(torch.load("results/grid/hrl_sarsa_key/c" + str(i + 1))[0:l])
    HRL_R_safe.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_10/r" + str(i + 1))[:l])
    HRL_C_safe.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_10/c" + str(i + 1))[0:l])

    if i < 3:
        HRL_R_safe_2.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_20/r" + str(i + 1))[:l])
        HRL_C_safe_2.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_20/c" + str(i + 1))[0:l])
        HRL_R_safe_3.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_30/r" + str(i + 1))[:l])
        HRL_C_safe_3.append(torch.load("results/grid/safe_lower_hrl_sarsa_key/c_30/c" + str(i + 1))[0:l])

R_avg = []
C_avg = []
R_safe_avg = []
C_safe_avg = []
HRL_R_safe_avg = []
HRL_C_safe_avg = []
HRL_R_safe_avg_2 = []
HRL_C_safe_avg_2 = []
HRL_R_safe_avg_3 = []
HRL_C_safe_avg_3 = []
R_k_avg = []
C_k_avg = []

for j in range(len(R)):
    r_avg = []
    c_avg = []
    r_safe_avg = []
    c_safe_avg = []
    hrl_r_safe_avg = []
    hrl_c_safe_avg = []
    hrl_r_safe_avg_2 = []
    hrl_c_safe_avg_2 = []
    hrl_r_safe_avg_3 = []
    hrl_c_safe_avg_3 = []
    r_k_avg = []
    c_k_avg = []
    for i in range(10,len(R_safe[0])):
        r_avg.append(np.mean(R[j][i - 10:i]))
        c_avg.append(np.mean(C[j][i - 10:i]))
        r_safe_avg.append(np.mean(R_safe[j][i-10:i]))
        c_safe_avg.append(np.mean(C_safe[j][i-10:i]))
        hrl_r_safe_avg.append(np.mean(HRL_R_safe[j][i - 10:i]))
        hrl_c_safe_avg.append(np.mean(HRL_C_safe[j][i - 10:i]))

        if j < 3:
            hrl_r_safe_avg_2.append(np.mean(HRL_R_safe_2[j][i - 10:i]))
            hrl_c_safe_avg_2.append(np.mean(HRL_C_safe_2[j][i - 10:i]))
            hrl_r_safe_avg_3.append(np.mean(HRL_R_safe_3[j][i - 10:i]))
            hrl_c_safe_avg_3.append(np.mean(HRL_C_safe_3[j][i - 10:i]))
        r_k_avg.append(np.mean(R_k[j][i - 10:i]))
        c_k_avg.append(np.mean(C_k[j][i - 10:i]))

    R_avg.append(r_avg)
    C_avg.append(c_avg)
    R_safe_avg.append(r_safe_avg)
    C_safe_avg.append(c_safe_avg)
    HRL_R_safe_avg.append(hrl_r_safe_avg)
    HRL_C_safe_avg.append(hrl_c_safe_avg)
    if j < 3:
        HRL_R_safe_avg_2.append(hrl_r_safe_avg_2)
        HRL_C_safe_avg_2.append(hrl_c_safe_avg_2)
        HRL_R_safe_avg_3.append(hrl_r_safe_avg_3)
        HRL_C_safe_avg_3.append(hrl_c_safe_avg_3)
    R_k_avg.append(r_k_avg)
    C_k_avg.append(c_k_avg)


print(len(HRL_R_safe_avg_2), len(HRL_R_safe_avg_2[0]))
R_avg = np.array(R_avg)
C_avg = np.array(C_avg)
R_safe_avg = np.array(R_safe_avg)
C_safe_avg = np.array(C_safe_avg)
HRL_R_safe_avg = np.array(HRL_R_safe_avg)
HRL_C_safe_avg = np.array(HRL_C_safe_avg)
HRL_R_safe_avg_2 = np.array(HRL_R_safe_avg_2)
HRL_C_safe_avg_2 = np.array(HRL_C_safe_avg_2)
HRL_R_safe_avg_3 = np.array(HRL_R_safe_avg_3)
HRL_C_safe_avg_3 = np.array(HRL_C_safe_avg_3)
R_k_avg = np.array(R_k_avg)
C_k_avg = np.array(C_k_avg)



R_mean = np.mean(R_avg, axis=0)
C_mean = np.mean(C_avg, axis=0)
R_safe_mean = np.mean(R_safe_avg, axis=0)
C_safe_mean = np.mean(C_safe_avg, axis=0)
HRL_R_safe_mean = np.mean(HRL_R_safe_avg, axis=0)
HRL_C_safe_mean = np.mean(HRL_C_safe_avg, axis=0)
HRL_R_safe_mean_2 = np.mean(HRL_R_safe_avg_2, axis=0)
HRL_C_safe_mean_2 = np.mean(HRL_C_safe_avg_2, axis=0)
HRL_R_safe_mean_3 = np.mean(HRL_R_safe_avg_3, axis=0)
HRL_C_safe_mean_3 = np.mean(HRL_C_safe_avg_3, axis=0)
R_k_mean = np.mean(R_k_avg, axis=0)
C_k_mean = np.mean(C_k_avg, axis=0)

R_std = np.std(R_avg, axis=0)
C_std = np.std(C_avg, axis=0)
R_safe_std = np.std(R_safe_avg, axis=0)
C_safe_std = np.std(C_safe_avg, axis=0)
HRL_R_safe_std = np.std(HRL_R_safe_avg, axis=0)
HRL_C_safe_std = np.std(HRL_C_safe_avg, axis=0)
HRL_R_safe_std_2 = np.std(HRL_R_safe_avg_2, axis=0)
HRL_C_safe_std_2 = np.std(HRL_C_safe_avg_2, axis=0)
HRL_R_safe_std_3 = np.std(HRL_R_safe_avg_3, axis=0)
HRL_C_safe_std_3 = np.std(HRL_C_safe_avg_3, axis=0)
R_k_std = np.std(R_k_avg, axis=0)
C_k_std = np.std(C_k_avg, axis=0)


x = [i for i in range(len(R_safe_mean))]
legend = ["sarsa", "bvf-safe-sarsa-eps", "hrl-sarsa", "hrl-safe-l-c-alloc-10", "hrl-safe-low-l-c-alloc-20", "hrl-safe-l-c-alloc-30" ]

fig, ax = plt.subplots(1, 1, figsize=(20, 10))
plt.tick_params(axis='both', which='major', labelsize=30)

plt.plot(x, R_mean, label=legend[0], linewidth=5)
plt.fill_between(x, R_mean + R_std, R_mean - R_std, alpha = 0.1)

plt.plot(x, R_safe_mean, label=legend[1], linewidth=5)
plt.fill_between(x, R_safe_mean + R_safe_std, R_safe_mean - R_safe_std, alpha = 0.1)

plt.plot(x, R_k_mean, label=legend[2], linewidth=5)
plt.fill_between(x, R_k_mean + R_k_std, R_k_mean - R_k_std, alpha = 0.1)

plt.plot(x, HRL_R_safe_mean, label=legend[3], linewidth=5)
plt.fill_between(x, HRL_R_safe_mean + HRL_R_safe_std, HRL_R_safe_mean - HRL_R_safe_std, alpha = 0.1)

plt.plot(x, HRL_R_safe_mean_2, label=legend[4], linewidth=5)
plt.fill_between(x, HRL_R_safe_mean_2 + HRL_R_safe_std_2, HRL_R_safe_mean_2 - HRL_R_safe_std_2, alpha = 0.1)

plt.plot(x, HRL_R_safe_mean_3, label=legend[5], linewidth=5)
plt.fill_between(x, HRL_R_safe_mean_3 + HRL_R_safe_std_3, HRL_R_safe_mean_3 - HRL_R_safe_std_3, alpha = 0.1)

plt.legend( prop={'size':40}, loc='upper left')
plt.xlabel('No of episodes X1000', size=40)
plt.ylabel("Reward", size=40)
plt.title("Reward comparision for the Grid World Environment with a key", size=40)
name = "figures/grid/Rewards_Key"
plt.savefig(name)
plt.close(fig)

fig, ax = plt.subplots(1, 1, figsize=(20, 10))
plt.tick_params(axis='both', which='major', labelsize=30)


plt.plot(C_mean, label=legend[0], linewidth=3)
plt.fill_between(x, C_mean + C_std, C_mean - C_std, alpha = 0.3)

plt.plot(C_safe_mean, label=legend[1], linewidth=3)
plt.fill_between(x, C_safe_mean + C_safe_std, C_safe_mean - C_safe_std, alpha = 0.3)

plt.plot(C_k_mean, label=legend[2], linewidth=3)
plt.fill_between(x, C_k_mean + C_k_std, C_k_mean - C_k_std, alpha = 0.3)

plt.plot(HRL_C_safe_mean, label=legend[3], linewidth=3)
plt.fill_between(x, HRL_C_safe_mean + HRL_C_safe_std, HRL_C_safe_mean - HRL_C_safe_std, alpha = 0.3)

plt.plot(HRL_C_safe_mean_2, label=legend[4], linewidth=3)
plt.fill_between(x, HRL_C_safe_mean_2 + HRL_C_safe_std_2, HRL_C_safe_mean_2 - HRL_C_safe_std_2, alpha = 0.3)

plt.plot(HRL_C_safe_mean_3, label=legend[5], linewidth=3)
plt.fill_between(x, HRL_C_safe_mean_3 + HRL_C_safe_std_3, HRL_C_safe_mean_3 - HRL_C_safe_std_3, alpha = 0.3)



plt.axhline(y=20, color='r', linestyle='--')
plt.legend(prop={'size':40}, loc='upper left')
plt.xlabel('No of episodes X1000', size=40)
plt.ylabel("Constraints", size=40)
plt.title("Constraint comparision for the Grid World Environment with a key", size=40)
name = "figures/grid/Constraints_Key"

ax.set_ylim(0, 150)
plt.savefig(name)
plt.close(fig)
