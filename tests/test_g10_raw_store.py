from __future__ import annotations

from datetime import date

from nowcast.g10.raw_store import write_raw_bytes


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

