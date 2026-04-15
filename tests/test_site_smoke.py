from __future__ import annotations

import functools
import http.server
import socketserver
import threading
import urllib.request


def test_site_serves_app_and_generated_payloads() -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory="site")
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        root = f"http://127.0.0.1:{server.server_address[1]}"
        assert _status(root + "/") == 200
        assert _status(root + "/app.js") == 200
        assert _status(root + "/data/countries.json") == 200
        assert _status(root + "/data/us/gdp/latest.json") == 200
        assert _status(root + "/data/us/gdp/history.csv") == 200
        assert _status(root + "/data/us/gdp/release_impacts.csv") == 200
        assert _status(root + "/data/au/inflation/metadata.json") == 200
    finally:
        server.shutdown()
        server.server_close()


def _status(url: str) -> int:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status
