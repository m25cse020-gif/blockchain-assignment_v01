import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transaction import Transaction
from core.crypto_identity import generate_keypair


def simulate_double_spend():

    # create producer + 2 refineries
    sk, pk = generate_keypair()
    refineryA = "0xAAA1"
    refineryB = "0xBBB2"

    # SAME asset twice
    tx1 = Transaction(sk, pk, refineryA, "100 barrels")
    tx2 = Transaction(sk, pk, refineryB, "100 barrels")

    ledger = {}
    
    for tx in [tx1, tx2]:
        asset = tx.data
        
        if asset in ledger:
            print("❌ DOUBLE SPEND DETECTED")
            print("Previous:", ledger[asset])
            print("New     :", tx.txid)
        else:
            ledger[asset] = tx.txid
            print("✅ Transaction accepted:", tx.txid)


if __name__ == "__main__":
    simulate_double_spend()