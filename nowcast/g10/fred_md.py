"""FRED-MD/FRED-QD vintage CSV parsing."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

from nowcast.g10.raw_store import RawWriteResult, fetch_url_to_raw
from nowcast.g10.vintage import validate_vintage_frame


Frequency = Literal["M", "Q"]
FRED_BASE_URL = "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md"
FRED_INDEX_URL = "https://www.stlouisfed.org/research/economists/mccracken/fred-databases"
FRED_MD_CURRENT_URL = f"{FRED_BASE_URL}/monthly/current-md.csv"
FRED_QD_CURRENT_URL = f"{FRED_BASE_URL}/quarterly/current-qd.csv"
FRED_MD_MONTHLY_URL = f"{FRED_BASE_URL}/monthly/{{vintage}}-md.csv"
FRED_QD_QUARTERLY_URL = f"{FRED_BASE_URL}/quarterly/{{vintage}}-qd.csv"
_FRED_DOWNLOAD_HEADERS = {"User-Agent": "nowcast-platform/0.1"}


def fred_vintage_url(dataset: Literal["fred_md", "fred_qd"], vintage: str | None = None) -> str:
    """Return the public McCracken-Ng CSV URL for a vintage month or current."""

    if dataset == "fred_md":
        return FRED_MD_CURRENT_URL if vintage in {None, "current"} else FRED_MD_MONTHLY_URL.format(vintage=vintage)
    if dataset == "fred_qd":
        return FRED_QD_CURRENT_URL if vintage in {None, "current"} else FRED_QD_QUARTERLY_URL.format(vintage=vintage)
    raise ValueError(f"unsupported FRED dataset {dataset}")


def fred_vintage_filename(dataset: Literal["fred_md", "fred_qd"], vintage: str | None = None) -> str:
    """Return the local raw filename matching the public FRED-MD/QD download."""

    if dataset == "fred_md":
        return "current-md.csv" if vintage in {None, "current"} else f"{vintage}-md.csv"
    if dataset == "fred_qd":
        return "current-qd.csv" if vintage in {None, "current"} else f"{vintage}-qd.csv"
    raise ValueError(f"unsupported FRED dataset {dataset}")


def fred_fallback_current_vintage(as_of: date) -> str:
    """Return the prior calendar-month vintage used if live index discovery fails."""

    year = as_of.year
    month = as_of.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def discover_current_fred_vintage_urls(timeout: int = 60) -> dict[Literal["fred_md", "fred_qd"], str]:
    """Discover current FRED-MD/QD CSV URLs from the St. Louis Fed index page."""

    request = Request(FRED_INDEX_URL, headers=_FRED_DOWNLOAD_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")
    monthly = _first_csv_href(html, "monthly", "md")
    quarterly = _first_csv_href(html, "quarterly", "qd")
    return {"fred_md": monthly, "fred_qd": quarterly}


def _first_csv_href(html: str, section: Literal["monthly", "quarterly"], suffix: Literal["md", "qd"]) -> str:
    pattern = re.compile(
        rf"https://www\.stlouisfed\.org/-/media/project/frbstl/stlouisfed/research/fred-md/{section}/"
        rf"(?:current|\d{{4}}-\d{{2}})-{suffix}\.csv",
        flags=re.IGNORECASE,
    )
    match = pattern.search(html)
    if match:
        return match.group(0)
    # The public page currently labels links as current.csv and dated .csv,
    # but the href targets include -md/-qd suffixes. Keep this explicit so a
    # changed page fails early instead of silently constructing a stale URL.
    raise ValueError(f"could not find FRED {section} {suffix} CSV link on {FRED_INDEX_URL}")


def download_fred_vintage(
    dataset: Literal["fred_md", "fred_qd"],
    *,
    vintage_date: date,
    raw_root: Path | str = "data/raw",
    vintage: str | None = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> RawWriteResult:
    """Download one FRED-MD or FRED-QD CSV into immutable raw storage."""

    url = fred_vintage_url(dataset, vintage)
    if vintage in {None, "current"}:
        try:
            url = discover_current_fred_vintage_urls(timeout=timeout)[dataset]
        except Exception:
            url = fred_vintage_url(dataset, fred_fallback_current_vintage(vintage_date))
    filename = Path(urlparse(url).path).name or fred_vintage_filename(dataset, vintage)
    return fetch_url_to_raw(
        url,
        root=raw_root,
        source=dataset,
        vintage_date=vintage_date,
        filename=filename,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )


def load_vintage_csv(
    path: Path | str,
    *,
    vintage_date: date,
    freq: Frequency,
    vintage_kind: str = "real",
) -> pd.DataFrame:
    """Load one McCracken-Ng vintage CSV into the tidy long schema.

    The parser handles the common FRED-MD/FRED-QD shape where row 1 is headers,
    row 2 contains transformation codes, and subsequent rows contain dated
    observations. It also tolerates fixture CSVs that omit the tcode row.
    """

    rows = _read_rows(path)
    if len(rows) < 2:
        raise ValueError(f"{path}: expected header plus at least one data row")
    headers = [item.strip() for item in rows[0]]
    if not headers:
        raise ValueError(f"{path}: missing header")
    series_ids = headers[1:]
    tcode_row = rows[1]
    has_tcodes = _looks_like_tcode_row(tcode_row, len(headers))
    tcodes = _tcodes(series_ids, tcode_row[1:] if has_tcodes else [])
    data_rows = rows[2:] if has_tcodes else rows[1:]

    records = []
    for row in data_rows:
        if not row or not row[0].strip():
            continue
        period = _parse_period(row[0].strip(), freq)
        for index, series_id in enumerate(series_ids, start=1):
            value = _parse_float(row[index] if index < len(row) else "")
            if value is None:
                continue
            records.append(
                {
                    "date": period,
                    "series_id": series_id,
                    "value": value,
                    "freq": freq,
                    "tcode": tcodes[series_id],
                    "vintage_date": vintage_date,
                    "vintage_kind": vintage_kind,
                    "source": Path(path).name,
                }
            )
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        raise ValueError(f"{path}: no numeric observations")
    validate_vintage_frame(frame, as_of=vintage_date)
    return frame


def _read_rows(path: Path | str) -> list[list[str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


def _looks_like_tcode_row(row: list[str], width: int) -> bool:
    if len(row) < width:
        return False
    codes = [item.strip() for item in row[1:width]]
    return bool(codes) and all(code in {"1", "2", "3", "4", "5", "6", "7"} for code in codes)


def _tcodes(series_ids: list[str], raw_codes: list[str]) -> dict[str, int]:
    return {
        series_id: int(raw_codes[index]) if index < len(raw_codes) and raw_codes[index].strip() else 1
        for index, series_id in enumerate(series_ids)
    }


def _parse_period(value: str, freq: Frequency) -> date:
    parsed = pd.to_datetime(value)
    if freq == "Q":
        return parsed.to_period("Q").end_time.date().replace(day=1)
    return parsed.to_period("M").to_timestamp().date()


def _parse_float(value: str) -> float | None:
    item = value.strip()
    if not item or item in {".", "NA", "NaN", "nan"}:
        return None
    return float(item)
