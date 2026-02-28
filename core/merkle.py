import hashlib


def hash_pair(a, b):
    return hashlib.sha256((a + b).encode()).hexdigest()


def merkle_root(txids):

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
