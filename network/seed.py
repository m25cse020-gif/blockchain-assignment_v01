import socket
import threading
import json
import sys

peers = set()


def handle_client(conn):
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