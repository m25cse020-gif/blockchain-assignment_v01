import hashlib
import secrets


def commit(m):
    """
    Implements the 'Exploration' phase of a Bit Commitment Scheme.
    
    The producer commits to a delivery volume 'm' with a random nonce 'r'.
    This ensures the 'Hiding' property: a party can see the commitment hash (C)
    without knowing the actual value 'm'.
    
    :param m: The message (delivery volume) to commit to.
    :return: (c, r) where 'c' is the hash commitment and 'r' is the secret nonce.
    """
    r = secrets.token_hex(8)
    c = hashlib.sha256((m + r).encode()).hexdigest()
    return c, r


def verify(c, m, r):
    """
    Implements the 'Refining' phase where the actual value 'm' is revealed.
    
    This ensures the 'Binding' property: once the commitment 'c' is shared, the 
    producer cannot change the value 'm' without the resulting hash failing to match.
    
    :param c: The original commitment hash shared during the Exploration phase.
    :param m: The revealed delivery volume.
    :param r: The revealed nonce.
    :return: True if the revelation matches the commitment, False otherwise.
    """
    check = hashlib.sha256((m + r).encode()).hexdigest()
    return check == c


# simulate
message = "100 barrels"

commitment, nonce = commit(message)

print("Commitment:", commitment)

# reveal phase
result = verify(commitment, message, nonce)

print("Verification:", result)
