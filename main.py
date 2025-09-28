import logging
import os

import typer
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TextColumn

from client import FileClient
from server import FileServer
from shared import (
    ErrorDuringDownload,
    ErrorDuringUpload,
    FileNotFound,
    PeerDisconnected,
)

logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[RichHandler(show_path=False)]
)


class FileExchangerCLI:
    def __init__(self) -> None:
        self.app: typer.Typer = typer.Typer(help="File Exchanger CLI")
        self.client: FileClient = FileClient()
        self.server: FileServer = FileServer()
        self._register_commands()

    def _register_commands(self) -> None:
        self.app.command()(self.serve)
        self.app.command()(self.share)
        self.app.command()(self.upload)
        self.app.command()(self.download)
        self.app.command()(self.list)
        self.app.command()(self.search)

    def serve(
        self,
        threaded: bool = typer.Option(
            True,
            "--threaded/--async",
            help="Run server in threaded (--threaded) or async (--async) mode",
        ),
    ) -> None:
        mode = "threaded" if threaded else "async"
        logging.info(f"Starting server in {mode} mode…")
        self.server.mode = mode
        self.server.start()

    def share(
        self,
        directory: str = typer.Argument(
            ..., help="Local directory to auto-upload on startup"
        ),
        compress: bool = typer.Option(
            False, "--compress", help="ZIP files before sharing"
        ),
    ) -> None:
        try:
            self.client.share_directory(directory, compress=compress, progress_cb=None)
            logging.info(f"Shared directory: {directory}")
        except Exception as e:
            logging.error(f"Error sharing directory: {e}")

    def upload(
        self,
        file: str = typer.Argument(..., help="Path to file to upload"),
        compress: bool = typer.Option(
            False, "--compress", help="ZIP file before sending"
        ),
    ) -> None:
        self.client.connect()
        logger = logging.getLogger()
        old_level = logger.level
        logger.setLevel(logging.WARNING)

        try:
            if compress:
                to_send = self.client.compress_file(file)
            else:
                to_send = file
            total = os.path.getsize(to_send)
        except Exception as e:
            logger.setLevel(old_level)
            logging.error(f"Error: {e}")
            self.client.disconnect()
            return

        with Progress(
            TextColumn("[cyan]{task.description}"),
            BarColumn(),
            TextColumn("[green]{task.completed}/{task.total} bytes"),
        ) as progress:
            task = progress.add_task(
                f"Uploading {os.path.basename(to_send)}", total=total
            )
            try:
                self.client.upload(
                    file,
                    compress=compress,
                    progress_cb=lambda n: progress.update(task, advance=n),
                )
            except FileNotFound as e:
                logger.setLevel(old_level)
                logging.error(f"Error: {e}")
                self.client.disconnect()
                return
            except ErrorDuringUpload as e:
                logger.setLevel(old_level)
                logging.error(f"Upload failed: {e}")
                self.client.disconnect()
                return

        logger.setLevel(old_level)
        logging.info(f"Upload complete: {os.path.basename(to_send)}")
        self.client.disconnect()

    def download(
        self,
        file: str = typer.Argument(..., help="Filename to download"),
        decompress: bool = typer.Option(
            False, "--decompress", help="Unzip after download"
        ),
        output_dir: str = typer.Option(
            ".", "--output-dir", "-o", help="Directory to save the file"
        ),
    ) -> None:
        self.client.connect()
        logger = logging.getLogger()
        old_level = logger.level
        logger.setLevel(logging.WARNING)
        try:
            self.client.client_socket.sendall(f"GET FILE {file}\n".encode())
            line = self.client.client_socket.recv(1024).decode().strip()
            if line.startswith("ERROR"):
                raise FileNotFound(line)
            parts = line.split()
            if parts[0] != "READY" or len(parts) != 2:
                raise ErrorDuringDownload(f"Unexpected response from server: {line}")
            total = int(parts[1])
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file)
            with Progress(
                TextColumn("[cyan]{task.description}"),
                BarColumn(),
                TextColumn("[green]{task.completed}/{task.total} bytes"),
            ) as progress:
                task = progress.add_task(f"Downloading {file}", total=total)
                received = 0
                with open(output_path, "wb") as f:
                    while received < total:
                        chunk = self.client.client_socket.recv(
                            min(4096, total - received)
                        )
                        if not chunk:
                            raise PeerDisconnected("Connection lost during download")
                        f.write(chunk)
                        received += len(chunk)
                        progress.update(task, advance=len(chunk))
            logger.setLevel(old_level)
            logging.info(f"Download complete: {file}")
            if decompress and output_path.endswith(".zip"):
                self.client.decompress_file(output_path, output_dir)
                logging.info(f"Decompressed to {output_dir}: {output_path}")
                os.remove(output_path)
                logging.info(f"Removed zip file: {output_path}")
        except FileNotFound as e:
            logging.error(f"Error: {e}")
        except ErrorDuringDownload as e:
            logging.error(f"Download failed: {e}")
        finally:
            self.client.disconnect()

    def list(self) -> None:
        self.client.connect()
        self.client.list_files()
        self.client.disconnect()

    def search(
        self,
        pattern: str = typer.Argument(
            ..., help="Wildcard pattern to search (e.g. *.txt)"
        ),
    ) -> None:
        self.client.connect()
        self.client.search_file(pattern)
        self.client.disconnect()


if __name__ == "__main__":
    FileExchangerCLI().app()
