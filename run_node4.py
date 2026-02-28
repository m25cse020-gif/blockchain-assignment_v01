"""
run_node4.py – Trading Desk Node
Hash Power: 5%
Role: Invoice, payment, letter-of-credit transactions
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
    port         = 9004,
    seed_list    = SEED_LIST,
    hash_power   = 5.0,
    interarrival = 15.0,
)
node.start(seed_tx_count=4, tx_gen_interval=25) #25

while True:
    time.sleep(5)
    print(f"[NODE 9004] Chain height={len(node.blockchain.chain)} "
          f"mempool={node.mempool.size()} "
          f"pending={len(node.pending_queue)}")
