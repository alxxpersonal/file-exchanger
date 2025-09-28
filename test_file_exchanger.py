import os
import shutil
import socket
import tempfile
import threading
import time
import unittest

from typer.testing import CliRunner

from client import FileClient
from main import FileExchangerCLI
from server import FileServer
from shared import (
    ErrorDuringDownload,
    ErrorDuringUpload,
    FileNotFound,
    PeerDisconnected,
)


class TestSharedErrors(unittest.TestCase):
    def test_file_not_found_message(self):
        e = FileNotFound("missing.txt")
        self.assertIn("missing.txt", str(e))

    def test_error_types_are_exceptions(self):
        for exc_cls, msg in [
            (ErrorDuringUpload, "upload fail"),
            (ErrorDuringDownload, "download fail"),
            (PeerDisconnected, "peer gone"),
        ]:
            with self.subTest(exc=exc_cls):
                e = exc_cls(msg)
                self.assertIsInstance(e, Exception)
                self.assertIn(msg, str(e))


class TestClientCompressDecompress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "foo.txt")
        with open(self.src, "w") as f:
            f.write("hello")
        self.client = FileClient()

    def tearDown(self):
        self.tmp.cleanup()

    def test_compress_and_decompress(self):
        zip_path = self.client.compress_file(self.src)
        self.assertTrue(os.path.isfile(zip_path))
        out_dir = os.path.join(self.tmp.name, "out")
        os.makedirs(out_dir)
        self.client.decompress_file(zip_path, out_dir)
        with open(os.path.join(out_dir, "foo.txt")) as f:
            self.assertEqual(f.read(), "hello")


class TestClientUploadDownload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.storage = tempfile.TemporaryDirectory()
        fs = FileServer(
            host="127.0.0.1",
            port=cls.port,
            storage_dir=cls.storage.name,
            mode="threaded",
        )
        cls.thread = threading.Thread(target=fs.start, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def test_roundtrip_upload_download(self):
        local = os.path.join(tempfile.gettempdir(), "up.txt")
        with open(local, "w") as f:
            f.write("data123")
        client = FileClient(host="127.0.0.1", port=self.port)
        client.connect()
        client.upload(local, compress=False)
        client.disconnect()
        stored = os.path.join(self.storage.name, "up.txt")
        self.assertTrue(os.path.isfile(stored))
        outdir = os.path.join(tempfile.gettempdir(), "dlout")
        if os.path.isdir(outdir):
            shutil.rmtree(outdir)
        os.makedirs(outdir)
        client.connect()
        client.download("up.txt", decompress=False, output_dir=outdir)
        client.disconnect()
        with open(os.path.join(outdir, "up.txt")) as f:
            self.assertEqual(f.read(), "data123")
        os.remove(local)
        shutil.rmtree(outdir)

    def test_upload_nonexistent_raises(self):
        client = FileClient()
        client.connect()
        with self.assertRaises(FileNotFound):
            client.upload("no_such_file.txt")
        client.disconnect()


class TestServerThreaded(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.storage = tempfile.TemporaryDirectory()
        fs = FileServer(
            host="127.0.0.1",
            port=cls.port,
            storage_dir=cls.storage.name,
            mode="threaded",
        )
        cls.thread = threading.Thread(target=fs.start, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def send_recv(self, msg):
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            sock.sendall((msg + "\n").encode())
            return sock.recv(4096).decode()

    def test_list_empty(self):
        resp = self.send_recv("GET FILES ALL")
        self.assertEqual(resp.strip(), "")

    def test_store_and_list(self):
        path = os.path.join(self.storage.name, "a.txt")
        with open(path, "w") as f:
            f.write("x")
        resp = self.send_recv("GET FILES ALL")
        self.assertIn("a.txt", resp)

    def test_search_pattern(self):
        for name in ("one.log", "two.txt", "three.log"):
            with open(os.path.join(self.storage.name, name), "w") as f:
                f.write("x")
        resp = self.send_recv("GET FILES *.log")
        lines = resp.strip().splitlines()
        self.assertEqual(set(lines), {"one.log", "three.log"})


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        fs = FileServer(
            host="127.0.0.1", port=5000, storage_dir=cls.storage.name, mode="threaded"
        )
        cls.thread = threading.Thread(target=fs.start, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def setUp(self):
        self.runner = CliRunner()

    def test_help_lists_commands(self):
        result = self.runner.invoke(FileExchangerCLI().app, ["--help"])
        self.assertIn("serve", result.output)
        self.assertIn("share", result.output)

    def test_list_empty(self):
        result = self.runner.invoke(FileExchangerCLI().app, ["list"])
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
