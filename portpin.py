import socket
import threading

LISTEN_IP = "127.0.0.1"
LISTEN_PORT = 13389

SOURCE_IP = "192.168.31.31"
SOURCE_PORT = 40000

REMOTE_IP = "192.168.31.58"
REMOTE_PORT = 3389


def forward(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client):
    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 尽量允许端口快速重复使用
    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # 关键：固定 55 的出站源端口
        remote.bind((SOURCE_IP, SOURCE_PORT))

        print(
            f"Connecting "
            f"{SOURCE_IP}:{SOURCE_PORT} -> "
            f"{REMOTE_IP}:{REMOTE_PORT}"
        )

        remote.connect((REMOTE_IP, REMOTE_PORT))

        print("RDP tunnel connected")

        t1 = threading.Thread(
            target=forward,
            args=(client, remote),
            daemon=True
        )
        t2 = threading.Thread(
            target=forward,
            args=(remote, client),
            daemon=True
        )

        t1.start()
        t2.start()

        t1.join()
        t2.join()

    except Exception as e:
        print("Connection error:", e)

    finally:
        try:
            client.close()
        except:
            pass

        try:
            remote.close()
        except:
            pass

        print("RDP tunnel closed")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 只监听 localhost，不向主网开放 13389
server.bind((LISTEN_IP, LISTEN_PORT))
server.listen(5)

print(f"Listening on {LISTEN_IP}:{LISTEN_PORT}")
print(
    f"Outbound fixed source: "
    f"{SOURCE_IP}:{SOURCE_PORT}"
)

while True:
    client, addr = server.accept()

    threading.Thread(
        target=handle,
        args=(client,),
        daemon=True
    ).start()
