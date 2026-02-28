from core.crypto_identity import generate_keypair
from core.transaction import Transaction

skA, pkA = generate_keypair()
skB, pkB = generate_keypair()

addrB = "0x1234"

tx = Transaction(skA, pkA, addrB, "100 barrels delivered")

tx.show()

print("Valid:", tx.verify())