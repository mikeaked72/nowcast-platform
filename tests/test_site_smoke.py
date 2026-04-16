from __future__ import annotations

import functools
import http.server
import json
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
        assert _status(root + "/_headers") == 200
        assert _status(root + "/data/countries.json") == 200
        assert _status(root + "/data/manifest.json") == 200
        assert _status(root + "/data/us/gdp/latest.json") == 200
        assert _status(root + "/data/us/gdp/history.csv") == 200
        assert _status(root + "/data/us/gdp/release_impacts.csv") == 200
        assert _status(root + "/data/au/inflation/metadata.json") == 200
        assert "validatePayload" in _text(root + "/app.js")
        assert "provenancePanel" in _text(root + "/app.js")
        assert "renderComparison" in _text(root + "/app.js")
        assert "model-status-badge" in _text(root + "/styles.css")
        manifest = json.loads(_text(root + "/data/manifest.json"))
        assert manifest["schema_version"] == 1
        assert manifest["country_count"] >= 2
        latest = json.loads(_text(root + "/data/us/gdp/latest.json"))
        assert latest["schema_version"] == 1
        assert latest["model_version"]
        release_header = _text(root + "/data/us/gdp/release_impacts.csv").splitlines()[0]
        assert "source" in release_header
        assert "source_url" in release_header
        headers_text = _text(root + "/_headers")
        assert "/data/*.json" in headers_text
        assert "max-age=60" in headers_text
    finally:
        server.shutdown()
        server.server_close()


def _status(url: str) -> int:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status


def _text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")
