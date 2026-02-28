import hashlib
import secrets

# secp256k1 parameters
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a = 0
b = 7

Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424
G = (Gx, Gy)

n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

INF = (None, None)


# ---------------- Basic Math ----------------

def mod_inv(x, m):
    return pow(x, -1, m)


def point_add(P, Q):
    if P == INF:
        return Q
    if Q == INF:
        return P

    x1, y1 = P
    x2, y2 = Q

    if x1 == x2 and y1 != y2:
        return INF

    if P == Q:
        lam = (3 * x1 * x1) * mod_inv(2 * y1, p) % p
    else:
        lam = (y2 - y1) * mod_inv(x2 - x1, p) % p

    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p

    return (x3, y3)


def scalar_mult(k, P):
    result = INF
    addend = P

    while k > 0:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


# ---------------- Key Generation ----------------

def generate_keypair():
    sk = int(hashlib.sha256(secrets.token_bytes(32)).hexdigest(), 16) % n
    pk = scalar_mult(sk, G)
    return sk, pk


def address_from_pk(pk):
    pk_bytes = str(pk[0]).encode() + str(pk[1]).encode()
    h = hashlib.sha256(pk_bytes).hexdigest()
    return "0x" + h[-4:]


# ---------------- ECDSA ----------------

def sign(msg, sk):
    z = int(hashlib.sha256(msg.encode()).hexdigest(), 16)

    while True:
        k = secrets.randbelow(n)
        x, _ = scalar_mult(k, G)
        r = x % n
        if r == 0:
            continue

        s = (mod_inv(k, n) * (z + r * sk)) % n
        if s == 0:
            continue

        return (r, s)


def verify(msg, signature, pk):
    r, s = signature
    if not (1 <= r < n and 1 <= s < n):
        return False

    z = int(hashlib.sha256(msg.encode()).hexdigest(), 16)

    w = mod_inv(s, n)
    u1 = (z * w) % n
    u2 = (r * w) % n

    P = point_add(scalar_mult(u1, G), scalar_mult(u2, pk))
    if P == INF:
        return False

    return (P[0] % n) == r


# ---------------- Demo ----------------

if __name__ == "__main__":
    sk, pk = generate_keypair()
    addr = address_from_pk(pk)

    print("Private Key:", hex(sk))
    print("Public Key :", pk)
    print("Address    :", addr)

    msg = "100 barrels delivered"
    sig = sign(msg, sk)

    print("\nSignature:", sig)
    print("Verify   :", verify(msg, sig, pk))