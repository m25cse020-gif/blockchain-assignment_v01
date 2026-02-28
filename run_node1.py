"""
run_node1.py – Upstream Producer Node
Hash Power: 30%
Role: Oil field extraction & shipping transactions
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
    port         = 9001,
    seed_list    = SEED_LIST,
    hash_power   = 30.0,   # 30% of network hash power
    interarrival = 15.0,   # 15-second target block interval
)
node.start(seed_tx_count=6, tx_gen_interval=18) #18

while True:
    time.sleep(5)
    print(f"[NODE 9001] Chain height={len(node.blockchain.chain)} "
          f"mempool={node.mempool.size()} "
          f"pending={len(node.pending_queue)}")
