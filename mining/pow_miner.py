"""
pow_miner.py – Proof-of-Work miner (assignment Block Mining spec)
=================================================================
The assignment specifies:

  meanTk  = 1.0 / interarrival_time
  lambda  = nodeHashPower * meanTk / 100.0
  Tk      = random.expovariate(lambda)

State machine
-------------
IDLE  ──mine()──►  MINING  ──timer_fires()──►  returns True
                     │
                abort() called
                     │
                     ▼
                  returns False

Thread safety: `abort_event` is a threading.Event; safe to set from
any thread (e.g. network handler receiving a better block).
"""

import random
import threading
import time


class Miner:
    """
    Simulates one node's PoW mining process.

    Parameters
    ----------
    hash_power   : float  – percentage of total network hash power (0–100)
    interarrival : float  – target network-wide average block interval (seconds)
    """

    def __init__(self, hash_power: float = 20.0, interarrival: float = 15.0):
        if not (0 < hash_power <= 100):
            raise ValueError("hash_power must be in (0, 100]")
        if interarrival <= 0:
            raise ValueError("interarrival must be positive")

        self.hash_power   = hash_power
        self.interarrival = interarrival

        # threading.Event used to signal abort from outside
        self.abort_event  = threading.Event()

        # Diagnostics (populated after each mine() call)
        self.last_lambda   = None
        self.last_tau      = None
        self.last_outcome  = None   # 'mined' | 'aborted'

    # ------------------------------------------------------------------
    # Lambda / waiting time helpers (public – used by tests & plots)
    # ------------------------------------------------------------------

    @property
    def lam(self) -> float:
        """
        Per-node lambda = nodeHashPower * meanTk / 100.0
        where meanTk = 1 / interarrival_time
        """
        meanTk = 1.0 / self.interarrival
        return (self.hash_power * meanTk) / 100.0

    def sample_wait_time(self) -> float:
        """
        Draw one exponential waiting time tau ~ Exp(lambda).
        Expected value = 1/lambda = interarrival / (hash_power/100).
        """
        return random.expovariate(self.lam)

    # ------------------------------------------------------------------
    # Core mining method
    # ------------------------------------------------------------------

    def mine(self) -> bool:
        """
        Block until either:
          (a) tau seconds elapse  -> returns True  ('mined')
          (b) abort() is called   -> returns False ('aborted')
        """
        self.abort_event.clear()

        tau = self.sample_wait_time()
        self.last_lambda = self.lam
        self.last_tau    = tau

        print(f"  [MINER] lambda={self.lam:.6f}  tau={tau:.2f}s  "
              f"hash_power={self.hash_power}%")

        deadline = time.time() + tau

        while time.time() < deadline:
            # Poll abort every 100 ms for responsiveness
            if self.abort_event.wait(timeout=0.1):
                self.last_outcome = "aborted"
                print(f"  [MINER] Mining aborted (received longer chain)")
                return False

        self.last_outcome = "mined"
        print(f"  [MINER] Block found after tau={tau:.2f}s")
        return True

    def abort(self):
        """
        Signal that a block has been received from the network that
        creates a longer chain -> abort the current mining round.
        Thread-safe.
        """
        self.abort_event.set()
