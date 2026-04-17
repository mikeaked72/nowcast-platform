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
        assert _status(root + "/data/source_coverage.json") == 200
        assert _status(root + "/data/us/gdp/latest.json") == 200
        assert _status(root + "/data/us/gdp/history.csv") == 200
        assert _status(root + "/data/us/gdp/release_impacts.csv") == 200
        assert _status(root + "/data/us/gdp/model_summary.json") == 200
        assert _status(root + "/data/us/gdp/component_diagnostics.csv") == 200
        assert _status(root + "/data/us/gdp/data_inventory.csv") == 200
        assert _status(root + "/data/us/gdp_experimental/latest.json") == 200
        assert _status(root + "/data/us/gdp_experimental/history.csv") == 200
        assert _status(root + "/data/us/gdp_experimental/g10_experimental_summary.json") == 200
        assert _status(root + "/data/us/gdp_experimental/g10_smoke.json") == 200
        assert _status(root + "/data/au/inflation/metadata.json") == 200
        assert _status(root + "/data/de/gdp/latest.json") == 200
        assert _status(root + "/data/br/inflation/latest.json") == 200
        assert "validatePayload" in _text(root + "/app.js")
        assert "provenancePanel" in _text(root + "/app.js")
        assert "renderComparison" in _text(root + "/app.js")
        assert "diagnosticsPanel" in _text(root + "/app.js")
        assert "Data-backed experimental tracker" in _text(root + "/app.js")
        assert "Experimental G10 model path" in _text(root + "/app.js")
        assert "releaseImpactGroups" in _text(root + "/app.js")
        assert "G10 estimate provenance" in _text(root + "/app.js")
        assert "Replay vintages" in _text(root + "/app.js")
        assert "Replay Path" in _text(root + "/app.js")
        assert "model-status-badge" in _text(root + "/styles.css")
        assert "model-notice" in _text(root + "/styles.css")
        assert "diagnostics-panel" in _text(root + "/styles.css")
        manifest = json.loads(_text(root + "/data/manifest.json"))
        assert manifest["schema_version"] == 1
        assert manifest["country_count"] >= 4
        us_manifest = next(country for country in manifest["countries"] if country["code"] == "us")
        g10_manifest = next(indicator for indicator in us_manifest["indicators"] if indicator["code"] == "gdp_experimental")
        assert "g10_experimental_summary.json" in g10_manifest["artifacts"]
        assert "g10_smoke.json" in g10_manifest["artifacts"]
        coverage = json.loads(_text(root + "/data/source_coverage.json"))
        assert coverage["schema_version"] == 1
        assert coverage["series_count"] >= 250
        assert any(country["code"] == "br" for country in coverage["countries"])
        assert any(country["code"] == "de" for country in coverage["countries"])
        latest = json.loads(_text(root + "/data/us/gdp/latest.json"))
        assert latest["schema_version"] == 1
        assert latest["model_version"]
        metadata = json.loads(_text(root + "/data/us/gdp/metadata.json"))
        assert "model_summary.json" in metadata["downloads"]
        assert "component_diagnostics.csv" in metadata["downloads"]
        summary = json.loads(_text(root + "/data/us/gdp/model_summary.json"))
        assert summary["latest_components"]
        diagnostics_header = _text(root + "/data/us/gdp/component_diagnostics.csv").splitlines()[0]
        assert "training_rmse" in diagnostics_header
        inventory_header = _text(root + "/data/us/gdp/data_inventory.csv").splitlines()[0]
        assert "target_quarter_status" in inventory_header
        tracking_latest = json.loads(_text(root + "/data/au/inflation/latest.json"))
        assert tracking_latest["model_status"] == "warning"
        assert tracking_latest["model_version"] == "tracking-0.1.0"
        g10_latest = json.loads(_text(root + "/data/us/gdp_experimental/latest.json"))
        assert g10_latest["model_version"] == "g10_dfm_experimental_v0.1.0"
        g10_history = _text(root + "/data/us/gdp_experimental/history.csv").splitlines()
        assert any("2026-03-01" in row for row in g10_history)
        assert any("2026-04-01" in row for row in g10_history)
        g10_summary = json.loads(_text(root + "/data/us/gdp_experimental/g10_experimental_summary.json"))
        assert g10_summary["replay_vintages"] == ["2026-03-01", "2026-04-01"]
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
