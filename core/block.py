import hashlib
import time
from core.merkle import merkle_root


class Block:

    def __init__(self, prev_hash, transactions):
        self.prev_hash = prev_hash
        self.transactions = transactions
        self.timestamp = time.time()
        

        txids = [tx.txid for tx in transactions] if transactions else []
        self.merkle = merkle_root(txids) if txids else None

        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = f"{self.prev_hash}{self.merkle}{self.timestamp}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "merkle": self.merkle,
            "hash": self.hash,
            "transactions": [
                {
                    "sender_pk": tx.sender_pk,
                    "receiver_addr": tx.receiver_addr,
                    "data": tx.data,
                    "signature": tx.signature,
                    "txid": tx.txid
                }
                for tx in self.transactions
            ]
        }

    @staticmethod
    def from_dict(data):
        from core.transaction import Transaction

        txs = []
        for t in data["transactions"]:
            tx = Transaction(
                None,
                tuple(t["sender_pk"]),
                t["receiver_addr"],
                t["data"]
            )
            tx.signature = tuple(t["signature"])
            tx.txid = t["txid"]
            txs.append(tx)

        block = Block(data["prev_hash"], txs)
        block.timestamp = data["timestamp"]
        block.hash = data["hash"]
        block.merkle = data["merkle"]

        return block