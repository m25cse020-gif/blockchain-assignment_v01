import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transaction import Transaction
from core.crypto_identity import generate_keypair
from core.merkle import merkle_root, merkle_proof

# generate identity
sk, pk = generate_keypair()

# create 8 transactions
txs = [Transaction(sk, pk, "0xABCD", f"tx{i}") for i in range(8)]

# extract txids
txids = [tx.txid for tx in txs]

# build merkle tree
root = merkle_root(txids)

# proof for 4th transaction (index 3)
proof = merkle_proof(txids, 3)

print("Merkle Root:", root)
print("\nProof Path:")
for p in proof:
    print(p)