import argparse
import json
import os
import select
import socket
import struct


DEFAULT_CONFIG_PATH = "config.json"


def load_config(path):
    with open(path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    environment_keys = {
        "listen_ip": "LISTEN_IP",
        "listen_port": "LISTEN_PORT",
        "source_ip": "SOURCE_IP",
        "source_port": "SOURCE_PORT",
        "remote_ip": "REMOTE_IP",
        "remote_port": "REMOTE_PORT",
        "reset_on_disconnect": "RESET_ON_DISCONNECT",
    }
    for config_key, environment_key in environment_keys.items():
        if environment_key in os.environ:
            value = os.environ[environment_key]
            if config_key == "reset_on_disconnect":
                if value.lower() not in ("true", "false"):
                    raise ValueError("RESET_ON_DISCONNECT must be true or false")
                value = value.lower() == "true"
            elif config_key.endswith("_port"):
                try:
                    value = int(value)
                except ValueError:
                    pass
            config[config_key] = value

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

    config.setdefault("reset_on_disconnect", True)
    if not isinstance(config["reset_on_disconnect"], bool):
        raise ValueError("reset_on_disconnect must be a boolean")

    return config


def handle(client, config):
    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if config.get("reset_on_disconnect", True):
            # Reconnecting to the same peer needs the same TCP four-tuple.
            # SO_REUSEADDR alone cannot bypass TIME_WAIT for that connection.
            # Winsock uses unsigned shorts for linger; Unix uses ints.
            linger_format = "HH" if os.name == "nt" else "ii"
            remote.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER,
                struct.pack(linger_format, 1, 0),
            )

        print(
            f"[+] Connecting "
            f"{config['source_ip']}:{config['source_port']} -> "
            f"{config['remote_ip']}:{config['remote_port']}"
        )

        remote.bind((config["source_ip"], config["source_port"]))
        remote.connect((config["remote_ip"], config["remote_port"]))

        print("[+] Remote connected")

        sockets = [client, remote]

        while True:
            readable, _, exceptional = select.select(
                sockets,
                [],
                sockets,
            )

            if exceptional:
                print("[-] Socket exception")
                break

            for source in readable:
                try:
                    data = source.recv(65536)
                except OSError as error:
                    print(f"[-] recv error: {error}")
                    return

                if not data:
                    print("[-] Peer closed connection")
                    return

                if source is client:
                    destination = remote
                    direction = "CLIENT -> REMOTE"
                else:
                    destination = client
                    direction = "REMOTE -> CLIENT"

                try:
                    destination.sendall(data)
                except OSError as error:
                    print(f"[-] send error: {error}")
                    return

                print(f"[>] {direction}: {len(data)} bytes")

    except Exception as error:
        print(f"[-] Connection error: {error!r}")

    finally:
        try:
            remote.close()
        except Exception:
            pass

        try:
            client.close()
        except Exception:
            pass

        print("[-] Connection closed")


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
            client, address = server.accept()
            print(f"[+] Client connected: {address}")
            handle(client, config)
    finally:
        server.close()


if __name__ == "__main__":
    main()
