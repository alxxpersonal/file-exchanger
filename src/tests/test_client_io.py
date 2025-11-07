import os
import tempfile
import unittest

from client import FileClient


class TestClientCompressDecompress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "foo.txt")
        with open(self.src, "w", encoding="utf-8") as handle:
            handle.write("hello")
        self.client = FileClient()

    def tearDown(self):
        self.tmp.cleanup()

    def test_compress_and_decompress(self):
        zip_path = self.client.compress_file(self.src)
        self.assertTrue(os.path.isfile(zip_path))

        out_dir = os.path.join(self.tmp.name, "out")
        os.makedirs(out_dir)
        self.client.decompress_file(zip_path, out_dir)

        with open(os.path.join(out_dir, "foo.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "hello")
