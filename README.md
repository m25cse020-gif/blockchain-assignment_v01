# Blockchain Assignment v03 – Petroleum Supply Chain Ledger

## What's New in v03

### 1. Mempool (`core/mempool.py`)
A thread-safe transaction pool seeded with realistic **petroleum supply-chain events**:
- Upstream: exploration permits, well drilling, crude extraction
- Midstream: pipeline shipments, tanker voyages, storage fills
- Downstream: refinery intake/output, quality certificates, fuel deliveries
- Financial: invoices, payments, letters of credit, royalty payments, carbon offsets

Each node seeds the mempool at startup and continuously generates new transactions in the background.

### 2. Block Mining (assignment spec)
`mining/pow_miner.py` and `network/node.py` now fully implement the spec:

```
meanTk  = 1.0 / interarrival_time
lambda  = nodeHashPower * meanTk / 100.0
Tk      = random.expovariate(lambda)
```

**Node lifecycle:**
1. Register with seeds, get peer list
2. Seed mempool with petroleum transactions
3. **Sync chain** (request B0..Bk from network) before mining
4. **Process pending queue** until empty
5. **Mine** (draw Exp(λ) waiting time)
   - Timer fires → create block, store, broadcast
   - Abort() called (longer chain received) → return txs to mempool, restart
6. Always mine on the **longest chain** available locally

### 3. Node Roles and Hash Powers
| Node | Port | Role | Hash Power |
|------|------|------|-----------|
| node1 | 9001 | Upstream Producer | 30% |
| node2 | 9002 | Pipeline Operator | 20% |
| node3 | 9003 | Refinery (dominant miner) | 40% |
| node4 | 9004 | Trading Desk | 5% |
| node5 | 9005 | Regulatory/Auditor | 5% |

Total hash power = 100%.

---

## How to Run

### Prerequisites
```bash
pip install pytest   # optional, for test runner
```

### Step 1 – Start Seed Nodes (3 terminals)
```bash
python network/seed.py 8000
python network/seed.py 8001
python network/seed.py 8002
```

### Step 2 – Start Peer Nodes (5 terminals)
```bash
python run_node1.py   # Upstream Producer  (30% hash power)
python run_node2.py   # Pipeline Operator  (20% hash power)
python run_node3.py   # Refinery           (40% hash power)
python run_node4.py   # Trading Desk        (5% hash power)
python run_node5.py   # Regulatory/Auditor  (5% hash power)
```

Each node prints its chain height, mempool size, and pending queue depth every 5 seconds.

---

## Running the Tests

```bash
# From the project root
python tests/test_block_mining.py

# Or with pytest
python -m pytest tests/test_block_mining.py -v
```

### Test Coverage (28 tests, all Block Mining requirements)

| Req | Description |
|-----|-------------|
| R1  | Exp samples are positive; mean within 30% of theoretical |
| R2  | Lambda formula: `lambda = nodeHashPower * meanTk / 100` |
| R3  | Higher hash_power → larger lambda |
| R4  | Higher lambda → shorter expected wait |
| R5  | `mine()` returns True when timer expires |
| R6  | `mine()` returns False when `abort()` called |
| R7  | Fresh Exp draw after abort; second mine can succeed |
| R8  | Pending queue is unbounded |
| R9  | `process_pending_queue()` appends valid block |
| R10 | Longer chain arrival aborts current mining |
| R11 | `mine_loop` waits while `_syncing=True` |
| R12 | Mined block stored in chain + broadcast |
| R13 | Transactions returned to mempool on abort |
| R14 | Node adopts longest chain (fork resolution) |
| R15 | Blocks with timestamp ±1 hour: accepted/rejected correctly |
| R16 | Blocks with invalid TX signatures rejected |
| R17 | Mempool seeds petroleum supply-chain transactions |
| R18 | Mempool deduplicates by txid |
| R19 | `mempool.take()` removes transactions from pool |
| R20 | `mempool.remove()` purges confirmed txids |

---

## File Structure
```
core/
  block.py          – Block data structure
  blockchain.py     – Persistent chain
  crypto_identity.py – secp256k1 key gen, ECDSA sign/verify
  mempool.py        – NEW: thread-safe tx pool + petroleum tx generator
  merkle.py         – Merkle tree / proof
  transaction.py    – Signed transaction

mining/
  pow_miner.py      – UPDATED: Miner with Exp(λ) timer + abort event

network/
  node.py           – UPDATED: Full Block Mining spec + mempool integration
  seed.py           – Seed server

tests/
  test_block_mining.py – NEW: 28-requirement test suite

run_node{1-5}.py    – UPDATED: node configs with hash power + roles
experiments/        – Assignment tasks 1-6
plots/              – Task 7 mining analysis
```
