import socket
import threading
import json
import sys

peers = set()


def handle_client(conn):
    """
    Handles incoming connections from Peer Nodes. 
    Manages both new peer registration and liveness reporting.
    """
    global peers

    data = conn.recv(1024).decode()

    # DEAD NODE REPORT
    if data.startswith("Dead Node"):
        print("[SEED] DEAD REPORT:", data)
        conn.close()
        return

    # NORMAL REGISTRATION
    try:
        peer = json.loads(data)
        peers.add((peer["host"], peer["port"]))
        conn.send(json.dumps(list(peers)).encode())
    except:
        pass

    conn.close()


def start_seed(host, port):
    """
    Initializes the Seed Node server using Socket Programming.
    The seed acts as a bootstrapping point for the petroleum supply chain ledger.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()

    print(f"[SEED] Running on {host}:{port}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    start_seed("127.0.0.1", port)