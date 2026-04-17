"""Immutable raw-source storage helpers for G10 data pulls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RawWriteResult:
    path: Path
    revision: int
    created: bool


class RawFetchError(RuntimeError):
    """Raised when a raw source cannot be fetched after retries."""


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
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> RawWriteResult:
    payload = _fetch_url(url, timeout=timeout, retries=retries, backoff_seconds=backoff_seconds)
    return write_raw_bytes(root, source, vintage_date, filename, payload)


def _fetch_url(url: str, *, timeout: int, retries: int, backoff_seconds: float) -> bytes:
    attempts = max(1, retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": "nowcast-platform/0.1"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, TimeoutError, URLError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            sleep(backoff_seconds * (2 ** (attempt - 1)))
    raise RawFetchError(f"failed to fetch {url} after {attempts} attempts: {last_error}") from last_error
