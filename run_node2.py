"""
run_node2.py – Pipeline Operator Node
Hash Power: 20%
Role: Transport & storage transactions
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
    port         = 9002,
    seed_list    = SEED_LIST,
    hash_power   = 20.0,
    interarrival = 15.0,
)
node.start(seed_tx_count=5, tx_gen_interval=22) #22

while True:
    time.sleep(5)
    print(f"[NODE 9002] Chain height={len(node.blockchain.chain)} "
          f"mempool={node.mempool.size()} "
          f"pending={len(node.pending_queue)}")
