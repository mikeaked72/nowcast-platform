from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socketserver
import tempfile
import threading
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright
Error = playwright.Error


def test_dashboard_tabs_and_selectors_render_in_browser() -> None:
    with _served_site(Path("site")) as root, _browser_page() as page:
        page.goto(root + "/", wait_until="networkidle")

        page.get_by_role("button", name="Comparison").click()
        page.get_by_text("Run Comparison").wait_for()
        page.get_by_text("Estimate change").wait_for()

        page.get_by_role("button", name="Downloads").click()
        page.get_by_text("Artifact").wait_for()
        page.get_by_text("manifest").wait_for()
        page.get_by_text("Data Store Coverage").wait_for()

        page.select_option("#indicator-select", "gdp_experimental")
        page.get_by_role("button", name="Downloads").click()
        page.get_by_text("Replay vintages").wait_for()
        page.get_by_text("Replay Path").wait_for()

        page.select_option("#country-select", "au")
        page.select_option("#indicator-select", "inflation")
        page.get_by_text("Australia Inflation").wait_for()
        page.get_by_text("Data-backed experimental tracker").wait_for()
        page.get_by_text("experimental tracking proxy").wait_for()


def test_dashboard_reports_missing_indicator_payload(tmp_path: Path) -> None:
    site = _copy_site(tmp_path)
    (site / "data" / "us" / "gdp" / "latest.json").unlink()

    with _served_site(site) as root, _browser_page() as page:
        page.goto(root + "/", wait_until="networkidle")
        page.get_by_text("Could not render published nowcast data").wait_for()
        page.get_by_text("Could not load data/us/gdp/latest.json").wait_for()


def test_dashboard_reports_stale_schema_version(tmp_path: Path) -> None:
    site = _copy_site(tmp_path)
    latest_path = site / "data" / "us" / "gdp" / "latest.json"
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 0
    latest_path.write_text(json.dumps(payload), encoding="utf-8")

    with _served_site(site) as root, _browser_page() as page:
        page.goto(root + "/", wait_until="networkidle")
        page.get_by_text("schema_version must be 1").wait_for()


def test_dashboard_reports_malformed_csv_header(tmp_path: Path) -> None:
    site = _copy_site(tmp_path)
    history_path = site / "data" / "us" / "gdp" / "history.csv"
    text = history_path.read_text(encoding="utf-8")
    history_path.write_text(text.replace("model_version", "model_build", 1), encoding="utf-8")

    with _served_site(site) as root, _browser_page() as page:
        page.goto(root + "/", wait_until="networkidle")
        page.get_by_text("history.csv missing model_version").wait_for()


def test_dashboard_ignores_malformed_optional_provenance(tmp_path: Path) -> None:
    site = _copy_site(tmp_path)
    metadata_path = site / "data" / "us" / "gdp" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["downloads"].append("g10_experimental_summary.json")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    (site / "data" / "us" / "gdp" / "g10_experimental_summary.json").write_text("{bad json", encoding="utf-8")

    with _served_site(site) as root, _browser_page() as page:
        page.goto(root + "/", wait_until="networkidle")
        page.get_by_text("United States GDP").wait_for()
        page.get_by_role("button", name="Downloads").click()
        page.get_by_text("g10_experimental_summary.json").wait_for()


def _copy_site(tmp_path: Path) -> Path:
    destination = tmp_path / "site"
    shutil.copytree("site", destination)
    return destination


class _served_site:
    def __init__(self, directory: Path):
        self.directory = directory
        self.server: socketserver.TCPServer | None = None

    def __enter__(self) -> str:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.directory)
        self.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __exit__(self, *args: object) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


class _browser_page:
    def __enter__(self):
        if not _playwright_transport_available():
            pytest.skip("Playwright transport is unavailable in this Windows sandbox")
        try:
            self.playwright = sync_playwright().start()
        except PermissionError as exc:
            pytest.skip(f"Playwright could not start in this sandbox: {exc}")
        try:
            self.browser = self.playwright.chromium.launch()
        except Error as exc:
            self.playwright.stop()
            pytest.skip(f"Playwright Chromium browser is not installed: {exc}")
        self.page = self.browser.new_page()
        return self.page

    def __exit__(self, *args: object) -> None:
        self.browser.close()
        self.playwright.stop()


def _playwright_transport_available() -> bool:
    if os.name != "nt":
        return True
    try:
        import _winapi  # type: ignore[import-not-found]
    except ImportError:
        return True
    address = tempfile.mktemp(prefix=rf"\\.\pipe\pytest-playwright-{os.getpid()}-")
    h1 = h2 = None
    try:
        h1 = _winapi.CreateNamedPipe(
            address,
            _winapi.PIPE_ACCESS_INBOUND | _winapi.FILE_FLAG_FIRST_PIPE_INSTANCE,
            _winapi.PIPE_WAIT,
            1,
            0,
            8192,
            _winapi.NMPWAIT_WAIT_FOREVER,
            _winapi.NULL,
        )
        h2 = _winapi.CreateFile(
            address,
            _winapi.GENERIC_WRITE,
            0,
            _winapi.NULL,
            _winapi.OPEN_EXISTING,
            0,
            _winapi.NULL,
        )
        return True
    except PermissionError:
        return False
    finally:
        for handle in (h2, h1):
            if handle is not None:
                _winapi.CloseHandle(handle)
