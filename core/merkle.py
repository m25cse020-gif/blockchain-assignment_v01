import hashlib


def hash_pair(a, b):
    """
    Concatenates two hex strings and returns their SHA-256 hash.
    This supports the integrity requirements where TxIDs and block hashes 
    must ensure the 'Avalanche Effect'.
    """
    return hashlib.sha256((a + b).encode()).hexdigest()


def merkle_root(txids):
    """
    Computes the Merkle Root for a list of transaction IDs (TxIDs).
    
    As per Task 2, this root summarizes all transactions in a block.
    The function iteratively hashes pairs of SHA-256 strings until a single 
    representative hash (the root) remains.
    """
    # copy list
    level = txids[:]

    # if empty
    if not level:
        return None

    # loop until single hash
    while len(level) > 1:

        next_level = []

        for i in range(0, len(level), 2):

            left = level[i]

            # duplicate last if odd
            if i + 1 < len(level):
                right = level[i+1]
            else:
                right = left

            next_level.append(hash_pair(left, right))

        level = next_level

    return level[0]


# test run
if __name__ == "__main__":
    txs = ["a", "b", "c", "d"]
    hashed = [hashlib.sha256(x.encode()).hexdigest() for x in txs]

    root = merkle_root(hashed)

    print("Merkle Root:", root)


def merkle_proof(txids, index):
    """
    Generates a Merkle Proof for a specific transaction at a given index.
    
    In the context of the Petroleum Supply Chain Ledger, this allows Light Nodes 
    to verify a transaction's existence without downloading the entire 8-transaction 
    block body.
    """
    proof = []
    level = txids[:]

    while len(level) > 1:

        if index % 2 == 0:
            pair_index = index + 1 if index + 1 < len(level) else index
        else:
            pair_index = index - 1

        proof.append(level[pair_index])

        # build next level
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i+1] if i+1 < len(level) else left
            next_level.append(hash_pair(left, right))

        level = next_level
        index //= 2

    return proof
