import argparse
import json
import socket
import threading


DEFAULT_CONFIG_PATH = "config.json"


def load_config(path):
    with open(path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    required = {
        "listen_ip",
        "listen_port",
        "source_ip",
        "source_port",
        "remote_ip",
        "remote_port",
    }
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Missing configuration keys: {', '.join(sorted(missing))}")

    for key in ("listen_port", "source_port", "remote_port"):
        if not isinstance(config[key], int) or not 1 <= config[key] <= 65535:
            raise ValueError(f"{key} must be an integer between 1 and 65535")

    return config


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


def handle(client, config):
    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 尽量允许端口快速重复使用
    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        remote.bind((config["source_ip"], config["source_port"]))

        print(
            f"Connecting "
            f"{config['source_ip']}:{config['source_port']} -> "
            f"{config['remote_ip']}:{config['remote_port']}"
        )

        remote.connect((config["remote_ip"], config["remote_port"]))

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
        except OSError:
            pass

        try:
            remote.close()
        except:
            pass

        print("RDP tunnel closed")


def main():
    parser = argparse.ArgumentParser(description="Forward TCP connections with a fixed source port")
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"path to JSON configuration (default: {DEFAULT_CONFIG_PATH})",
    )
    args = parser.parse_args()
    config = load_config(args.config)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((config["listen_ip"], config["listen_port"]))
        server.listen(5)

        print(f"Listening on {config['listen_ip']}:{config['listen_port']}")
        print(
            f"Outbound fixed source: "
            f"{config['source_ip']}:{config['source_port']}"
        )

        while True:
            client, _ = server.accept()
            threading.Thread(
                target=handle,
                args=(client, config),
                daemon=True,
            ).start()
    finally:
        server.close()


if __name__ == "__main__":
    main()
