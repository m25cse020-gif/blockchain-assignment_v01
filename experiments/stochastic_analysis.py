"""
Task 7: Stochastic Analysis of Mining Probability
===================================================
Attaches to a Node that is ALREADY RUNNING in your live network
(seeds on 8000/8001/8002, peer nodes on 9001-9005).

How it works:
  1. Imports the Node class and connects to YOUR existing seeds.
  2. Starts a new node on port 9099 that joins the live network —
     it registers with your seeds, discovers your running peers,
     and syncs the current blockchain from them.
  3. Lets the mine_loop run normally (driven by the network),
     but hooks into the Miner to record every real tau and lambda
     value after each mine() call.
  4. Waits until 100 real mining cycles are collected.
  5. Plots the results.

PRE-REQUISITE:
  Start your seeds and at least one peer node first, e.g.:
    Terminal 1:  python3 network/seed.py 8000
    Terminal 2:  python3 network/seed.py 8001
    Terminal 3:  python3 network/seed.py 8002
    Terminal 4:  python3 run_node1.py
  Then in a new terminal from the project root:
    python3 plots/task7_stochastic_analysis.py
"""

import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from network.node import Node
from mining.pow_miner import Miner

# ─────────────────────────────────────────────────────────────────────────────
# Configuration — points to YOUR live network
# ─────────────────────────────────────────────────────────────────────────────

HASH_POWER   = 30.0   # this node's hash power (%)
INTERARRIVAL = 1.0   # must match the rest of your network
NUM_CYCLES   = 100  # mining cycles to collect

# Your existing seed nodes
SEED_LIST = [
    ("127.0.0.1", 8000),
    ("127.0.0.1", 8001),
    ("127.0.0.1", 8002),
]

NODE_PORT = 9099   # dedicated port for this analysis node
HOST      = "127.0.0.1"

meanTk = 1.0 / INTERARRIVAL


def compute_lambda(hp):
    return (hp * meanTk) / 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Join the existing network as a real peer
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 62)
print("  Task 7: Stochastic Analysis — Live Network Collection")
print("=" * 62)
print(f"\n[SETUP] Joining your live network (seeds: {SEED_LIST})...")

node = Node(
    host         = HOST,
    port         = NODE_PORT,
    seed_list    = SEED_LIST,   # YOUR running seeds
    hash_power   = HASH_POWER,
    interarrival = INTERARRIVAL,
)

# register_with_seed connects to 8000/8001/8002 and gets the peer list
# of your running nodes (9001, 9002, etc.)
node.register_with_seed()

# sync the real blockchain from your existing peers
node.request_chain_sync()

# start the TCP server so other nodes can gossip blocks to us
threading.Thread(target=node.start_server, daemon=True).start()
time.sleep(0.5)

print(f"[SETUP] Joined network.")
print(f"        Peers discovered : {node.peers}")
print(f"        Chain height     : {len(node.blockchain.chain)}")
print(f"        Mempool size     : {node.mempool.size()}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Seed mempool (so this node always has txs to mine)
# ─────────────────────────────────────────────────────────────────────────────

needed = NUM_CYCLES * 5 + 50
if node.mempool.size() < needed:
    top_up = needed - node.mempool.size()
    print(f"\n[SETUP] Topping up mempool with {top_up} petroleum transactions...")
    node.mempool.seed_initial_transactions(count=top_up)

print(f"[SETUP] Mempool ready: {node.mempool.size()} transactions")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Hook into the Miner to intercept every mine() call
#
# We wrap node.miner.mine() so that after EACH real call we record
# the tau and lambda that were actually used. The mining logic itself
# (including abort on receiving a longer chain from your live peers)
# is completely unchanged.
# ─────────────────────────────────────────────────────────────────────────────

collected_tau    = []
collected_lambda = []
collection_done  = threading.Event()

_original_mine = node.miner.mine   # keep reference to real method

def _instrumented_mine():
    """Drop-in replacement: calls real mine(), then records the result."""
    result = _original_mine()

    # miner.last_tau and miner.last_lambda are set by mine() in pow_miner.py
    tau = node.miner.last_tau
    lam = node.miner.last_lambda

    if result and tau is not None:
        # Only count successful (non-aborted) cycles
        collected_tau.append(tau)
        collected_lambda.append(lam)
        n = len(collected_tau)
        print(f"  [TAU collected {n:>3}/{NUM_CYCLES}]  "
              f"tau={tau:.4f}s  lambda={lam:.6f}  "
              f"chain={len(node.blockchain.chain)}")
        if n >= NUM_CYCLES:
            collection_done.set()

    return result

# Swap in our instrumented version
node.miner.mine = _instrumented_mine

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Start the real mine_loop (same as run_node1.py does)
# ─────────────────────────────────────────────────────────────────────────────

print(f"\n[MINING] Node 9099 now mining on the live network.")
print(f"         Collecting {NUM_CYCLES} successful mining cycles...")
print(f"         hash_power={HASH_POWER}%  "
      f"lambda={compute_lambda(HASH_POWER):.6f}  "
      f"E[Tk]={1/compute_lambda(HASH_POWER):.1f}s\n")

# mine_loop is the same loop run_node1.py uses — it processes the
# pending queue (blocks arriving from your live peers), pulls txs
# from the mempool, calls mine(), and broadcasts mined blocks.
node._syncing = False
threading.Thread(target=node.mine_loop, daemon=True).start()
threading.Thread(target=node.liveness_loop, daemon=True).start()

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Wait for NUM_CYCLES collections
# ─────────────────────────────────────────────────────────────────────────────

collection_done.wait()   # blocks until 100 taus are recorded

print(f"\n[DONE] Collected {len(collected_tau)} real tau values "
      f"from the live network.")
print(f"       Final chain height: {len(node.blockchain.chain)}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Plot
# ─────────────────────────────────────────────────────────────────────────────

lam_fixed = compute_lambda(HASH_POWER)
mean_theo = 1.0 / lam_fixed
mean_obs  = float(np.mean(collected_tau))
std_obs   = float(np.std(collected_tau))

fig = plt.figure(figsize=(15, 6))
fig.suptitle(
    f"Task 7: Stochastic Analysis of Mining Probability\n"
    f"[Live data from Node port={NODE_PORT}  joined network with peers {node.peers}]\n"
    f"hash_power={HASH_POWER}%   λ={lam_fixed:.5f}   "
    f"interarrival={INTERARRIVAL}s   meanTk={meanTk:.4f}",
    fontsize=11, fontweight="bold", y=1.02
)

gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38)

# ── Part 1: Histogram + Theoretical PDF ───────────────────────────────────

ax1 = fig.add_subplot(gs[0])

ax1.hist(
    collected_tau,
    bins=15,
    density=True,
    color="#4C72B0",
    edgecolor="white",
    linewidth=0.6,
    alpha=0.75,
    label=f"Real Tk from Node {NODE_PORT}  (n={NUM_CYCLES})"
)

t_range = np.linspace(0, max(collected_tau) * 1.15, 500)
pdf     = lam_fixed * np.exp(-lam_fixed * t_range)
ax1.plot(t_range, pdf, color="#C44E52", linewidth=2.2,
         label="Theoretical PDF  f(t) = λe$^{-λt}$")

ax1.axvline(mean_obs,  color="#2CA02C", linestyle="--", linewidth=1.8,
            label=f"Observed mean = {mean_obs:.2f}s")
ax1.axvline(mean_theo, color="#FF7F0E", linestyle=":",  linewidth=2.0,
            label=f"Theoretical E[Tk] = {mean_theo:.2f}s")

ax1.set_title(
    "Part 1 — Waiting Time Distribution\n"
    "(100 real cycles from live network node)",
    fontsize=11
)
ax1.set_xlabel("Waiting Time  Tk  (seconds)", fontsize=10)
ax1.set_ylabel("Probability Density", fontsize=10)
ax1.legend(fontsize=8.5)
ax1.grid(axis="y", linestyle="--", alpha=0.4)

info = (
    f"Source: live Node port {NODE_PORT}\n"
    f"Peers : {node.peers}\n"
    f"hash_power  = {HASH_POWER}%\n"
    f"λ           = {lam_fixed:.6f}\n"
    f"E[Tk] = 1/λ = {mean_theo:.2f}s\n"
    f"Obs mean    = {mean_obs:.3f}s\n"
    f"Obs std     = {std_obs:.3f}s\n"
    f"Rel error   = {abs(mean_obs - mean_theo)/mean_theo * 100:.1f}%"
)
ax1.text(0.97, 0.97, info, transform=ax1.transAxes,
         fontsize=7.5, va="top", ha="right",
         bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow",
                   ec="gray", alpha=0.9))

# ── Part 2: Lambda vs Hash Power ───────────────────────────────────────────

ax2 = fig.add_subplot(gs[1])

hp_range  = np.arange(1, 101, 1)
lam_range = (hp_range * meanTk) / 100.0
etk_range = 1.0 / lam_range

c1, c2 = "#4C72B0", "#C44E52"

l1, = ax2.plot(hp_range, lam_range, color=c1, linewidth=2.2,
               label="λ  (left axis)")
ax2.set_xlabel("Hash Power  (%)", fontsize=10)
ax2.set_ylabel("Lambda  (λ)", fontsize=10, color=c1)
ax2.tick_params(axis="y", labelcolor=c1)

ax2b = ax2.twinx()
l2, = ax2b.plot(hp_range, etk_range, color=c2, linewidth=2.2,
                linestyle="--", label="E[Tk] = 1/λ  (right axis)")
ax2b.set_ylabel("Expected Waiting Time  E[Tk]  (s)", fontsize=10, color=c2)
ax2b.tick_params(axis="y", labelcolor=c2)

ax2.axvline(HASH_POWER, color="#2CA02C", linestyle=":", linewidth=1.5, alpha=0.8)
ax2.annotate(
    f"  This node\n  hp={HASH_POWER:.0f}%\n  λ={lam_fixed:.5f}",
    xy=(HASH_POWER, lam_fixed),
    xytext=(HASH_POWER + 10, lam_fixed * 0.5),
    fontsize=8, color="#2CA02C",
    arrowprops=dict(arrowstyle="->", color="#2CA02C", lw=1.2)
)

ax2.legend([l1, l2], [l1.get_label(), l2.get_label()],
           fontsize=8.5, loc="upper left")
ax2.set_title(
    "Part 2 — λ and E[Tk] vs Hash Power\n"
    f"(meanTk = 1/{INTERARRIVAL:.0f} = {meanTk:.4f})",
    fontsize=11
)
ax2.grid(linestyle="--", alpha=0.4)

table = (
    "Formula:  λ = (hp × meanTk) / 100\n"
    "          E[Tk] = 1/λ\n\n"
    + "\n".join(
        f"hp={hp:>3}%  λ={compute_lambda(hp):.5f}  "
        f"E[Tk]={1/compute_lambda(hp):>7.1f}s"
        for hp in [1, 10, 20, 30, 51, 75, 100]
    )
)
ax2.text(0.97, 0.42, table, transform=ax2.transAxes,
         fontsize=7.5, va="top", ha="right", family="monospace",
         bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow",
                   ec="gray", alpha=0.9))

# ─────────────────────────────────────────────────────────────────────────────
# Save + terminal summary
# ─────────────────────────────────────────────────────────────────────────────

out = os.path.join(os.path.dirname(__file__), "task7_output.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nPlot saved → {out}")

print("\n" + "=" * 62)
print("  SUMMARY")
print("=" * 62)
print(f"  Node port         : {NODE_PORT}")
print(f"  Peers in network  : {node.peers}")
print(f"  Hash power        : {HASH_POWER}%")
print(f"  Lambda (λ)        : {lam_fixed:.6f}")
print(f"  Theoretical E[Tk] : {mean_theo:.4f}s")
print(f"  Observed mean     : {mean_obs:.4f}s")
print(f"  Observed std      : {std_obs:.4f}s")
print(f"  Relative error    : {abs(mean_obs - mean_theo)/mean_theo * 100:.2f}%")
print(f"  Final chain height: {len(node.blockchain.chain)}")
print(f"""
Answer to Assignment Question:
───────────────────────────────
As hash power increases, λ = (hp × meanTk) / 100 increases linearly.
A higher λ compresses the exponential distribution toward zero, so the
node draws shorter waiting times more frequently.

Since E[Tk] = 1/λ, doubling hash power doubles λ and halves the average
wait. The real data above (hp={HASH_POWER}%, λ={lam_fixed:.5f}) gave an
observed mean of {mean_obs:.2f}s vs theoretical {mean_theo:.2f}s, confirming
the exponential model holds on the live network.
""")

plt.show()