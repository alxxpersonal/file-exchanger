import logging
import os
import socket
import zipfile
from typing import Callable, Optional

from shared import (
    ErrorDuringDownload,
    ErrorDuringUpload,
    FileNotFound,
    PeerDisconnected,
)


class FileClient:
    def __init__(self, host: str = "0.0.0.0", port: int = 5050) -> None:
        self.host: str = host
        self.port: int = port
        self.client_socket: Optional[socket.socket] = None

    def compress_file(self, path: str) -> str:
        zip_path: str = f"{path}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(path, arcname=os.path.basename(path))
        return zip_path

    def decompress_file(self, zip_path: str, output_dir: str = ".") -> None:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(output_dir)

    def connect(self) -> None:
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            logging.info(f"Connected to server at {self.host}:{self.port}")
        except ConnectionRefusedError:
            logging.error("Server not running or refused connection.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    def disconnect(self) -> None:
        if self.client_socket:
            self.client_socket.close()
            logging.info("Disconnected.")

    def upload(
        self,
        file_name: str,
        compress: bool = False,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> None:
        if not self.client_socket:
            logging.error("Not connected to server.")
            return

        if not os.path.isfile(file_name):
            logging.error(f"File {file_name} not found.")
            raise FileNotFound(f"File {file_name} not found.")

        if compress:
            file_to_send = self.compress_file(file_name)
            label = os.path.basename(file_to_send)
        else:
            file_to_send = file_name
            label = os.path.basename(file_name)

        try:
            command = f"LOAD {label} {'COMPRESSED' if compress else ''}\n"
            self.client_socket.sendall(command.encode())
            resp = self.client_socket.recv(1024).decode().strip()
            if resp != "READY":
                logging.error(f"Server not ready for upload: {resp}")
                return

            with open(file_to_send, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.client_socket.sendall(chunk)
                    if progress_cb:
                        progress_cb(len(chunk))

            self.client_socket.sendall(b"<END>\n")
            logging.info(f"Upload of {file_name} complete.")

            if compress:
                try:
                    os.remove(file_to_send)
                    logging.info(f"Removed temporary zip file: {file_to_send}")
                except OSError:
                    pass

        except Exception as e:
            logging.error(f"Error during upload: {e}")
            raise ErrorDuringUpload(str(e))

    def download(
        self,
        file_name: str,
        decompress: bool = False,
        output_dir: str = ".",
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> None:
        if not self.client_socket:
            logging.error("Not connected to server.")
            return

        try:
            command = f"GET FILE {file_name}\n"
            self.client_socket.sendall(command.encode())
            line = self.client_socket.recv(1024).decode().strip()
            if line.startswith("ERROR"):
                raise FileNotFound(line)
            parts = line.split()
            if parts[0] != "READY" or len(parts) != 2:
                raise ErrorDuringDownload(f"Unexpected response from server: {line}")
            total_size = int(parts[1])

            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file_name)
            received = 0

            with open(output_path, "wb") as f:
                while received < total_size:
                    chunk = self.client_socket.recv(min(4096, total_size - received))
                    if not chunk:
                        raise PeerDisconnected("Connection lost during download")
                    f.write(chunk)
                    received += len(chunk)
                    if progress_cb:
                        progress_cb(len(chunk))

            logging.info(f"Download of {file_name} complete.")

            if decompress and output_path.endswith(".zip"):
                self.decompress_file(output_path, output_dir)
                logging.info(f"Decompressed to {output_dir}: {output_path}")
                os.remove(output_path)
                logging.info(f"Removed zip file: {output_path}")

        except FileNotFound:
            raise
        except ErrorDuringDownload:
            raise
        except Exception as e:
            logging.error(f"Error during download: {e}")
            raise ErrorDuringDownload(str(e))

    def list_files(self) -> None:
        if not self.client_socket:
            logging.error("Not connected to server.")
            return
        try:
            command: str = "GET FILES ALL\n"
            self.client_socket.sendall(command.encode())

            files: str = self.client_socket.recv(8192).decode().strip()
            logging.info(f"Files on server:\n{files}")

        except Exception as e:
            logging.error(f"Error listing files: {e}")
            raise PeerDisconnected(str(e))

    def search_file(self, pattern: str) -> None:
        if not self.client_socket:
            logging.error("Not connected to server.")
            return
        try:
            command: str = f"GET FILES {pattern}\n"
            self.client_socket.sendall(command.encode())

            files: str = self.client_socket.recv(8192).decode().strip()
            logging.info(f"Matching files on server:\n{files}")

        except Exception as exception:
            logging.error(f"Error searching files: {exception}")
            raise PeerDisconnected(str(exception))

    def share_directory(
        self,
        directory: str,
        compress: bool = False,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> None:
        if not os.path.isdir(directory):
            logging.error(f"Directory {directory} does not exist.")
            return

        for root, _, files in os.walk(directory):
            for fname in files:
                path = os.path.join(root, fname)
                logging.info(f"Sharing file: {path}")
                self.connect()
                try:
                    self.upload(path, compress=compress, progress_cb=progress_cb)
                finally:
                    self.disconnect()
