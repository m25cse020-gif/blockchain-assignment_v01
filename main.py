from core.transaction import Transaction
from core.merkle import merkle_root, merkle_proof
import hashlib

from core.crypto_identity import generate_keypair
from core.transaction import Transaction

sk, pk = generate_keypair()

txs = [Transaction(sk, pk, "0xDEAD", str(i)) for i in range(8)]
txids = [tx.txid for tx in txs]

root = merkle_root(txids)
proof = merkle_proof(txids, 3)   # proof for 4th tx

print("Merkle Root:", root)
print("\nProof Path:")
for p in proof:
    print(p)
