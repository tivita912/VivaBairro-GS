"""Confirma que o Uvicorn serve a página e os recursos por HTTP local."""
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
import sys
from threading import Thread
from urllib.request import urlopen

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.web import create_app


def main():
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", log_level="warning", access_log=False))
    with socket(AF_INET, SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{port}"
            with urlopen(url, timeout=15) as response:
                page = response.read()
                assert b"VivaBairro Voz" in page
                assert b'id="capture-controls" hidden' in page
            for asset in ("site.css", "site.js", "bairro.webp"):
                with urlopen(f"{url}/assets/{asset}", timeout=15) as response:
                    assert response.read(1)
            print("PASS: HTTP local, consentimento inicial e recursos do site.")
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        assert not thread.is_alive(), "O servidor de teste não encerrou."


if __name__ == "__main__":
    main()
