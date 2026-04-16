"""Assemble country vintage parquets from raw source files."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.fred_md import download_fred_vintage, load_vintage_csv
from nowcast.g10.raw_store import source_vintage_dir
from nowcast.g10.vintage import validate_vintage_frame


def assemble_us_vintage(
    vintage_date: date,
    *,
    raw_root: Path | str = "data/raw",
    vintage_root: Path | str = "data/vintages",
    download: bool = False,
    vintage_month: str | None = None,
) -> Path:
    """Assemble the US FRED-MD/FRED-QD vintage into one tidy parquet."""

    if download:
        download_fred_vintage("fred_md", vintage_date=vintage_date, raw_root=raw_root, vintage=vintage_month)
        download_fred_vintage("fred_qd", vintage_date=vintage_date, raw_root=raw_root, vintage=vintage_month)

    md_path = _latest_raw_file(raw_root, "fred_md", vintage_date, "current.csv" if vintage_month is None else f"{vintage_month}.csv")
    qd_path = _latest_raw_file(raw_root, "fred_qd", vintage_date, "current.csv" if vintage_month is None else f"{vintage_month}.csv")
    monthly = load_vintage_csv(md_path, vintage_date=vintage_date, freq="M")
    quarterly = load_vintage_csv(qd_path, vintage_date=vintage_date, freq="Q")
    frame = pd.concat([monthly, quarterly], ignore_index=True)
    validate_vintage_frame(frame, as_of=vintage_date)

    output = Path(vintage_root) / "US" / f"{vintage_date.isoformat()}.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    _write_vintage_manifest(output.with_suffix(".json"), frame, md_path, qd_path)
    return output


def _latest_raw_file(raw_root: Path | str, source: str, vintage_date: date, filename: str) -> Path:
    revision = 1
    latest: Path | None = None
    while True:
        candidate = source_vintage_dir(raw_root, source, vintage_date, revision=revision) / filename
        if candidate.exists():
            latest = candidate
            revision += 1
            continue
        break
    if latest is None:
        raise FileNotFoundError(f"missing raw {source} {filename} for {vintage_date}")
    return latest


def _write_vintage_manifest(path: Path, frame: pd.DataFrame, md_path: Path, qd_path: Path) -> None:
    payload = {
        "iso": "US",
        "vintage_date": str(frame["vintage_date"].iloc[0]),
        "row_count": int(len(frame)),
        "series_count": int(frame["series_id"].nunique()),
        "monthly_series": int(frame.loc[frame["freq"] == "M", "series_id"].nunique()),
        "quarterly_series": int(frame.loc[frame["freq"] == "Q", "series_id"].nunique()),
        "vintage_kind": sorted(str(item) for item in frame["vintage_kind"].unique()),
        "sources": {
            "fred_md": str(md_path),
            "fred_qd": str(qd_path),
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
