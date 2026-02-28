import json
from core.block import Block


class Blockchain:
    """
    Manages the petroleum supply chain ledger.
    Handles block sequencing, persistence, and chain height synchronization.
    """
    def __init__(self):
        self.chain = []
        self.load()

        if not self.chain:
            self.create_genesis()

    # -------- Genesis --------
    def create_genesis(self):
        """
        Generates the initial block (B0) of the network.
        This serves as the foundation for the petroleum ledger.
        """
        genesis = Block("0", [])
        self.chain.append(genesis)
        self.save()

    # -------- Add Block --------
    def add_block(self, transactions):
        """
        Finalizes the mining process by creating a new block.
        Links the new block to the hash of the current 'Longest Chain' tip.
        """
        prev_hash = self.chain[-1].hash
        new_block = Block(prev_hash, transactions)
        self.chain.append(new_block)
        self.save()
        return new_block

    # -------- Save to Disk --------
    def save(self):
        """
        Database Persistence: 
        Saves the current state of the blockchain to a JSON-based database.
        """
        data = [block.to_dict() for block in self.chain]

        with open("blockchain_db.json", "w") as f:
            json.dump(data, f)

    # -------- Load from Disk --------
    def load(self):
        """
        Retrieves the ledger from the database to resume 
        participation in the P2P network after a restart.
        """
        try:
            with open("blockchain_db.json", "r") as f:
                data = json.load(f)

            self.chain = [Block.from_dict(b) for b in data]

        except:
            self.chain = []

    # -------- Height --------
    def height(self):
        """
        Returns the current height (k) of the blockchain.
        Used by new nodes (N) to determine synchronization requirements.
        """
        return len(self.chain)

    # -------- Show --------
    def show_chain(self):
        """
        Utility function to visualize the current state of the trusted ledger.
        Displays the 'Public Trusted Bulletin Board'.
        """
        print("\n======= BLOCKCHAIN =======")
        for i, block in enumerate(self.chain):
            print(f"\nBlock {i}")
            block.show()
        print("===========================\n")