# import random
# import math
# import matplotlib.pyplot as plt

# # base mining rate (difficulty 0)
# base_lambda = 1.0

# d_values = list(range(0, 10))  # leading zero bits 0..9
# avg_tau = []

# for d in d_values:
#     lam = base_lambda / (2 ** d)

#     samples = []
#     for _ in range(1000):
#         tau = random.expovariate(lam)
#         samples.append(tau)

#     avg_tau.append(sum(samples) / len(samples))

# plt.figure()
# plt.plot(d_values, avg_tau, marker='o')
# plt.xlabel("Leading Zero Bits (d)")
# plt.ylabel("Average Waiting Time τ")
# plt.title("Effect of Leading Zeros on Mining Time")
# plt.show()

"""
leading_zero_simulation.py
===========================
Simulates the relationship between Proof-of-Work difficulty
(number of required leading zero bits) and two key mining parameters:

  1. Average waiting time  τ  (E[Tk] = 1 / λ_effective)
  2. The effective lambda  λ_effective = base_lambda / 2^d

Theory
------
In a standard PoW scheme a valid hash must be less than a target T.
Requiring d leading zero bits means:

    T  =  2^(256 - d)   (out of 2^256 possible hashes)

The probability that any single hash attempt succeeds is:

    p  =  T / 2^256  =  1 / 2^d

In our exponential-simulation model the overall network block-generation
rate is meanTk = 1 / interarrival_time.  Scaling by hash power gives:

    lambda_node = nodeHashPower * meanTk / 100

Adding PoW difficulty d multiplies the expected search space by 2^d,
so the effective per-node lambda becomes:

    lambda_effective(d) = lambda_node / 2^d

Consequently the average waiting time scales as:

    E[Tk](d)  =  1 / lambda_effective(d)  =  2^d / lambda_node

Plots produced
--------------
  Figure 1 (top)    – Average waiting time τ vs. leading zero bits  (original)
  Figure 1 (bottom) – Effective lambda λ    vs. leading zero bits  (NEW)

Both plots are drawn side-by-side in a single figure so the inverse
relationship between λ and E[Tk] is visually obvious.
"""

import random
import math
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ── Simulation parameters ───────────────────────────────────────────────────

HASH_POWER    = 30          # node's share of total hash power (%)
INTERARRIVAL  = 15.0        # target network-wide block interval (seconds)
N_SAMPLES     = 2000        # exponential samples per difficulty level
D_MAX         = 16          # max leading zero bits to simulate (0 … D_MAX)

# Derived base lambda (no difficulty penalty)
MEAN_TK      = 1.0 / INTERARRIVAL
BASE_LAMBDA  = (HASH_POWER * MEAN_TK) / 100.0   # = 0.02 for hp=30, ia=15

d_values = list(range(0, D_MAX + 1))

# ── Simulation ───────────────────────────────────────────────────────────────

avg_tau       = []   # simulated average waiting time per difficulty level
lambda_values = []   # exact analytical lambda per difficulty level

for d in d_values:
    # Effective lambda: each extra leading-zero bit halves the success probability
    lam_eff = BASE_LAMBDA / (2 ** d)
    lambda_values.append(lam_eff)

    # Draw N_SAMPLES exponential waiting times and average them
    samples = [random.expovariate(lam_eff) for _ in range(N_SAMPLES)]
    avg_tau.append(sum(samples) / len(samples))

# Analytical curves (exact, no noise)
analytical_tau    = [1.0 / lam for lam in lambda_values]
analytical_lambda = lambda_values   # already exact

# ── Styling ──────────────────────────────────────────────────────────────────

DARK_BG    = "#0d1117"
PANEL_BG   = "#161b22"
GRID_COL   = "#21262d"
TEXT_COL   = "#e6edf3"
ACCENT1    = "#58a6ff"    # blue  – simulated / bar fill
ACCENT2    = "#3fb950"    # green – analytical line
ACCENT3    = "#f78166"    # coral – lambda curve
ACCENT3L   = "#ff7b72"
MID_TEXT   = "#8b949e"

plt.rcParams.update({
    "figure.facecolor":  DARK_BG,
    "axes.facecolor":    PANEL_BG,
    "axes.edgecolor":    GRID_COL,
    "axes.labelcolor":   TEXT_COL,
    "axes.titlecolor":   TEXT_COL,
    "xtick.color":       MID_TEXT,
    "ytick.color":       MID_TEXT,
    "grid.color":        GRID_COL,
    "grid.linestyle":    "--",
    "grid.linewidth":    0.6,
    "text.color":        TEXT_COL,
    "font.family":       "monospace",
    "legend.facecolor":  PANEL_BG,
    "legend.edgecolor":  GRID_COL,
    "legend.labelcolor": TEXT_COL,
})

fig, (ax1, ax2) = plt.subplots(
    2, 1,
    figsize=(12, 9),
    facecolor=DARK_BG,
    gridspec_kw={"hspace": 0.55},
)

fig.suptitle(
    "Proof-of-Work Difficulty Analysis\n"
    f"(hash_power={HASH_POWER}%,  interarrival={INTERARRIVAL}s,  "
    f"base λ={BASE_LAMBDA:.4f})",
    fontsize=13,
    fontweight="bold",
    color=TEXT_COL,
    y=0.97,
)

# ── Plot 1 : Average Waiting Time vs Leading Zero Bits ────────────────────────

ax1.set_facecolor(PANEL_BG)
ax1.grid(True, axis="both", zorder=0)

# Bar chart of simulated averages
bars = ax1.bar(
    d_values, avg_tau,
    color=ACCENT1, alpha=0.45, zorder=2,
    label="Simulated avg τ",
    width=0.6,
)

# Analytical exponential curve
ax1.plot(
    d_values, analytical_tau,
    color=ACCENT2, linewidth=2.0, marker="o",
    markersize=5, zorder=3,
    label=f"Analytical  E[Tk] = 2^d / λ_base",
)

# Annotate the doubling factor
for i in range(1, len(d_values)):
    ratio = analytical_tau[i] / analytical_tau[i - 1]
    ax1.annotate(
        f"×{ratio:.0f}",
        xy=(d_values[i], analytical_tau[i]),
        xytext=(0, 8),
        textcoords="offset points",
        fontsize=6.5,
        color=ACCENT2,
        ha="center",
    )

ax1.set_xlabel("Leading Zero Bits  (d)", fontsize=11)
ax1.set_ylabel("Average Waiting Time  τ  (seconds)", fontsize=11)
ax1.set_title("Graph 1 – Waiting Time grows exponentially with difficulty", fontsize=11)
ax1.set_xticks(d_values)
ax1.yaxis.set_major_formatter(
    ticker.FuncFormatter(lambda v, _: f"{v:,.0f}s" if v >= 1000 else f"{v:.1f}s")
)
ax1.legend(fontsize=9, loc="upper left")
ax1.set_xlim(-0.5, D_MAX + 0.5)

# ── Plot 2 : Lambda vs Leading Zero Bits  (NEW) ───────────────────────────────

ax2.set_facecolor(PANEL_BG)
ax2.grid(True, axis="both", zorder=0)

# Filled area under the lambda curve to emphasise the decay
ax2.fill_between(
    d_values, lambda_values,
    color=ACCENT3, alpha=0.15, zorder=1,
)

# Main lambda line
ax2.plot(
    d_values, lambda_values,
    color=ACCENT3L, linewidth=2.2, marker="s",
    markersize=5, zorder=3,
    label=r"$\lambda_{eff}(d)\ =\ \lambda_{base}\ /\ 2^d$",
)

# Annotate each point with its exact value
for d, lam in zip(d_values, lambda_values):
    if lam >= 1e-4:
        label_str = f"{lam:.4f}"
    else:
        exp = int(math.log10(lam))
        coeff = lam / (10 ** exp)
        label_str = f"{coeff:.2f}×10^{exp}"

    ax2.annotate(
        label_str,
        xy=(d, lam),
        xytext=(0, 9),
        textcoords="offset points",
        fontsize=6.2,
        color=MID_TEXT,
        ha="center",
    )

# Mark base_lambda with a dashed horizontal reference
ax2.axhline(
    y=BASE_LAMBDA, color=ACCENT1,
    linewidth=1.0, linestyle=":",
    label=f"Base λ = {BASE_LAMBDA:.4f}  (d=0)",
    zorder=2,
)

# Shade the "halving per bit" zones
for d in range(0, D_MAX, 2):
    ax2.axvspan(d, d + 1, color=ACCENT3, alpha=0.04, zorder=0)

ax2.set_xlabel("Leading Zero Bits  (d)", fontsize=11)
ax2.set_ylabel("Effective Lambda  λ_eff", fontsize=11)
ax2.set_title(
    "Graph 2 – λ halves with each additional leading-zero bit  "
    r"($\lambda_{eff}=\lambda_{base}/2^d$)",
    fontsize=11,
)
ax2.set_xticks(d_values)
ax2.set_yscale("log")   # log scale makes the halving pattern a straight line
ax2.yaxis.set_major_formatter(
    ticker.FuncFormatter(lambda v, _: f"{v:.2e}" if v < 0.001 else f"{v:.5f}")
)
ax2.legend(fontsize=9, loc="upper right")
ax2.set_xlim(-0.5, D_MAX + 0.5)

# Footnote
fig.text(
    0.5, 0.005,
    "Note: log-scale on Graph 2 reveals that λ decays linearly on a log axis "
    "– i.e. each extra leading-zero bit is a constant multiplicative penalty of ½.",
    ha="center", va="bottom",
    fontsize=8, color=MID_TEXT,
    style="italic",
)

# ── Save + show ───────────────────────────────────────────────────────────────

plt.savefig(
    "leading_zero_difficulty.png",
    dpi=150, bbox_inches="tight",
    facecolor=DARK_BG,
)
print("Plot saved → leading_zero_difficulty.png")
plt.show()
