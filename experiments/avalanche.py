import hashlib


def sha256_bits(data):
    """
    Computes the SHA-256 hash of a string and returns its 256-bit binary representation.
    This is used to analyze the 'Avalanche Effect' at the bit level.
    """
    h = hashlib.sha256(data.encode()).hexdigest()
    return bin(int(h, 16))[2:].zfill(256)


def bit_difference(a, b):
    """
    Compares two bitstrings and returns the total number of differing bits.
    This quantification helps determine how significantly a small change in 
    input affects the final hash output.
    """
    diff = sum(x != y for x, y in zip(a, b))
    return diff


# original string
s1 = "Pipeline shipment no. 33: 105 barrels shipped"

# small change
s2 = "Pipeline shipment no. 34: 105 barrels shipped"


h1 = sha256_bits(s1)
h2 = sha256_bits(s2)

# Calculate the bitwise difference between the two hashes
diff = bit_difference(h1, h2)
percent = (diff / 256) * 100

print("Bits changed:", diff)
print("Percentage change: %.2f%%" % percent)
