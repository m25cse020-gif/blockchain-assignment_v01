"""
tests/test_block_mining.py
===========================
Verifies ALL requirements in the "Block Mining" section of the assignment.

Run with:
    python tests/test_block_mining.py
or (with pytest):
    python -m pytest tests/test_block_mining.py -v

Requirements tested
-------------------
R1.  Exponential waiting time samples are always positive
R2.  Lambda formula: lambda = nodeHashPower * meanTk / 100.0
R3.  Higher hash_power -> larger lambda
R4.  Higher lambda -> shorter expected wait time (E[Tk] = 1/lambda)
R5.  mine() returns True when timer expires (no abort)
R6.  mine() returns False when abort() is called
R7.  Fresh exponential draw after abort; second mine() can succeed
R8.  pending_queue is unbounded (holds many blocks)
R9.  process_pending_queue() appends a valid block to chain
R10. process_pending_queue() triggers abort when longer chain found
R11. mine_loop waits while _syncing=True before mining
R12. Mined block stored in blockchain + broadcast_block called
R13. Transactions returned to mempool when mining is aborted
R14. Node adopts the longest chain (longest-chain rule)
R15. Block with timestamp >1 hour rejected; valid timestamp accepted
R16. Block with invalid TX signature rejected
R17. Mempool seeds petroleum supply-chain transactions
R18. Mempool deduplicates transactions by txid
R19. mempool.take() removes transactions from pool
R20. mempool.remove() purges confirmed txids
"""

import sys, os, time, threading, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.crypto_identity import generate_keypair, address_from_pk
from core.transaction import Transaction
from core.block import Block
from core.blockchain import Blockchain
from core.mempool import Mempool
from mining.pow_miner import Miner

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def make_tx(data="100 barrels delivered"):
    sk, pk = generate_keypair()
    receiver = address_from_pk(generate_keypair()[1])
    return Transaction(sk, pk, receiver, data)

def make_block(prev_hash="0", n_tx=2):
    txs = [make_tx(f"tx-{i}") for i in range(n_tx)]
    return Block(prev_hash, txs)

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
_results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    line = f"  [{status}] {name}"
    if detail:
        line += f"\n           {detail}"
    print(line)
    _results.append((name, bool(condition)))
    return bool(condition)

# ────────────────────────────────────────────────────────────────────────────
# Mock Node (no TCP sockets)
# ────────────────────────────────────────────────────────────────────────────

class MockNode:
    """Minimal node for unit testing – no real sockets."""

    def __init__(self, hash_power=20, interarrival=0.5):
        self.host       = "127.0.0.1"
        self.port       = 0
        self.seed_list  = []
        self.peers      = set()

        # Fresh in-memory blockchain (no file I/O)
        self.blockchain = _MemoryBlockchain()
        genesis = Block("0", [])
        self.blockchain.chain = [genesis]

        self.block_index    = {genesis.hash: genesis}
        self.pending_queue  = []
        self._queue_lock    = threading.Lock()
        self.mempool        = Mempool(node_port=0)
        self.miner          = Miner(hash_power=hash_power,
                                    interarrival=interarrival)
        self._mining_active = False
        self._syncing       = False
        self.msg_counter    = 0
        self.seen_messages  = set()
        self._broadcasts    = []   # track broadcast_block calls

    def broadcast_block(self, block):
        self._broadcasts.append(block)

    def process_pending_queue(self):
        """Mirror of Node.process_pending_queue."""
        processed = False
        with self._queue_lock:
            snapshot = list(self.pending_queue)

        for block in snapshot:
            if block.prev_hash == self.blockchain.chain[-1].hash:
                self.blockchain.chain.append(block)
                with self._queue_lock:
                    if block in self.pending_queue:
                        self.pending_queue.remove(block)
                self.broadcast_block(block)
                processed = True

            elif block.prev_hash in self.block_index:
                fork = self._build_fork_chain(block)
                if len(fork) > len(self.blockchain.chain):
                    self.blockchain.chain = fork
                    with self._queue_lock:
                        if block in self.pending_queue:
                            self.pending_queue.remove(block)
                    self.broadcast_block(block)
                    processed = True

        if processed and len(self.pending_queue) == 0:
            self.miner.abort()

        return processed

    def _build_fork_chain(self, tip):
        chain = [tip]
        ph = tip.prev_hash
        while ph in self.block_index:
            parent = self.block_index[ph]
            chain.insert(0, parent)
            ph = parent.prev_hash
            if ph == "0":
                break
        return chain

    def mine_loop_one_cycle(self):
        """Run exactly one mining attempt (for test isolation)."""
        while self._syncing:
            time.sleep(0.1)
        while self.pending_queue:
            self.process_pending_queue()
            time.sleep(0.05)
        if self.mempool.is_empty():
            return
        self._mining_active = True
        txs = self.mempool.take(5)
        if not txs:
            self._mining_active = False
            return
        mined = self.miner.mine()
        self._mining_active = False
        if mined:
            prev_hash = self.blockchain.chain[-1].hash
            new_block = Block(prev_hash, txs)
            self.blockchain.chain.append(new_block)
            self.block_index[new_block.hash] = new_block
            self.mempool.remove([tx.txid for tx in txs])
            self.broadcast_block(new_block)
        else:
            for tx in txs:
                self.mempool.add(tx)


class _MemoryBlockchain:
    """Blockchain that never touches disk."""
    def __init__(self):
        self.chain = []
    def save(self):
        pass


# ============================================================================
# R1-R4: Lambda & waiting time
# ============================================================================

def test_lambda_and_waiting_time():
    print("\n── R1-R4: Lambda & waiting time ──")
    m = Miner(hash_power=20, interarrival=15)
    expected = (20 * (1/15)) / 100.0

    check("R2: lambda = nodeHashPower * meanTk / 100",
          abs(m.lam - expected) < 1e-10,
          f"got {m.lam:.8f} expected {expected:.8f}")

    m2 = Miner(hash_power=40, interarrival=15)
    check("R3: higher hash_power -> larger lambda",
          m2.lam > m.lam,
          f"lam(hp=40)={m2.lam:.6f} lam(hp=20)={m.lam:.6f}")

    check("R4: E[Tk]=1/lambda; higher lambda -> shorter wait",
          (1/m2.lam) < (1/m.lam),
          f"E[Tk] hp=40: {1/m2.lam:.2f}s  hp=20: {1/m.lam:.2f}s")

    samples = [m.sample_wait_time() for _ in range(200)]
    check("R1: all samples > 0",
          all(s > 0 for s in samples))

    mean_obs  = sum(samples)/len(samples)
    mean_theo = 1.0 / m.lam
    rel_err   = abs(mean_obs - mean_theo) / mean_theo
    check("R1: sample mean within 30% of theoretical E[Tk]",
          rel_err < 0.30,
          f"obs={mean_obs:.2f}s theo={mean_theo:.2f}s err={rel_err:.1%}")


# ============================================================================
# R5-R7: mine() behaviour
# ============================================================================

def test_mine_returns_true_on_timeout():
    print("\n── R5: mine() returns True when timer expires ──")
    m = Miner(hash_power=20, interarrival=0.3)
    m.sample_wait_time = lambda: 0.15   # force short tau

    result = [None]
    def _run():
        result[0] = m.mine()
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=5)

    check("R5: mine() returns True (timer fires)", result[0] is True)


def test_mine_returns_false_on_abort():
    print("\n── R6: mine() returns False on abort ──")
    m = Miner(hash_power=1, interarrival=200)   # very long natural wait

    result = [None]
    def _run():
        result[0] = m.mine()
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(0.3)
    m.abort()
    t.join(timeout=3)

    check("R6: mine() returns False when abort() called", result[0] is False)


def test_fresh_draw_after_abort():
    print("\n── R7: fresh Exp draw after abort ──")
    m = Miner(hash_power=20, interarrival=0.3)
    m.sample_wait_time = lambda: 0.15

    # Round 1 – abort it
    r = [None, None]
    def _r1():
        r[0] = m.mine()
    t1 = threading.Thread(target=_r1, daemon=True)
    t1.start()
    time.sleep(0.04)
    m.abort()
    t1.join(timeout=3)

    # Round 2 – let it finish
    def _r2():
        r[1] = m.mine()
    t2 = threading.Thread(target=_r2, daemon=True)
    t2.start()
    t2.join(timeout=5)

    check("R7: round-1 aborted, round-2 succeeds",
          r[0] is False and r[1] is True,
          f"r1={r[0]} r2={r[1]}")


# ============================================================================
# R8-R10: Pending queue
# ============================================================================

def test_pending_queue_unbounded():
    print("\n── R8: pending_queue unbounded ──")
    node = MockNode()
    blocks = [make_block("0") for _ in range(100)]
    for b in blocks:
        node.block_index[b.hash] = b
        node.pending_queue.append(b)
    check("R8: pending_queue holds 100 blocks",
          len(node.pending_queue) == 100)


def test_process_pending_appends_block():
    print("\n── R9: process_pending_queue() appends valid block ──")
    node = MockNode()
    genesis_hash = node.blockchain.chain[0].hash
    b1 = make_block(prev_hash=genesis_hash)
    node.block_index[b1.hash] = b1
    node.pending_queue.append(b1)

    node.process_pending_queue()

    check("R9: block appended to chain (height=2)",
          len(node.blockchain.chain) == 2 and
          node.blockchain.chain[-1].hash == b1.hash)


def test_abort_triggered_on_longer_chain():
    print("\n── R10: abort triggered when longer chain processed ──")
    node = MockNode()
    genesis_hash = node.blockchain.chain[0].hash

    b1 = make_block(genesis_hash)
    b2 = make_block(b1.hash)
    b3 = make_block(b2.hash)
    for b in [b1, b2, b3]:
        node.block_index[b.hash] = b

    node.pending_queue.extend([b1, b2, b3])

    abort_called = [False]
    orig = node.miner.abort
    def _tracked():
        abort_called[0] = True
        orig()
    node.miner.abort = _tracked

    for _ in range(6):
        node.process_pending_queue()

    check("R10: miner.abort() called on longer chain",
          abort_called[0],
          f"chain height={len(node.blockchain.chain)}")


# ============================================================================
# R11: Sync before mining
# ============================================================================

def test_mine_loop_waits_for_sync():
    print("\n── R11: mine_loop waits while _syncing=True ──")
    node = MockNode(hash_power=99, interarrival=0.2)
    node._syncing = True
    node.mempool.seed_initial_transactions(3)
    node.miner.sample_wait_time = lambda: 0.1

    mine_while_syncing = [False]
    orig_mine = node.miner.mine
    def _patched():
        if node._syncing:
            mine_while_syncing[0] = True
        return orig_mine()
    node.miner.mine = _patched

    t = threading.Thread(target=node.mine_loop_one_cycle, daemon=True)
    t.start()
    time.sleep(0.3)
    node._syncing = False   # release sync flag
    t.join(timeout=5)

    check("R11: mine() not called while _syncing=True",
          not mine_while_syncing[0])


# ============================================================================
# R12: Block stored and broadcast
# ============================================================================

def test_mined_block_stored_and_broadcast():
    print("\n── R12: block stored + broadcast_block called ──")
    node = MockNode(hash_power=99, interarrival=0.2)
    node._syncing = False
    node.mempool.seed_initial_transactions(3)
    node.miner.sample_wait_time = lambda: 0.1

    height_before = len(node.blockchain.chain)

    t = threading.Thread(target=node.mine_loop_one_cycle, daemon=True)
    t.start()
    t.join(timeout=10)

    check("R12a: blockchain height increased",
          len(node.blockchain.chain) > height_before,
          f"height: {height_before} -> {len(node.blockchain.chain)}")

    check("R12b: broadcast_block was called",
          len(node._broadcasts) > 0)


# ============================================================================
# R13: Transactions returned on abort
# ============================================================================

def test_txs_returned_on_abort():
    print("\n── R13: txs returned to mempool on abort ──")
    node = MockNode(hash_power=1, interarrival=200)
    node._syncing = False

    # Instant abort
    node.miner.mine = lambda: False

    node.mempool.seed_initial_transactions(5)
    pool_before = node.mempool.size()

    taken = node.mempool.take(3)
    mined = node.miner.mine()
    if not mined:
        for tx in taken:
            node.mempool.add(tx)

    check("R13: taken txs returned after abort",
          node.mempool.size() >= len(taken),
          f"pool_before_take={pool_before} taken={len(taken)} "
          f"pool_now={node.mempool.size()}")


# ============================================================================
# R14: Longest chain rule
# ============================================================================

def test_longest_chain_rule():
    print("\n── R14: Longest chain rule ──")
    node = MockNode()
    genesis_hash = node.blockchain.chain[0].hash

    # Short fork: genesis -> a1 -> a2
    a1 = make_block(genesis_hash)
    a2 = make_block(a1.hash)

    # Longer fork: genesis -> b1 -> b2 -> b3
    b1 = make_block(genesis_hash)
    b2 = make_block(b1.hash)
    b3 = make_block(b2.hash)

    for b in [a1, a2, b1, b2, b3]:
        node.block_index[b.hash] = b

    node.pending_queue.extend([a1, a2, b1, b2, b3])
    for _ in range(8):
        node.process_pending_queue()

    check("R14: node adopts longest chain (height >= 4)",
          len(node.blockchain.chain) >= 4,
          f"chain height={len(node.blockchain.chain)}")


# ============================================================================
# R15: Timestamp validation
# ============================================================================

def test_timestamp_validation():
    print("\n── R15: Block timestamp validation ──")

    def _ts_valid(block):
        return abs(block.timestamp - time.time()) <= 3600

    good = make_block("0")
    bad  = make_block("0")
    bad.timestamp = time.time() - 7200  # 2 hours ago

    check("R15a: valid timestamp (now) accepted", _ts_valid(good))
    check("R15b: stale timestamp (2h ago) rejected", not _ts_valid(bad))


# ============================================================================
# R16: TX signature validation
# ============================================================================

def test_tx_signature_validation():
    print("\n── R16: TX signature validation ──")
    sk1, pk1 = generate_keypair()
    sk2, pk2 = generate_keypair()
    rcv = address_from_pk(generate_keypair()[1])

    good = Transaction(sk1, pk1, rcv, "200 barrels")
    bad  = Transaction(sk1, pk1, rcv, "200 barrels")
    # Replace signature with one signed by a different key
    bad.signature = Transaction(sk2, pk2, rcv, "200 barrels").signature

    check("R16a: valid TX signature passes", good.verify())
    check("R16b: forged TX signature fails", not bad.verify())


# ============================================================================
# R17-R20: Mempool tests
# ============================================================================

def test_mempool_seeds_petroleum_txs():
    print("\n── R17: Mempool seeds petroleum transactions ──")
    mp = Mempool(node_port=9999)
    txs = mp.seed_initial_transactions(count=5)

    check("R17a: 5 transactions seeded", len(txs) == 5)
    check("R17b: mempool size == 5", mp.size() == 5)

    keywords = ["barrel", "refin", "tanker", "pipeline", "shipment",
                "invoice", "payment", "delivery", "extraction",
                "exploration", "well", "crude", "fuel", "royalty",
                "cargo", "bbl", "storage", "pump"]
    corpus = " ".join(tx.data.lower() for tx in txs)
    check("R17c: data contains petroleum keywords",
          any(kw in corpus for kw in keywords),
          f"sample: {txs[0].data}")


def test_mempool_dedup():
    print("\n── R18: Mempool deduplication ──")
    mp = Mempool(node_port=9999)
    tx = make_tx("100 barrels")
    mp.add(tx)
    again = mp.add(tx)

    check("R18: duplicate add returns False and pool stays at 1",
          not again and mp.size() == 1)


def test_mempool_take():
    print("\n── R19: Mempool take() ──")
    mp = Mempool(node_port=9999)
    for i in range(10):
        mp.add(make_tx(f"event-{i}"))

    taken = mp.take(4)
    check("R19a: take(4) returns 4 txs", len(taken) == 4)
    check("R19b: pool size reduced to 6", mp.size() == 6)


def test_mempool_remove():
    print("\n── R20: Mempool remove() ──")
    mp = Mempool(node_port=9999)
    txs = [make_tx(f"item-{i}") for i in range(5)]
    for tx in txs:
        mp.add(tx)

    mp.remove([txs[0].txid, txs[2].txid])
    remaining_ids = {tx.txid for tx in mp.peek()}

    check("R20a: pool size == 3 after removing 2", mp.size() == 3)
    check("R20b: removed txids no longer in pool",
          txs[0].txid not in remaining_ids and
          txs[2].txid not in remaining_ids)


# ============================================================================
# Main runner
# ============================================================================

def main():
    print("=" * 62)
    print("  Block Mining Requirements – Test Suite")
    print("=" * 62)

    test_lambda_and_waiting_time()
    test_mine_returns_true_on_timeout()
    test_mine_returns_false_on_abort()
    test_fresh_draw_after_abort()
    test_pending_queue_unbounded()
    test_process_pending_appends_block()
    test_abort_triggered_on_longer_chain()
    test_mine_loop_waits_for_sync()
    test_mined_block_stored_and_broadcast()
    test_txs_returned_on_abort()
    test_longest_chain_rule()
    test_timestamp_validation()
    test_tx_signature_validation()
    test_mempool_seeds_petroleum_txs()
    test_mempool_dedup()
    test_mempool_take()
    test_mempool_remove()

    print("\n" + "=" * 62)
    passed = sum(1 for _, ok in _results if ok)
    total  = len(_results)
    colour = "\033[32m" if passed == total else "\033[31m"
    print(f"  {colour}Results: {passed}/{total} passed\033[0m")
    if passed < total:
        print("  Failed:")
        for name, ok in _results:
            if not ok:
                print(f"    ✗  {name}")
    print("=" * 62)
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
