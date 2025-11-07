import asyncio
import logging
import os
import re
import socket
import threading
from pathlib import Path
from typing import Tuple

try:
    from .shared import ErrorDuringUpload, FileNotFound, PeerDisconnected
except ImportError:  # pragma: no cover - script/CLI execution
    from shared import (  # type: ignore
        ErrorDuringUpload,
        FileNotFound,
        PeerDisconnected,
    )

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_STORAGE_DIR = str(BASE_DIR / "database")


class FileServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5050,
        storage_dir: str = DEFAULT_STORAGE_DIR,
        mode: str = "threaded",
    ) -> None:
        self.host: str = host
        self.port: int = port
        self.storage_dir: str = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.mode: str = mode
        logging.info(f"Storage directory set to {self.storage_dir}")

    def start(self) -> None:
        if self.mode == "threaded":
            self._start_threaded()
        else:
            asyncio.run(self._start_async())

    def _start_threaded(self) -> None:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen()
        logging.info(f"Threaded server listening on {self.host}:{self.port}")
        while True:
            conn, addr = sock.accept()
            threading.Thread(
                target=self._handle_client, args=(conn, addr), daemon=True
            ).start()

    async def _start_async(self) -> None:
        server = await asyncio.start_server(
            self._handle_client_async, self.host, self.port
        )
        logging.info(f"Async server listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        try:
            with conn:
                buffer = b""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        self._dispatch_command(conn, addr, line.decode().strip())
        except ConnectionResetError:
            pass
        except Exception as e:
            logging.error(f"[{addr}] Error: {e}")
        finally:
            conn.close()
            logging.info(f"[-] Connection closed: {addr}")

    async def _handle_client_async(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info("peername")
        try:
            while not reader.at_eof():
                data = await reader.readline()
                if not data:
                    break
                line = data.decode().strip()
                await self._dispatch_command_async(reader, writer, addr, line)
        except ConnectionResetError:
            pass
        except Exception as e:
            logging.error(f"[{addr}] Async error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionResetError:
                pass
            logging.info(f"[-] Async connection closed: {addr}")

    def _dispatch_command(
        self, peer: socket.socket, addr: Tuple[str, int], line: str
    ) -> None:
        logging.info(f"[{addr}] Command received: {line}")
        parts = line.split()
        if not parts:
            return
        cmd = parts[0].upper()
        try:
            if cmd == "LOAD":
                filename = parts[1]
                self._cmd_load(peer, addr, filename)
                return
            elif cmd == "GET" and len(parts) >= 3:
                sub = parts[1].upper()
                if sub == "FILE":
                    self._cmd_get_file(peer, addr, parts[2])
                elif sub == "FILES":
                    self._cmd_get_files(peer, addr, parts[2])
                else:
                    peer.sendall(b"ERROR Unknown GET subcommand\n")
            else:
                peer.sendall(b"ERROR Unknown command\n")
        except FileNotFound as e:
            peer.sendall(f"ERROR FileNotFound {e}\n".encode())
        except ErrorDuringUpload as e:
            peer.sendall(f"ERROR ErrorDuringUpload {e}\n".encode())
        except PeerDisconnected as e:
            peer.sendall(f"ERROR PeerDisconnected {e}\n".encode())
        except Exception as e:
            peer.sendall(f"ERROR {e}\n".encode())

    async def _dispatch_command_async(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        addr: Tuple[str, int],
        line: str,
    ) -> None:
        parts = line.split()
        cmd = parts[0].upper() if parts else ""
        if cmd == "LOAD":
            filename = parts[1]
            await self._cmd_load_async(reader, writer, addr, filename)
            return
        elif cmd == "GET" and len(parts) >= 3:
            sub = parts[1].upper()
            if sub == "FILE":
                await self._cmd_get_file_async(writer, addr, parts[2])
            elif sub == "FILES":
                await self._cmd_get_files_async(writer, addr, parts[2])
        else:
            writer.write(b"ERROR Unknown command\n")
            await writer.drain()

    def _cmd_load(
        self, peer: socket.socket, addr: Tuple[str, int], filename: str
    ) -> None:
        peer.sendall(b"READY\n")
        file_path = os.path.join(self.storage_dir, filename)
        try:
            with open(file_path, "wb") as f:
                buffer = b""
                while True:
                    chunk = peer.recv(4096)
                    if not chunk:
                        raise PeerDisconnected("Connection lost during upload")
                    buffer += chunk
                    if b"<END>\n" in buffer:
                        content, _ = buffer.split(b"<END>\n", 1)
                        f.write(content)
                        break
                    f.write(buffer)
                    buffer = b""
            logging.info(f"[{addr}] Upload complete: {filename}")
        except Exception as e:
            logging.error(f"[{addr}] Upload error: {e}")
            raise ErrorDuringUpload(e)

    async def _cmd_load_async(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        addr: Tuple[str, int],
        filename: str,
    ) -> None:
        writer.write(b"READY\n")
        await writer.drain()
        file_path = os.path.join(self.storage_dir, filename)
        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = await reader.read(4096)
                    if not chunk:
                        raise PeerDisconnected("Connection lost during upload")
                    if b"<END>\n" in chunk:
                        content, _ = chunk.split(b"<END>\n", 1)
                        f.write(content)
                        break
                    f.write(chunk)
            logging.info(f"[{addr}] Upload complete: {filename}")
        except Exception as e:
            logging.error(f"[{addr}] Upload error: {e}")
            raise ErrorDuringUpload(e)

    def _cmd_get_file(
        self, peer: socket.socket, addr: Tuple[str, int], filename: str
    ) -> None:
        path = os.path.join(self.storage_dir, filename)
        if not os.path.isfile(path):
            peer.sendall(f"ERROR FileNotFound {filename}\n".encode())
            return
        size = os.path.getsize(path)
        peer.sendall(f"READY {size}\n".encode())
        with open(path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                peer.sendall(chunk)
        peer.sendall(b"<END>\n")
        logging.info(f"[{addr}] File sent: {filename}")

    async def _cmd_get_file_async(
        self, writer: asyncio.StreamWriter, addr: Tuple[str, int], filename: str
    ) -> None:
        path = os.path.join(self.storage_dir, filename)
        if not os.path.isfile(path):
            writer.write(f"ERROR FileNotFound {filename}\n".encode())
            await writer.drain()
            return
        size = os.path.getsize(path)
        writer.write(f"READY {size}\n".encode())
        await writer.drain()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        writer.write(b"<END>\n")
        await writer.drain()
        logging.info(f"[{addr}] File sent: {filename}")

    def _cmd_get_files(
        self, peer: socket.socket, addr: Tuple[str, int], pattern: str
    ) -> None:
        if pattern.upper() == "ALL":
            regex = re.compile(".*")
        else:
            regex = re.compile("^" + pattern.replace("*", ".*") + "$")
        matches = [f for f in os.listdir(self.storage_dir) if regex.match(f)]
        peer.sendall(("\n".join(matches) + "\n").encode())
        logging.info(f"[{addr}] Sent list of {len(matches)} files")

    async def _cmd_get_files_async(
        self, writer: asyncio.StreamWriter, addr: Tuple[str, int], pattern: str
    ) -> None:
        if pattern.upper() == "ALL":
            regex = re.compile(".*")
        else:
            regex = re.compile("^" + pattern.replace("*", ".*") + "$")
        matches = [f for f in os.listdir(self.storage_dir) if regex.match(f)]
        writer.write(("\n".join(matches) + "\n").encode())
        await writer.drain()
        logging.info(f"[{addr}] Sent list of {len(matches)} files")
