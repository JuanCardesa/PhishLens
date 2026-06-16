from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8080
DEMO_ROOT = Path(__file__).resolve().parent


def main() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(DEMO_ROOT))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    print(f"Serving PhishLens demo pages at http://{HOST}:{PORT}/pages/")
    server.serve_forever()


if __name__ == "__main__":
    main()
