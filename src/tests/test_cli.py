import tempfile
import threading
import time
import unittest

from typer.testing import CliRunner

from main import FileExchangerCLI
from server import FileServer


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.host = "127.0.0.1"
        cls.port = 5000
        server = FileServer(
            host=cls.host,
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

    def setUp(self):
        self.runner = CliRunner()
        self.cli = FileExchangerCLI()
        self.cli.client.host = self.__class__.host
        self.cli.client.port = self.__class__.port

    def test_help_lists_commands(self):
        result = self.runner.invoke(self.cli.app, ["--help"])
        self.assertIn("serve", result.output)
        self.assertIn("share", result.output)

    def test_list_empty(self):
        result = self.runner.invoke(self.cli.app, ["list"])
        self.assertEqual(result.exit_code, 0)
