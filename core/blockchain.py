import json
from core.block import Block


class Blockchain:

    def __init__(self):
        self.chain = []
        self.load()

        if not self.chain:
            self.create_genesis()

    # -------- Genesis --------
    def create_genesis(self):
        genesis = Block("0", [])
        self.chain.append(genesis)
        self.save()

    # -------- Add Block --------
    def add_block(self, transactions):
        prev_hash = self.chain[-1].hash
        new_block = Block(prev_hash, transactions)
        self.chain.append(new_block)
        self.save()
        return new_block

    # -------- Save to Disk --------
    def save(self):
        data = [block.to_dict() for block in self.chain]

        with open("blockchain_db.json", "w") as f:
            json.dump(data, f)

    # -------- Load from Disk --------
    def load(self):
        try:
            with open("blockchain_db.json", "r") as f:
                data = json.load(f)

            self.chain = [Block.from_dict(b) for b in data]

        except:
            self.chain = []

    # -------- Height --------
    def height(self):
        return len(self.chain)

    # -------- Show --------
    def show_chain(self):
        print("\n======= BLOCKCHAIN =======")
        for i, block in enumerate(self.chain):
            print(f"\nBlock {i}")
            block.show()
        print("===========================\n")