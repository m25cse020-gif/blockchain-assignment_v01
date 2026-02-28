"""
mempool.py – Petroleum Supply Chain Mempool
============================================
Maintains a pool of unconfirmed transactions generated from realistic
petroleum supply-chain events (exploration, extraction, transport,
refining, delivery, payment).

Each node holds ONE Mempool instance.  Transactions arrive either:
  • Locally generated (seeded at startup / periodically)
  • Received via gossip from peers

Public interface
----------------
  mempool.add(tx)         -> bool  (True if accepted / False if duplicate)
  mempool.take(n)         -> list[Transaction]  (pop up to n tx for mining)
  mempool.peek()          -> list[Transaction]  (non-destructive)
  mempool.remove(txids)   -> None  (purge confirmed txids after block mined)
  mempool.size()          -> int
"""

import threading
import time
import hashlib
import random

from core.crypto_identity import generate_keypair, address_from_pk
from core.transaction import Transaction


# ---------------------------------------------------------------------------
# Petroleum supply-chain event templates
# ---------------------------------------------------------------------------

_SUPPLY_CHAIN_TEMPLATES = [
    # Upstream – Exploration & Extraction
    "Exploration permit issued for Block-{block_id} in {field}",
    "Seismic survey completed at {field}: {barrels}k barrels estimated",
    "Well #{well_id} spudded at {field}",
    "Well #{well_id} production started: {barrels} bbl/day",
    "Crude extraction report: {barrels} barrels extracted at {field}",

    # Midstream – Transportation
    "Pipeline shipment #{ship_id}: {barrels} barrels from {field} to {refinery}",
    "Tanker {tanker} loaded: {barrels} barrels crude, departing {port}",
    "Tanker {tanker} arrived at {port}: {barrels} barrels unloaded",
    "Pipeline integrity check #{check_id}: status PASS",
    "Storage tank T-{tank_id} filled to {pct}% capacity at {hub}",

    # Downstream – Refining & Distribution
    "Refinery {refinery} intake: {barrels} barrels crude (grade {grade})",
    "Refinery {refinery} output: {product} – {barrels} barrels",
    "Quality certificate QC-{qc_id} issued for {product} batch",
    "Fuel delivery {barrels} liters of {product} to {station}",
    "Export clearance XP-{ship_id}: {barrels} barrels to {dest}",

    # Financial / Commercial
    "Invoice INV-{inv_id}: {barrels} bbl @ ${price}/bbl from {seller} to {buyer}",
    "Payment confirmed: ${amount} for INV-{inv_id}",
    "Letter of credit LC-{lc_id} opened for ${amount}",
    "Royalty payment: ${amount} to government for Q{quarter}",
    "Carbon offset purchase: {carbon_tons} tonnes CO2 credit",
]

# Named entities used to make transactions realistic
_FIELDS      = ["Ghawar", "Prudhoe Bay", "Cantarell", "North Sea", "Permian Basin"]
_REFINERIES  = ["RefineCo Alpha", "PetroRefine Beta", "Gulf Refinery", "Delta Refinery"]
_PORTS       = ["Port Rashid", "Ras Tanura", "Rotterdam", "Houston Ship Channel"]
_PRODUCTS    = ["Gasoline-95", "Diesel B5", "Jet-A1", "Heavy Fuel Oil", "Naphtha"]
_GRADES      = ["Brent", "WTI", "Dubai", "Arab Light"]
_HUBS        = ["Cushing Hub", "Fujairah Hub", "ARA Hub"]
_STATIONS    = ["PetroGas Sta-7", "QuickFuel Sta-12", "EnergyMart Sta-3"]


def _random_tx_data():
    """Return a realistic petroleum supply-chain event string."""
    template = random.choice(_SUPPLY_CHAIN_TEMPLATES)
    return template.format(
        block_id  = random.randint(1, 99),
        well_id   = random.randint(100, 999),
        ship_id   = random.randint(1000, 9999),
        check_id  = random.randint(100, 999),
        tank_id   = random.randint(1, 20),
        inv_id    = random.randint(10000, 99999),
        lc_id     = random.randint(1000, 9999),
        qc_id     = random.randint(100, 999),
        barrels   = random.randint(100, 50000),
        pct       = random.randint(20, 95),
        price     = round(random.uniform(60, 110), 2),
        amount    = random.randint(10000, 5000000),
        quarter   = random.randint(1, 4),
        carbon_tons = random.randint(50, 5000),
        field     = random.choice(_FIELDS),
        refinery  = random.choice(_REFINERIES),
        port      = random.choice(_PORTS),
        tanker    = f"MT-{random.randint(100,999)}",
        product   = random.choice(_PRODUCTS),
        grade     = random.choice(_GRADES),
        hub       = random.choice(_HUBS),
        station   = random.choice(_STATIONS),
        seller    = random.choice(["UpstreamCo", "OilMajor", "Aramco LLC"]),
        buyer     = random.choice(["RefineGroup", "FuelTrader", "GovOilDesk"]),
        dest      = random.choice(["China", "India", "EU", "Japan"]),
    )


# ---------------------------------------------------------------------------
# Mempool
# ---------------------------------------------------------------------------

class Mempool:
    """Thread-safe transaction pool for a single node."""

    def __init__(self, node_port: int, max_size: int = 500):
        self._lock   = threading.Lock()
        self._pool   = {}          # txid -> Transaction (dict preserves insertion order)
        self.max_size   = max_size
        self.node_port  = node_port

        # Each node gets its own identity for generating local transactions
        self._sk, self._pk = generate_keypair()
        self._addr = address_from_pk(self._pk)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add(self, tx: Transaction) -> bool:
        """
        Accept a transaction into the pool.
        Returns True if added, False if duplicate or pool full.
        """
        with self._lock:
            if tx.txid in self._pool:
                return False  # already seen
            if len(self._pool) >= self.max_size:
                return False  # pool full – could implement fee-priority eviction
            self._pool[tx.txid] = tx
            return True

    def take(self, n: int = 10):
        """
        Remove and return up to *n* transactions for inclusion in a block.
        Called by the miner just before sealing a block.
        """
        with self._lock:
            txids = list(self._pool.keys())[:n]
            selected = [self._pool.pop(tid) for tid in txids]
            return selected

    def peek(self):
        """Return a snapshot of the current pool (non-destructive)."""
        with self._lock:
            return list(self._pool.values())

    def remove(self, txids):
        """Purge confirmed transactions after a block is committed."""
        with self._lock:
            for tid in txids:
                self._pool.pop(tid, None)

    def size(self) -> int:
        with self._lock:
            return len(self._pool)

    def is_empty(self) -> bool:
        return self.size() == 0

    # ------------------------------------------------------------------
    # Transaction factory – petroleum supply chain
    # ------------------------------------------------------------------

    def generate_local_tx(self, receiver_addr: str = None) -> Transaction:
        """
        Create and add one randomly generated petroleum supply-chain
        transaction signed with this node's private key.
        """
        if receiver_addr is None:
            # Generate a throw-away receiver address
            _, rpk = generate_keypair()
            receiver_addr = address_from_pk(rpk)

        data = _random_tx_data()
        tx = Transaction(self._sk, self._pk, receiver_addr, data)
        self.add(tx)
        return tx

    def seed_initial_transactions(self, count: int = 5,
                                   partner_addresses: list = None):
        """
        Populate the mempool with *count* petroleum transactions at startup.
        Optionally direct some transactions at known peer addresses.
        """
        partners = partner_addresses or []
        txs = []
        for i in range(count):
            addr = partners[i % len(partners)] if partners else None
            tx = self.generate_local_tx(receiver_addr=addr)
            txs.append(tx)
            print(f"[MEMPOOL {self.node_port}] Seeded TX {tx.txid[:12]}… | {tx.data[:60]}")
        return txs

    def periodic_generator(self, interval: int = 20,
                             partner_addresses: list = None,
                             broadcast_callback=None):
        """
        Background thread: generate one new petroleum supply-chain
        transaction every *interval* seconds.
        Calls broadcast_callback(tx) if provided so the node can gossip it.
        """
        def _loop():
            while True:
                time.sleep(interval)
                tx = self.generate_local_tx(
                    receiver_addr=(random.choice(partner_addresses)
                                   if partner_addresses else None)
                )
                print(f"[MEMPOOL {self.node_port}] New TX {tx.txid[:12]}… "
                      f"pool_size={self.size()} | {tx.data[:60]}")
                if broadcast_callback:
                    broadcast_callback(tx)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return t
