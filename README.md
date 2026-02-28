#  Blockchain-Based Petroleum Supply Chain Ledger

> **CSL7490 — Assignment 1**  

A full-stack blockchain simulation modelling a petroleum supply chain, built on a custom peer-to-peer TCP network. Implements secp256k1 cryptographic identities, ECDSA-signed transactions, gossip protocol propagation, simulated Proof-of-Work mining, and seven experimental analyses.


##  Project Overview

This project implements a blockchain network from scratch, simulating a petroleum supply chain where producers, pipeline operators, refineries, and distributors record verifiable, tamper-proof supply events on a distributed ledger.

The system is composed of:

- **Seed Nodes** — Bootstrapping servers that maintain and distribute the peer list.
- **Peer Nodes** — Full nodes that generate identities, create and sign transactions, mine blocks, and propagate data via gossip.
- **Blockchain DB** — A per-node SQLite database storing the local copy of the chain.
- **Experiment Scripts** — Standalone scripts demonstrating cryptographic and consensus properties.

---

## Features

| Feature | Description |
|---|---|
| secp256k1 Key Generation | Private key from SHA-256(random), public key via Double-and-Add |
| Wallet Address | Last 16 bits of SHA-256(pubkey) in `0x????` hex format |
| ECDSA Signatures | Sign and verify every transaction; non-repudiation guaranteed |
| P2P Registration | New peers register with ⌊n/2⌋+1 seeds for Byzantine-fault tolerance |
| Gossip Protocol | Message-list deduplication, signature validation before relay |
| Liveness Monitoring | 13-second ping/pong; 3 misses → Dead Node report to seeds |
| PoW Simulation | Exponential random variable model; lambda scaled by hash power % |
| Blockchain Sync | Pending queue + IBD-style chain download for newly joined nodes |
| Merkle Trees | SHA-256 binary hash tree; O(log n) membership proofs |
| Bit Commitment | Hiding + binding scheme C = H(m ∥ r) for supply chain coordination |

---


##  Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.10 or higher | Runtime |
| pip | Latest | Package management |

Check your Python version:
```bash
python3 --version
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/m25cse020-gif/blockchain-assignment_v01.git
cd blockchain-assignment_v01
```

### 2. (Recommended) Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt` contents:**
```
cryptography>=41.0.0     # secp256k1, ECDSA, SHA-256 (via hazmat primitives)
numpy>=1.26.0            # Exponential RV generation (Task 7)
matplotlib>=3.8.0        # Plot generation (Task 7)
```

Install manually if needed:
```bash
pip install cryptography numpy matplotlib
```


##  Running the Simulation

Open a **separate terminal** for each node. All commands are run from the project root.

### Step 1 — Start Seed Nodes

```bash
# Terminal 1
python3 network/seed.py 8000

# Terminal 2
python3 network/seed.py 8001

# Terminal 3
python3 network/seed.py 8002
```

Expected output per seed:
```
[SEED :8000] Listening...
```

---

### Step 2 — Start Peer Nodes

Each peer node requires `--seeds` (comma-separated list of seed addresses) and `--port`:

```bash
# on different Terminals
python3 run_node1.py # Creates a transaction and mines
python3 run_node2.py # Passive listener/miner
python3 run_node3.py # 51% hash power node
python3 run_node4.py
python3 run_node5.py


### Stopping the Simulation

Press `Ctrl+C` in each terminal. Seed nodes should be stopped last.

---

##  Running Experiments

All experiment scripts are standalone and do not require a live network.

### Task 1 — Avalanche Effect
```bash
python3 experiments/avalanche.py
```


### Task 2 — Merkle Tree and Proof
```bash
python3 experiments/merkle_proof.py
```


### Task 3 — Double-Spend Simulation
```bash
python3 experiments/double_spend.py
```


### Task 4 — 51% Attack Simulation
refer report

### Task 5 — Bit Commitment Scheme
```bash
python3 experiments/commitment.py
```

### Task 6 — Difficulty and Leading Zeros Analysis
```bash
python3 experiments/leading_zero_simulation.py
```


### Task 7 — Stochastic Mining Plots
```bash
python3 plots/mining_analysis.py
```
**Output:** Two PNG files saved in the current directory:
- `waiting_time_dist.png` — Histogram of 100 mining waiting times with theoretical Exp(λ) PDF overlay.
- `lambda_vs_hashpower.png` — Lambda and mean waiting time as functions of hash power percentage (1%–100%).

---



## 👥 Authors

| Roll Number | Name |
|---|---|
| `M25CSE018` | `Mangalton Okram` |
| `M25CSE020` | `Nishant Chourasia` |
| `M25CSE028` | `Sarita Mandal` |


---

## 📄 License

This project is submitted as academic coursework for CSL7490. All code is original work by the group members listed above.
