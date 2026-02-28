"""
Task 7: Stochastic Analysis of Mining Probability
===================================================
Analyzes the statistical behavior of the simulated Proof of Work process
based on the variables lambda (λ) and waiting time (Tk).

Part 1 — Waiting Time Distribution:
    For a node with a fixed hash power, collect Tk over 100 mining cycles
    and plot as histogram + theoretical PDF overlay.

Part 2 — Lambda vs Hash Power:
    Plot the relationship between a node's individual lambda and its assigned
    hash power percentage (1% to 100%), given a constant meanTk.

Run from the project root:
    python3 plots/task7_stochastic_analysis.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.stats import expon

# ─────────────────────────────────────────────────────────────────────────────
# Parameters (matching the assignment spec exactly)
# ─────────────────────────────────────────────────────────────────────────────

INTERARRIVAL   = 10.0      # target network-wide average block interval (seconds)
HASH_POWER_FIXED = 30.0   # fixed hash power for Part 1 (%)
NUM_CYCLES     = 100       # number of mining cycles to simulate

# Derived from spec:
#   meanTk = 1.0 / interarrival
#   lambda = nodeHashPower * meanTk / 100.0
#   Tk     = random.expovariate(lambda)

meanTk = 1.0 / INTERARRIVAL


def compute_lambda(hash_power):
    """lambda = nodeHashPower * meanTk / 100.0"""
    return (hash_power * meanTk) / 100.0


def simulate_mining_cycles(hash_power, n_cycles):
    """Draw n_cycles exponential waiting times for a given hash power."""
    lam = compute_lambda(hash_power)
    return [random.expovariate(lam) for _ in range(n_cycles)]


# ─────────────────────────────────────────────────────────────────────────────
# Figure setup — two plots side by side
# ─────────────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(15, 6))
fig.suptitle(
    "Task 7: Stochastic Analysis of Mining Probability\n"
    f"(interarrival={INTERARRIVAL}s,  meanTk=1/{INTERARRIVAL:.0f}={meanTk:.3f})",
    fontsize=13, fontweight="bold", y=1.01
)

gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38)

# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — Waiting Time Distribution (Histogram + PDF)
# ─────────────────────────────────────────────────────────────────────────────

ax1 = fig.add_subplot(gs[0])

lam_fixed  = compute_lambda(HASH_POWER_FIXED)
samples    = simulate_mining_cycles(HASH_POWER_FIXED, NUM_CYCLES)
mean_obs   = np.mean(samples)
std_obs    = np.std(samples)
mean_theo  = 1.0 / lam_fixed   # E[Tk] = 1/lambda

# Histogram (normalised to density so PDF overlays correctly)
n_bins = 15
counts, bin_edges, patches = ax1.hist(
    samples,
    bins=n_bins,
    density=True,
    color="#4C72B0",
    edgecolor="white",
    linewidth=0.6,
    alpha=0.75,
    label=f"Simulated Tk  (n={NUM_CYCLES})"
)

# Theoretical PDF: f(t) = λ · e^(−λt)
t_range = np.linspace(0, max(samples) * 1.1, 500)
pdf     = lam_fixed * np.exp(-lam_fixed * t_range)
ax1.plot(t_range, pdf, color="#C44E52", linewidth=2.2,
         label=f"Theoretical PDF  f(t)=λe$^{{-λt}}$")

# Vertical lines for means
ax1.axvline(mean_obs,  color="#2CA02C", linestyle="--", linewidth=1.6,
            label=f"Observed mean = {mean_obs:.2f}s")
ax1.axvline(mean_theo, color="#FF7F0E", linestyle=":",  linewidth=1.8,
            label=f"Theoretical mean = {mean_theo:.2f}s")

ax1.set_title(
    f"Part 1 — Waiting Time Distribution\n"
    f"hash_power={HASH_POWER_FIXED:.0f}%,  λ={lam_fixed:.4f}",
    fontsize=11
)
ax1.set_xlabel("Waiting Time  Tk  (seconds)", fontsize=10)
ax1.set_ylabel("Probability Density", fontsize=10)
ax1.legend(fontsize=8.5)
ax1.grid(axis="y", linestyle="--", alpha=0.4)

# Annotation box
textstr = (
    f"λ  = {lam_fixed:.5f}\n"
    f"E[Tk] = 1/λ = {mean_theo:.2f}s\n"
    f"Obs mean  = {mean_obs:.2f}s\n"
    f"Obs std   = {std_obs:.2f}s"
)
ax1.text(0.97, 0.97, textstr, transform=ax1.transAxes,
         fontsize=8, verticalalignment="top", horizontalalignment="right",
         bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                   edgecolor="gray", alpha=0.9))

# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — Lambda vs Hash Power
# ─────────────────────────────────────────────────────────────────────────────

ax2 = fig.add_subplot(gs[1])

hash_powers   = np.arange(1, 101, 1)             # 1% to 100%
lambdas       = (hash_powers * meanTk) / 100.0   # λ = hp * meanTk / 100
expected_waits = 1.0 / lambdas                   # E[Tk] = 1/λ

# Primary axis: lambda vs hash power
color_lam = "#4C72B0"
l1, = ax2.plot(hash_powers, lambdas, color=color_lam, linewidth=2.2,
               label="λ  (left axis)")
ax2.set_xlabel("Hash Power  (%)", fontsize=10)
ax2.set_ylabel("Lambda  (λ)", fontsize=10, color=color_lam)
ax2.tick_params(axis="y", labelcolor=color_lam)

# Secondary axis: expected waiting time vs hash power
ax2b = ax2.twinx()
color_wait = "#C44E52"
l2, = ax2b.plot(hash_powers, expected_waits, color=color_wait,
                linewidth=2.2, linestyle="--",
                label="E[Tk] = 1/λ  (right axis)")
ax2b.set_ylabel("Expected Waiting Time  E[Tk]  (s)",
                fontsize=10, color=color_wait)
ax2b.tick_params(axis="y", labelcolor=color_wait)

# Mark the fixed hash power used in Part 1
ax2.axvline(HASH_POWER_FIXED, color="#2CA02C", linestyle=":",
            linewidth=1.5, alpha=0.8)
ax2.annotate(
    f"  hp={HASH_POWER_FIXED:.0f}%\n  λ={lam_fixed:.4f}",
    xy=(HASH_POWER_FIXED, lam_fixed),
    xytext=(HASH_POWER_FIXED + 8, lam_fixed * 0.6),
    fontsize=8, color="#2CA02C",
    arrowprops=dict(arrowstyle="->", color="#2CA02C", lw=1.2)
)

# Combined legend
lines = [l1, l2]
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, fontsize=8.5, loc="upper left")

ax2.set_title(
    f"Part 2 — λ and E[Tk] vs Hash Power\n"
    f"(meanTk = 1/{INTERARRIVAL:.0f} = {meanTk:.3f})",
    fontsize=11
)
ax2.grid(linestyle="--", alpha=0.4)

# Annotation box
textstr2 = (
    f"Formula:\n"
    f"  λ = (hp × meanTk) / 100\n"
    f"  E[Tk] = 1 / λ\n\n"
    f"At hp=1%:  λ={compute_lambda(1):.5f},  E[Tk]={1/compute_lambda(1):.1f}s\n"
    f"At hp=50%: λ={compute_lambda(50):.5f},  E[Tk]={1/compute_lambda(50):.1f}s\n"
    f"At hp=100%:λ={compute_lambda(100):.5f},  E[Tk]={1/compute_lambda(100):.1f}s"
)
ax2.text(0.97, 0.35, textstr2, transform=ax2.transAxes,
         fontsize=7.5, verticalalignment="top", horizontalalignment="right",
         bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                   edgecolor="gray", alpha=0.9))

# ─────────────────────────────────────────────────────────────────────────────
# Save and show
# ─────────────────────────────────────────────────────────────────────────────

output_path = os.path.join(os.path.dirname(__file__), "task7_output.png")
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"\nPlot saved to: {output_path}")

# ─────────────────────────────────────────────────────────────────────────────
# Print answer to the assignment question
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 62)
print("  TASK 7 — ANALYSIS OUTPUT")
print("=" * 62)

print(f"\nPart 1: Waiting Time Distribution")
print(f"  Hash Power       : {HASH_POWER_FIXED}%")
print(f"  Lambda (λ)       : {lam_fixed:.6f}")
print(f"  Theoretical E[Tk]: {mean_theo:.4f} s")
print(f"  Observed mean    : {mean_obs:.4f} s")
print(f"  Observed std     : {std_obs:.4f} s")
print(f"  Relative error   : {abs(mean_obs - mean_theo)/mean_theo * 100:.2f}%")

print(f"\nPart 2: Lambda vs Hash Power")
print(f"  {'Hash Power':>12} | {'Lambda':>12} | {'E[Tk] (s)':>12}")
print(f"  {'-'*12}-+-{'-'*12}-+-{'-'*12}")
for hp in [1, 10, 20, 30, 50, 75, 100]:
    lam = compute_lambda(hp)
    etk = 1.0 / lam
    print(f"  {hp:>11}% | {lam:>12.6f} | {etk:>11.2f}s")

print(f"""
Answer to Assignment Question:
───────────────────────────────
As a node's hash power increases from 1% to 100%, its individual
lambda (λ) increases linearly: λ = (hashPower × meanTk) / 100.

A higher λ means the exponential distribution is more tightly
concentrated near zero — the node draws shorter waiting times
more frequently. Specifically:

  E[Tk] = 1/λ

So doubling hash power doubles λ, and halves the average waiting
time. A node with 50% hash power (λ={compute_lambda(50):.4f}) expects
to wait only {1/compute_lambda(50):.1f}s on average, while a node with 1%
hash power (λ={compute_lambda(1):.4f}) waits on average {1/compute_lambda(1):.1f}s.

This correctly models the proportional mining advantage of nodes
with greater computational resources in a PoW network.
""")

plt.show()
