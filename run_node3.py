"""
run_node3.py – Refinery Node  (highest hash power = 40%)
Hash Power: 40%
Role: Refining, quality certification, product distribution
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
    port         = 9003,
    seed_list    = SEED_LIST,
    hash_power   = 40.0,   # dominates mining
    interarrival = 15.0,
)
node.start(seed_tx_count=7, tx_gen_interval=15) #15

while True:
    time.sleep(5)
    print(f"[NODE 9003] Chain height={len(node.blockchain.chain)} "
          f"mempool={node.mempool.size()} "
          f"pending={len(node.pending_queue)}")
