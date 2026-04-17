from __future__ import annotations

from datetime import date
from urllib.error import URLError

import pytest

from nowcast.g10.raw_store import RawFetchError, _fetch_url, write_raw_bytes


def test_raw_store_does_not_overwrite_changed_payload(tmp_path) -> None:
    first = write_raw_bytes(tmp_path, "fred_md", date(2026, 3, 1), "current.csv", b"one")
    same = write_raw_bytes(tmp_path, "fred_md", date(2026, 3, 1), "current.csv", b"one")
    revised = write_raw_bytes(tmp_path, "fred_md", date(2026, 3, 1), "current.csv", b"two")

    assert first.revision == 1
    assert first.created is True
    assert same.path == first.path
    assert same.created is False
    assert revised.revision == 2
    assert revised.path.read_bytes() == b"two"
    assert first.path.read_bytes() == b"one"


def test_fetch_url_retries_and_reports_source_url(monkeypatch) -> None:
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise URLError("blocked")

    monkeypatch.setattr("nowcast.g10.raw_store.urlopen", fail)
    monkeypatch.setattr("nowcast.g10.raw_store.sleep", lambda seconds: None)

    with pytest.raises(RawFetchError, match="https://example.test/current.csv"):
        _fetch_url("https://example.test/current.csv", timeout=1, retries=3, backoff_seconds=0)

    assert len(calls) == 3
