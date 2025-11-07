## File Exchanger Runtime

*_Internal reference for how the `src/` tree is organized and how each module collaborates._*

---

### `[ RUNTIME ]`
- `main.py` hosts the Typer CLI (`FileExchangerCLI`) and wires every command to the matching client/server action.  
- Commands call into the `FileClient` to push, pull, and enumerate files; server lifecycle is proxied through `FileServer`.  
- Logging is configured once at import time so both CLI interactions and background threads share the same formatter.  

---

### `[ SERVER CORE ]`
- `server.py` exposes `FileServer`, a dual-mode TCP server.  
- Threaded mode spawns a worker thread per connection, async mode relies on `asyncio.start_server`.  
- Uploads land in `database/` (configurable via `storage_dir`) and every command funnels through `_dispatch_command*` helpers.  
- Regex-based filtering powers `GET FILES <pattern>` without duplicating logic between sync/async implementations.  

---

### `[ CLIENT FLOWS ]`
- `client.py` provides `FileClient`, the socket interface used by the CLI.  
- Handles compression (`zipfile`) and optional decompression, plus directory sharing by iterating and uploading with fresh connections.  
- Upload/download helpers surface typed errors so the CLI can display precise failure reasons without re-parsing strings.  

---

### `[ SHARED ]`
- `shared/__init__.py` centralizes exception classes (`FileNotFound`, `ErrorDuringUpload`, `ErrorDuringDownload`, `PeerDisconnected`).  
- Keeping them in `shared/` lets both client and server import from a single location and keeps logger/error handling consistent.  

---

### `[ EXECUTION FLOW ]`
1. Operator launches `python main.py serve|upload|list` from the `src/` directory.  
2. Typer maps CLI arguments to methods on `FileExchangerCLI`.  
3. Each method calls either `FileServer` (for `serve`) or `FileClient` (for everything else).  
4. Shared errors bubble up to the CLI where they are formatted for the terminal or progress bars.  

---

_`Last Edit: 11.07.2025`_
