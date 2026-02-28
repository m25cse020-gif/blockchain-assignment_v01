import hashlib
from core.crypto_identity import sign, verify, address_from_pk


class Transaction:

    def __init__(self, sender_sk, sender_pk, receiver_addr, data):
        self.sender_pk = sender_pk
        self.sender_addr = address_from_pk(sender_pk)
        self.receiver_addr = receiver_addr
        self.data = data

        self.msg = f"{self.sender_addr}:{self.receiver_addr}:{self.data}"

        # Only sign if sender has private key
        if sender_sk is not None:
            self.signature = sign(self.msg, sender_sk)
        else:
            self.signature = None

        self.txid = hashlib.sha256(self.msg.encode()).hexdigest()
    def verify(self):
        return verify(self.msg, self.signature, self.sender_pk)

    def show(self):
        print("---- Transaction ----")
        print("From :", self.sender_addr)
        print("To   :", self.receiver_addr)
        print("Data :", self.data)
        print("TxID :", self.txid)
        print("Sig  :", self.signature)
        print("---------------------")