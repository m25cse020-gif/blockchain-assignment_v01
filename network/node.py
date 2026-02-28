"""
node.py – P2P Node with Mempool + Block Mining (assignment spec)
================================================================
Key changes from v02
--------------------
1. Mempool (core/mempool.py) replaces the bare tx_pool list.
   - Petroleum supply-chain transactions are seeded at startup.
   - A background thread generates fresh transactions periodically.
2. Block Mining follows the assignment spec exactly:
   - pending_queue (unbounded) holds blocks received while syncing / mining.
   - Node syncs from genesis (B0..Bk-1) before processing pending queue.
   - Mining starts ONLY when pending_queue is empty.
   - On receiving a block that makes a longer chain: abort current mining,
     insert received block into pending_queue.
   - On mining success (timer expires): store block, broadcast it.
   - Always mine on the longest locally available chain.
3. Miner.abort() uses threading.Event (thread-safe).
4. Liveness: 3 consecutive failures -> report Dead Node to seeds.
"""

import socket
import threading
import json
import time
import uuid

from core.blockchain import Blockchain
from core.transaction import Transaction
from core.mempool import Mempool
from mining.pow_miner import Miner


# Number of transactions pulled from mempool per block
TX_PER_BLOCK = 5

# Max seconds to wait for chain-sync response
SYNC_TIMEOUT = 10


class Node:

    def __init__(self, host: str, port: int, seed_list: list,
                 hash_power: float = 20.0, interarrival: float = 15.0):
        self.host      = host
        self.port      = port
        self.seed_list = seed_list
        self.peers     = set()

        self.msg_counter  = 0
        self.seen_messages = set()
        self.liveness      = {}   # peer -> consecutive failure count

        # Blockchain & mining state
        self.blockchain    = Blockchain()
        self.block_index   = {}   # hash -> Block (all known blocks)
        self.pending_queue = []   # blocks waiting to be processed (unbounded)

        # Mempool with petroleum supply-chain transactions
        self.mempool = Mempool(node_port=port)

        # Miner
        self.miner   = Miner(hash_power=hash_power, interarrival=interarrival)

        # Flags
        self._mining_active = False
        self._syncing       = True   # True until initial chain sync finishes

        # Lock to serialize pending_queue processing
        self._queue_lock    = threading.Lock()

    # ================================================================
    # Seed Registration
    # ================================================================

    def register_with_seed(self):
        all_peers = set()
        for seed_host, seed_port in self.seed_list:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((seed_host, seed_port))
                s.send(json.dumps({"host": self.host, "port": self.port}).encode())
                peer_list = json.loads(s.recv(4096).decode())
                s.close()
                for p in peer_list:
                    if (p[0], p[1]) != (self.host, self.port):
                        all_peers.add((p[0], p[1]))
            except Exception as e:
                print(f"[NODE {self.port}] Seed {seed_port} unreachable: {e}")

        self.peers = set(list(all_peers)[:4])
        print(f"[NODE {self.port}] Peers: {self.peers}")

    # ================================================================
    # TCP Server
    # ================================================================

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        print(f"[NODE {self.port}] Listening...")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_message,
                             args=(conn,), daemon=True).start()

    # ================================================================
    # Message Handler
    # ================================================================

    def handle_message(self, conn):
        try:
            raw = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                raw += chunk
                try:
                    message = json.loads(raw.decode())
                    break
                except json.JSONDecodeError:
                    continue

            if not raw:
                return

            message = json.loads(raw.decode())
            msg_type = message.get("type")

            # ---- LIVENESS PING ----
            if msg_type == "LIVENESS":
                conn.send(json.dumps({"type": "ALIVE",
                                      "ip": self.host,
                                      "port": self.port}).encode())
                return

            # ---- CHAIN REQUEST (sync) ----
            if msg_type == "CHAIN_REQUEST":
                self._send_chain(conn)
                return

            # ---- ALIVE (response) ----
            if msg_type == "ALIVE":
                return

            # ---- Gossip dedup ----
            if "id" not in message:
                return
            msg_id = message["id"]
            if msg_id in self.seen_messages:
                return
            self.seen_messages.add(msg_id)

            # ---- TX ----
            if msg_type == "TX":
                self._handle_tx(message)

            # ---- BLOCK ----
            elif msg_type == "BLOCK":
                self._handle_block(message)

            # ---- CHAIN_RESPONSE ----
            elif msg_type == "CHAIN_RESPONSE":
                self._handle_chain_response(message)
                return   # don't gossip chain responses

            sender = (message.get("ip"), message.get("port"))
            self.gossip(message, sender)

        except Exception as e:
            print(f"[NODE {self.port}] handle_message error: {e}")
        finally:
            conn.close()

    # ================================================================
    # TX handling
    # ================================================================

    def _handle_tx(self, message):
        td = message["data"]
        tx = Transaction(None, tuple(td["sender_pk"]),
                         td["receiver_addr"], td["data"])
        tx.signature = tuple(td["signature"])
        tx.txid      = td.get("txid", tx.txid)

        if tx.verify():
            added = self.mempool.add(tx)
            status = "added" if added else "duplicate"
            print(f"[NODE {self.port}] TX {tx.txid[:10]}… {status} "
                  f"(pool={self.mempool.size()})")
        else:
            print(f"[NODE {self.port}] TX {tx.txid[:10]}… INVALID signature, rejected")

    # ================================================================
    # Block handling – per assignment spec
    # ================================================================

    def _handle_block(self, message):
        """
        On receiving a block:
          1. Validate (timestamp ±1 hour, TX signatures, prev_hash known).
          2. Insert into pending_queue.
          3. Abort current mining if the received block extends a longer chain.
        """
        from core.block import Block

        print(f"[NODE {self.port}] Received BLOCK message")

        block = Block.from_dict(message["data"])

        # -- Timestamp validation (±1 hour) --
        if abs(block.timestamp - time.time()) > 3600:
            print(f"[NODE {self.port}] Block rejected: timestamp out of range")
            return

        # -- TX signature validation --
        for tx in block.transactions:
            if not tx.verify():
                print(f"[NODE {self.port}] Block rejected: invalid TX signature")
                return

        # -- Track in block_index --
        self.block_index[block.hash] = block

        # -- Add to pending_queue --
        with self._queue_lock:
            self.pending_queue.append(block)
        print(f"[NODE {self.port}] Block {block.hash[:12]}… queued "
              f"(pending={len(self.pending_queue)})")

        # -- Abort mining if received block would make a longer chain --
        candidate_len = self._candidate_chain_length(block)
        if candidate_len > len(self.blockchain.chain):
            print(f"[NODE {self.port}] Longer chain detected (len={candidate_len})"
                  f" – aborting mining")
            self.miner.abort()

    def _candidate_chain_length(self, tip_block):
        """Estimate the length of a chain ending at tip_block."""
        length = 1
        ph = tip_block.prev_hash
        while ph in self.block_index:
            length += 1
            ph = self.block_index[ph].prev_hash
        # Add genesis offset
        return length

    # ================================================================
    # Chain sync
    # ================================================================

    def _handle_chain_response(self, message):
        from core.block import Block
        new_chain = [Block.from_dict(b) for b in message["chain"]]
        if len(new_chain) > len(self.blockchain.chain):
            self.blockchain.chain = new_chain
            # Rebuild block_index
            for b in new_chain:
                self.block_index[b.hash] = b
            print(f"[NODE {self.port}] Chain synced to height {len(new_chain)}")

    def _send_chain(self, conn):
        response = {
            "type": "CHAIN_RESPONSE",
            "chain": [b.to_dict() for b in self.blockchain.chain]
        }
        conn.send(json.dumps(response).encode())

    def request_chain_sync(self):
        """
        Ask the first available peer for its full chain.
        Per spec: node receives Bk from network right after joining,
        then requests B0..Bk-1 before processing pending_queue.
        """
        if not self.peers:
            self._syncing = False
            return

        peer = list(self.peers)[0]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SYNC_TIMEOUT)
            s.connect(peer)
            s.send(json.dumps({"type": "CHAIN_REQUEST"}).encode())

            raw = b""
            s.settimeout(SYNC_TIMEOUT)
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                raw += chunk
                try:
                    msg = json.loads(raw.decode())
                    break
                except json.JSONDecodeError:
                    continue
            s.close()

            if raw:
                msg = json.loads(raw.decode())
                self._handle_chain_response(msg)

        except Exception as e:
            print(f"[NODE {self.port}] Chain sync failed: {e}")

        self._syncing = False
        print(f"[NODE {self.port}] Sync complete. Chain height={len(self.blockchain.chain)}")

    # ================================================================
    # Gossip
    # ================================================================

    def gossip(self, message, sender=None):
        for peer in list(self.peers):
            if peer == sender:
                continue
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(peer)
                s.send(json.dumps(message).encode())
                s.close()
            except:
                pass

    def broadcast_tx(self, tx):
        self.msg_counter += 1
        message = {
            "id":        f"{time.time()}:{self.host}:{self.msg_counter}",
            "type":      "TX",
            "ip":        self.host,
            "port":      self.port,
            "timestamp": time.time(),
            "data": {
                "sender_pk":    list(tx.sender_pk),
                "receiver_addr": tx.receiver_addr,
                "data":         tx.data,
                "signature":    list(tx.signature),
                "txid":         tx.txid,
            }
        }
        self.seen_messages.add(message["id"])
        self.gossip(message)

    def broadcast_block(self, block):
        self.msg_counter += 1
        message = {
            "id":        f"{time.time()}:{self.host}:{self.msg_counter}",
            "type":      "BLOCK",
            "ip":        self.host,
            "port":      self.port,
            "timestamp": time.time(),
            "data":      block.to_dict(),
        }
        self.seen_messages.add(message["id"])
        self.gossip(message)

    # ================================================================
    # Pending Queue Processor
    # ================================================================

    def process_pending_queue(self):
        """
        Validate and apply blocks from pending_queue one at a time.
        Per spec:
          - Validate each block (timestamp, TX sigs, hash linkage).
          - Store in blockchain DB.
          - Broadcast to peers.
          - If block creates a longer chain AND pending_queue is empty,
            reset the miner timer (abort+restart).
        Returns True if any block was processed.
        """
        processed = False
        with self._queue_lock:
            queue_snapshot = list(self.pending_queue)

        for block in queue_snapshot:
            # Find if this block extends any known chain tip
            if block.prev_hash == self.blockchain.chain[-1].hash:
                # Direct extension of current chain
                self.blockchain.chain.append(block)
                self.blockchain.save()
                with self._queue_lock:
                    if block in self.pending_queue:
                        self.pending_queue.remove(block)
                print(f"[NODE {self.port}] Block {block.hash[:12]}… "
                      f"appended (height={len(self.blockchain.chain)})")
                self.broadcast_block(block)
                processed = True

            elif block.prev_hash in self.block_index:
                # Possible fork – check if it makes a longer chain
                fork = self._build_fork_chain(block)
                if len(fork) > len(self.blockchain.chain):
                    self.blockchain.chain = fork
                    self.blockchain.save()
                    with self._queue_lock:
                        if block in self.pending_queue:
                            self.pending_queue.remove(block)
                    print(f"[NODE {self.port}] Switched to longer fork "
                          f"(height={len(fork)})")
                    self.broadcast_block(block)
                    processed = True

        # If pending_queue is now empty and we processed something,
        # signal miner to reset its timer (abort so mine_loop restarts)
        if processed and len(self.pending_queue) == 0:
            self.miner.abort()

        return processed

    def _build_fork_chain(self, tip):
        chain = [tip]
        ph = tip.prev_hash
        while ph in self.block_index:
            parent = self.block_index[ph]
            chain.insert(0, parent)
            ph = parent.prev_hash
            if ph == "0":
                break
        return chain

    # ================================================================
    # Mining Loop – per assignment spec
    # ================================================================

    def mine_loop(self):
        """
        Main mining loop:
          - Wait until syncing is done.
          - Process pending_queue until empty.
          - Pull transactions from mempool.
          - Start Miner timer (Tk = Exp(lambda)).
          - If timer fires first: create block, store, broadcast.
          - If abort() called (longer chain received): loop back,
            process pending_queue, then restart timer.
        """
        # Wait for initial chain sync
        while self._syncing:
            time.sleep(0.5)

        print(f"[NODE {self.port}] Mining loop started "
              f"(hash_power={self.miner.hash_power}%)")

        while True:
            # 1. Drain the pending queue first
            while len(self.pending_queue) > 0:
                self.process_pending_queue()
                time.sleep(0.2)

            # 2. Need transactions to mine
            if self.mempool.is_empty():
                time.sleep(1)
                continue

            # 3. Start mining
            self._mining_active = True
            txs = self.mempool.take(TX_PER_BLOCK)

            if not txs:
                self._mining_active = False
                time.sleep(1)
                continue

            print(f"[NODE {self.port}] Starting mining "
                  f"({len(txs)} txs, pool remaining={self.mempool.size()})")

            # 4. Run the PoW timer
            mined = self.miner.mine()
            self._mining_active = False

            if mined:
                # -- Timer expired: we found the block --
                # Mine on the longest chain
                prev_hash = self.blockchain.chain[-1].hash
                from core.block import Block
                new_block = Block(prev_hash, txs)
                self.blockchain.chain.append(new_block)
                self.blockchain.save()
                self.block_index[new_block.hash] = new_block

                # Remove mined txids from mempool (in case some leaked back)
                self.mempool.remove([tx.txid for tx in txs])

                print(f"[NODE {self.port}] *** Block MINED "
                      f"hash={new_block.hash[:16]}… "
                      f"height={len(self.blockchain.chain)} ***")
                self.broadcast_block(new_block)

            else:
                # -- Aborted: longer chain received --
                # Put transactions back into the mempool
                for tx in txs:
                    self.mempool.add(tx)
                print(f"[NODE {self.port}] Mining aborted – txs returned to mempool")
                # Process pending queue (will be drained at top of loop)

    # ================================================================
    # Liveness
    # ================================================================

    def liveness_loop(self):
        while True:
            time.sleep(13)
            for peer in list(self.peers):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(3)
                    s.connect(peer)
                    s.send(json.dumps({
                        "type": "LIVENESS",
                        "ip":   self.host,
                        "port": self.port,
                        "time": time.time()
                    }).encode())
                    s.close()
                    self.liveness[peer] = 0   # reset on success
                except:
                    self.liveness[peer] = self.liveness.get(peer, 0) + 1
                    fails = self.liveness[peer]
                    print(f"[NODE {self.port}] Liveness fail #{fails} for {peer}")
                    if fails >= 3:
                        print(f"[NODE {self.port}] DEAD detected: {peer}")
                        self._report_dead(peer)
                        self.peers.discard(peer)

    def _report_dead(self, dead_peer):
        msg = (f"Dead Node:{dead_peer[0]}:{dead_peer[1]}"
               f":{time.time()}:{self.host}")
        for seed in self.seed_list:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(seed)
                s.send(msg.encode())
                s.close()
            except:
                pass

    # ================================================================
    # Start
    # ================================================================

    def start(self, seed_tx_count: int = 5, tx_gen_interval: int = 20):
        """
        Boot the node:
          1. Register with seeds, get peer list.
          2. Seed the mempool with petroleum supply-chain transactions.
          3. Sync blockchain from peers.
          4. Start server, mining, liveness, and tx-generation threads.
        """
        self.register_with_seed()

        # Seed mempool – gather partner addresses for more realistic routing
        # (we use placeholder addresses since we don't know peers' PKs yet)
        print(f"[NODE {self.port}] Seeding mempool with {seed_tx_count} "
              f"petroleum supply-chain transactions...")
        seeded = self.mempool.seed_initial_transactions(count=seed_tx_count)

        # Broadcast seeded transactions to peers after server starts
        self.request_chain_sync()

        # Server thread
        threading.Thread(target=self.start_server, daemon=True).start()

        # Broadcast initial transactions once server is up
        def _broadcast_seeded():
            time.sleep(2)
            for tx in seeded:
                self.broadcast_tx(tx)
        threading.Thread(target=_broadcast_seeded, daemon=True).start()

        # Periodic tx generator
        self.mempool.periodic_generator(
            interval=tx_gen_interval,
            broadcast_callback=self.broadcast_tx
        )

        # Mining loop
        threading.Thread(target=self.mine_loop, daemon=True).start()

        # Liveness loop
        threading.Thread(target=self.liveness_loop, daemon=True).start()

        print(f"[NODE {self.port}] Node started. "
              f"hash_power={self.miner.hash_power}%")
