import contextlib
import io
import json
import os
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import portpin


class ReconnectTests(unittest.TestCase):
    def setUp(self):
        self.target = socket.socket()
        self.target.bind(("127.0.0.1", 0))
        self.target.listen()
        self.target.settimeout(2)
        self.addCleanup(self.target.close)
        self.logs = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.logs))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            source_port = reservation.getsockname()[1]
        self.config = {
            "source_ip": "127.0.0.1",
            "source_port": source_port,
            "remote_ip": "127.0.0.1",
            "remote_port": self.target.getsockname()[1],
        }

    def start_tunnel(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            phone = socket.create_connection(listener.getsockname(), timeout=2)
            client, _ = listener.accept()
        self.addCleanup(phone.close)
        self.addCleanup(client.close)
        worker = threading.Thread(
            target=portpin.handle, args=(client, self.config), daemon=True
        )
        worker.start()
        try:
            desktop, address = self.target.accept()
        except TimeoutError:
            phone.close()
            worker.join(2)
            self.fail(f"The desktop did not receive the immediate reconnect\n{self.logs.getvalue()}")
        desktop.settimeout(2)
        self.addCleanup(desktop.close)
        self.assertEqual(address, ("127.0.0.1", self.config["source_port"]))
        phone.sendall(b"request")
        self.assertEqual(desktop.recv(7), b"request")
        desktop.sendall(b"response")
        self.assertEqual(phone.recv(8), b"response")
        return phone, desktop, worker

    def test_client_disconnect_allows_immediate_fixed_port_reconnect(self):
        for _ in range(5):
            phone, desktop, worker = self.start_tunnel()
            phone.close()
            try:
                self.assertEqual(desktop.recv(1), b"")
            except ConnectionResetError:
                pass
            desktop.close()
            worker.join(2)
            self.assertFalse(worker.is_alive(), "Disconnected tunnel did not exit")

    def test_remote_disconnect_allows_immediate_fixed_port_reconnect(self):
        for _ in range(5):
            phone, desktop, worker = self.start_tunnel()
            desktop.shutdown(socket.SHUT_WR)
            self.assertEqual(phone.recv(1), b"")
            worker.join(2)
            self.assertFalse(worker.is_alive())
            desktop.close()
            phone.close()

    def test_normal_close_can_be_selected(self):
        self.config["reset_on_disconnect"] = False
        phone, desktop, worker = self.start_tunnel()
        phone.close()
        self.assertEqual(desktop.recv(1), b"")  # A reset would raise here.
        desktop.close()
        worker.join(2)
        self.assertFalse(worker.is_alive())


class ConfigTests(unittest.TestCase):
    def load(self, **options):
        config = dict(
            listen_ip="127.0.0.1", listen_port=13389,
            source_ip="127.0.0.1", source_port=40000,
            remote_ip="127.0.0.1", remote_port=3389,
            **options,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(config, file)
            return portpin.load_config(path)

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))

    def test_existing_config_enables_fast_reconnect(self):
        self.assertIs(self.load()["reset_on_disconnect"], True)

    def test_json_can_disable_reset(self):
        self.assertIs(self.load(reset_on_disconnect=False)["reset_on_disconnect"], False)

    def test_environment_overrides_json(self):
        for value, expected in (("false", False), ("TRUE", True)):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"RESET_ON_DISCONNECT": value}):
                    self.assertIs(
                        self.load(reset_on_disconnect=not expected)["reset_on_disconnect"],
                        expected,
                    )

    def test_invalid_reset_values_are_rejected(self):
        for value in ("false", 0, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load(reset_on_disconnect=value)
        with patch.dict(os.environ, {"RESET_ON_DISCONNECT": "nope"}):
            with self.assertRaises(ValueError):
                self.load()


if __name__ == "__main__":
    unittest.main()
