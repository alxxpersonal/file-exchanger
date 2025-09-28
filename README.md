

# file_exchanger

tiny tcp client–server app to swap files straight from the cli.  
threaded or async server modes, chunked upload/download, list + search by pattern.

---

## quickstart

```bash
git clone https://github.com/alxxpersonal/file_exchanger.git
python -m venv .venv
source .venv/bin/activate   # windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## run the server

```bash
# threaded (default)
python main.py serve

# or explicitly
python main.py serve --threaded

# async mode
python main.py serve --async
```

---

## client cmds

| cmd | what it does |
| --- | ----------- |
| `python main.py share <dir>` | auto-upload every file in a folder |
| `python main.py upload <file> [--compress]` | upload single file (can compress) |
| `python main.py download <file> [--decompress]` | download (can decompress) |
| `python main.py list` | list all files on server |
| `python main.py search <pattern>` | wildcard search |

examples:
```bash
python main.py upload report.pdf --compress
python main.py list
python main.py download report.pdf --decompress
python main.py search "*mp4"
```

---

## docker

run the server inside a container:

```bash
docker build -t file_exchanger_server .
docker run -p 5050:5050 file_exchanger_server [--threaded|--async]
```

make sure port `5050` is open and matches the client.  
stop it:
```bash
docker ps     # get container id
docker stop <container_id>
```

---

## tests

unit tests included:
```bash
python test_file_exchanger.py
```
(run from the `file_exchanger` folder with deps installed)