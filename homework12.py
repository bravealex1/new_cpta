import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import beta

# Define theta grid
theta = np.linspace(0, 1, 1000)

# Define the 4 cases exactly as in the question
cases = [
    {"r": 1, "s": 1, "n": 4,  "k": 3},
    {"r": 1, "s": 1, "n": 20, "k": 11},
    {"r": 4, "s": 4, "n": 4,  "k": 3},
    {"r": 4, "s": 4, "n": 20, "k": 11},
]

# Setup 2x2 subplot layout
fig, axs = plt.subplots(2, 2, figsize=(12, 10))
axs = axs.ravel()

print("Posterior probabilities P(theta > 0.5):\n")

# Loop through cases and plot
for i, case in enumerate(cases):
    r, s, n, k = case["r"], case["s"], case["n"], case["k"]
    
    # Prior: Beta(r, s), Posterior: Beta(r + k, s + n - k)
    prior = beta.pdf(theta, r, s)
    posterior = beta.pdf(theta, r + k, s + n - k)

    # Plotting
    axs[i].plot(theta, prior, label="Prior", color="blue")
    axs[i].plot(theta, posterior, label="Posterior", color="red")
    axs[i].set_title(f"Case {i+1}: r={r}, s={s}, n={n}, k={k}")
    axs[i].set_xlabel(r"$\theta$")
    axs[i].set_ylabel("Density")
    axs[i].legend()

    # Compute and print P(theta > 0.5)
    prob_gt_0_5 = 1 - beta.cdf(0.5, r + k, s + n - k)
    print(f"Case {i+1}: r={r}, s={s}, n={n}, k={k} -> P(theta > 0.5) ≈ {prob_gt_0_5:.4f}")

plt.tight_layout()
plt.show()
