class FileNotFound(Exception):
    """Raised when a requested file is not found on the server or client."""


class ErrorDuringUpload(Exception):
    """Raised when there is an error while uploading a file."""


class ErrorDuringDownload(Exception):
    """Raised when there is an error while downloading a file."""


class PeerDisconnected(Exception):
    """Raised when the client or server disconnects unexpectedly."""
