import os
import socket
import tempfile
import threading
import time
import unittest

from server import FileServer


class TestServerThreaded(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        cls.storage = tempfile.TemporaryDirectory()
        server = FileServer(
            host="127.0.0.1",
            port=cls.port,
            storage_dir=cls.storage.name,
            mode="threaded",
        )
        cls.thread = threading.Thread(target=server.start, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def send_recv(self, message: str) -> str:
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            sock.sendall((message + "\n").encode())
            return sock.recv(4096).decode()

    def test_list_empty(self):
        response = self.send_recv("GET FILES ALL")
        self.assertEqual(response.strip(), "")

    def test_store_and_list(self):
        path = os.path.join(self.storage.name, "a.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
        response = self.send_recv("GET FILES ALL")
        self.assertIn("a.txt", response)

    def test_search_pattern(self):
        for name in ("one.log", "two.txt", "three.log"):
            with open(os.path.join(self.storage.name, name), "w", encoding="utf-8") as handle:
                handle.write("x")
        response = self.send_recv("GET FILES *.log")
        lines = response.strip().splitlines()
        self.assertEqual(set(lines), {"one.log", "three.log"})
