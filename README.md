## File Exchanger

*_CLI-native TCP service for fast file exchanges across machines._*

---

### `[ Overview ]`
- Share folders or single files through a minimal `python main.py` interface (run from `src/`).  
- Dual server cores: threaded (default) for broad compatibility, async for high concurrency.  
- Chunked transfers, optional compression, wildcard search, and Docker deployment baked in.  


---

### `[ Project Layout ]`
```text
file-exchanger/
├── README.md
├── LICENSE
└── src/
    ├── main.py                # CLI entrypoint (typer app)
    ├── client.py              # socket client used by CLI commands
    ├── server.py              # threaded/async server runtime
    ├── shared/                # exported exceptions live in __init__.py
    ├── database/              # default on-disk storage for uploads
    ├── tests/                 # unittest suite
    │   ├── test_shared.py
    │   ├── test_client_io.py
    │   ├── test_client_network.py
    │   ├── test_server_threaded.py
    │   └── test_cli.py
    ├── PROJECT.md             # internal runtime map
    ├── requirements.txt       # runtime dependencies
    ├── Dockerfile             # container spec (build with -f src/Dockerfile)
    └── pyproject.toml         # packaging metadata
```

`server_database/` now lives inside `src/database/`; update any local storage paths accordingly.  
All runtime commands below assume you have `cd src` and are running `python` (or `python3`) from inside that directory.

#

### `[ Quickstart ]`
1. Clone the repo and create a virtual environment in the repository root.  
2. Activate the environment.  
3. `cd src` so you are inside the runtime folder.  
4. Install dependencies via `pip install -r requirements.txt`.  
5. Launch `python main.py serve` (use `python3` if that is your interpreter name).  

```bash
git clone https://github.com/alxxpersonal/file-exchanger.git
cd file-exchanger
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
cd src
pip install -r requirements.txt
python main.py serve               # or: python3 main.py serve
```

---

### `[ Server Modes ]`
- `python main.py serve` boots the threaded server and listens on `5050`.  
- `python main.py serve --threaded` enforces the threaded worker pool explicitly.  
- `python main.py serve --async` switches to the asyncio reactor for higher concurrency.  

```bash
# threaded (default)
python main.py serve

# force a mode
python main.py serve --threaded
python main.py serve --async
```

---

### `[ Client Commands ]`
Run commands from inside `src/` with the virtual environment active.

| command | action |
| --- | --- |
| `python main.py share <dir>` | upload every file within a directory tree |
| `python main.py upload <file> [--compress]` | push a single file, optionally compressing chunks |
| `python main.py download <file> [--decompress]` | pull a file, optionally decompressing on receipt |
| `python main.py list` | list all server-hosted files |
| `python main.py search <pattern>` | wildcard search (e.g., `"*mp4"`) |

```bash
python main.py upload report.pdf --compress
python main.py list
python main.py download report.pdf --decompress
python main.py search "*mp4"
```

---

### `[ Docker Run ]`
- Build the container image once, then run it by mapping host port `5050`.  
- Keep the port consistent with clients and stop the container when done.  

```bash
docker build -f src/Dockerfile -t file-exchanger-server .
docker run -p 5050:5050 file-exchanger-server --threaded   # or --async

# stop the container
docker ps        # grab the container ID
docker stop <container_id>
```

---

### `[ Testing ]`
- Execute the bundled unit tests from the repository root.  

```bash
cd src
python -m unittest discover tests
```

---

*_This was the very first project I built at the start of my Python journey._*
