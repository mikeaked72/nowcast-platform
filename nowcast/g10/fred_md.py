"""FRED-MD/FRED-QD vintage CSV parsing."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd

from nowcast.g10.vintage import validate_vintage_frame


Frequency = Literal["M", "Q"]


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
    date_column = headers[0]
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

