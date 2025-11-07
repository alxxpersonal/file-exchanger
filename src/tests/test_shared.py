import unittest

from shared import (
    ErrorDuringDownload,
    ErrorDuringUpload,
    FileNotFound,
    PeerDisconnected,
)


class TestSharedErrors(unittest.TestCase):
    def test_file_not_found_message(self):
        error = FileNotFound("missing.txt")
        self.assertIn("missing.txt", str(error))

    def test_error_types_are_exceptions(self):
        for exc_cls, msg in [
            (ErrorDuringUpload, "upload fail"),
            (ErrorDuringDownload, "download fail"),
            (PeerDisconnected, "peer gone"),
        ]:
            with self.subTest(exc=exc_cls):
                error = exc_cls(msg)
                self.assertIsInstance(error, Exception)
                self.assertIn(msg, str(error))
