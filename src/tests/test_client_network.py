import os
import shutil
import socket
import tempfile
import threading
import time
import unittest

from client import FileClient
from server import FileServer
from shared import FileNotFound


class TestClientUploadDownload(unittest.TestCase):
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

    def test_roundtrip_upload_download(self):
        local = os.path.join(tempfile.gettempdir(), "up.txt")
        with open(local, "w", encoding="utf-8") as handle:
            handle.write("data123")

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

        with open(os.path.join(outdir, "up.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "data123")

        os.remove(local)
        shutil.rmtree(outdir)

    def test_upload_nonexistent_raises(self):
        client = FileClient()
        client.connect()
        with self.assertRaises(FileNotFound):
            client.upload("no_such_file.txt")
        client.disconnect()
