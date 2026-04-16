"""Immutable raw-source storage helpers for G10 data pulls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.request import urlopen


@dataclass(frozen=True)
class RawWriteResult:
    path: Path
    revision: int
    created: bool


def source_vintage_dir(root: Path | str, source: str, vintage_date: date, *, revision: int = 1) -> Path:
    suffix = "" if revision == 1 else f"_r{revision}"
    return Path(root) / source / f"{vintage_date.isoformat()}{suffix}"


def write_raw_bytes(
    root: Path | str,
    source: str,
    vintage_date: date,
    filename: str,
    payload: bytes,
) -> RawWriteResult:
    """Write raw bytes without mutating an existing different file."""

    revision = 1
    while True:
        directory = source_vintage_dir(root, source, vintage_date, revision=revision)
        path = directory / filename
        if not path.exists():
            directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            return RawWriteResult(path=path, revision=revision, created=True)
        if path.read_bytes() == payload:
            return RawWriteResult(path=path, revision=revision, created=False)
        revision += 1


def fetch_url_to_raw(
    url: str,
    *,
    root: Path | str,
    source: str,
    vintage_date: date,
    filename: str,
    timeout: int = 60,
) -> RawWriteResult:
    with urlopen(url, timeout=timeout) as response:
        payload = response.read()
    return write_raw_bytes(root, source, vintage_date, filename, payload)

