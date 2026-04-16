"""Build model-ready monthly and quarterly panels from tidy vintages."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.transforms import transform_values
from nowcast.g10.vintage import validate_vintage_frame


@dataclass(frozen=True)
class ProcessedPanelPaths:
    root: Path
    monthly: Path
    quarterly: Path
    manifest: Path


def build_processed_panel(
    iso: str,
    vintage_date: date,
    *,
    vintage_root: Path | str = "data/vintages",
    processed_root: Path | str = "data/processed",
) -> ProcessedPanelPaths:
    """Apply tcodes and write monthly/quarterly model matrices."""

    vintage_path = Path(vintage_root) / iso.upper() / f"{vintage_date.isoformat()}.parquet"
    frame = pd.read_parquet(vintage_path)
    validate_vintage_frame(frame, as_of=vintage_date)
    transformed = transform_vintage_frame(frame)
    root = Path(processed_root) / iso.upper()
    root.mkdir(parents=True, exist_ok=True)
    monthly_path = root / f"monthly_{vintage_date.isoformat()}.parquet"
    quarterly_path = root / f"quarterly_{vintage_date.isoformat()}.parquet"
    manifest_path = root / f"panel_{vintage_date.isoformat()}.json"
    _to_wide(transformed[transformed["freq"] == "M"]).to_parquet(monthly_path)
    _to_wide(transformed[transformed["freq"] == "Q"]).to_parquet(quarterly_path)
    _write_manifest(manifest_path, iso.upper(), vintage_date, transformed)
    return ProcessedPanelPaths(root=root, monthly=monthly_path, quarterly=quarterly_path, manifest=manifest_path)


def transform_vintage_frame(frame: pd.DataFrame) -> pd.DataFrame:
    validate_vintage_frame(frame)
    rows = []
    for series_id, group in frame.sort_values(["series_id", "date"]).groupby("series_id", sort=True):
        tcode = int(group["tcode"].iloc[0])
        transformed_values = transform_values(group["value"].tolist(), tcode)
        for (_, row), transformed in zip(group.iterrows(), transformed_values):
            if transformed is None:
                continue
            rows.append(
                {
                    "date": row["date"],
                    "series_id": series_id,
                    "value": transformed,
                    "freq": row["freq"],
                    "tcode": tcode,
                    "vintage_date": row["vintage_date"],
                    "vintage_kind": row["vintage_kind"],
                }
            )
    return pd.DataFrame.from_records(rows)


def _to_wide(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    wide = frame.pivot_table(index="date", columns="series_id", values="value", aggfunc="last")
    return wide.sort_index().sort_index(axis=1)


def _write_manifest(path: Path, iso: str, vintage_date: date, frame: pd.DataFrame) -> None:
    payload = {
        "iso": iso,
        "vintage_date": vintage_date.isoformat(),
        "row_count": int(len(frame)),
        "monthly_series": int(frame.loc[frame["freq"] == "M", "series_id"].nunique()),
        "quarterly_series": int(frame.loc[frame["freq"] == "Q", "series_id"].nunique()),
        "vintage_kind": sorted(str(item) for item in frame["vintage_kind"].unique()),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
