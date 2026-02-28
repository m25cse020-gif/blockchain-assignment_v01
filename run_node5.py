"""
run_node5.py – Regulatory / Auditor Node
Hash Power: 5%
Role: Compliance, carbon offset, royalty payment transactions
"""
from network.node import Node
import time

SEED_LIST = [
    ("127.0.0.1", 8000),
    ("127.0.0.1", 8001),
    ("127.0.0.1", 8002),
]

node = Node(
    host         = "127.0.0.1",
    port         = 9005,
    seed_list    = SEED_LIST,
    hash_power   = 5.0,
    interarrival = 15.0,
)
node.start(seed_tx_count=4, tx_gen_interval=30) #30

while True:
    time.sleep(5)
    print(f"[NODE 9005] Chain height={len(node.blockchain.chain)} "
          f"mempool={node.mempool.size()} "
          f"pending={len(node.pending_queue)}")
