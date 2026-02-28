import hashlib
from core.crypto_identity import sign, verify, address_from_pk


class Transaction:
    """
    Represents a supply chain event or financial transfer within the network.
    This class handles identity derivation, signing, and integrity hashing.
    """
    def __init__(self, sender_sk, sender_pk, receiver_addr, data):
        """
        Initializes the transaction object with cryptographic identities and data.
        
        :param sender_sk: The sender's 256-bit Secret Key (sk).
        :param sender_pk: The sender's Public Key (pk) derived via Double-and-Add.
        :param receiver_addr: The 16-bit hexadecimal identifier of the receiver.
        :param data: Details of the event (e.g., '100 barrels delivered').
        """
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
        """
        Verifies the transaction signature using the sender's public key (pk).
        A valid signature proves the sender authorized the transaction and the 
        data is untampered.
        """
        return verify(self.msg, self.signature, self.sender_pk)

    def show(self):
        """
        Prints the Transaction Object details as per the ledger requirements.
        Displays the 16-bit identifiers, event data, and cryptographic proof.
        """
        print("---- Transaction ----")
        print("From :", self.sender_addr)
        print("To   :", self.receiver_addr)
        print("Data :", self.data)
        print("TxID :", self.txid)
        print("Sig  :", self.signature)
        print("---------------------")