import hashlib
import secrets


def commit(m):
    r = secrets.token_hex(8)
    c = hashlib.sha256((m + r).encode()).hexdigest()
    return c, r


def verify(c, m, r):
    check = hashlib.sha256((m + r).encode()).hexdigest()
    return check == c


# simulate
message = "100 barrels"

commitment, nonce = commit(message)

print("Commitment:", commitment)

# reveal phase
result = verify(commitment, message, nonce)

print("Verification:", result)
