from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.assemble import assemble_us_vintage
from nowcast.g10.panel import build_processed_panel


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "g10_us"


def test_assemble_us_vintage_and_build_processed_panel(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    shutil.copytree(FIXTURE_ROOT, raw_root)

    vintage_path = assemble_us_vintage(date(2026, 3, 1), raw_root=raw_root, vintage_root=tmp_path / "vintages")
    frame = pd.read_parquet(vintage_path)

    assert set(frame["freq"]) == {"M", "Q"}
    assert set(frame["vintage_kind"]) == {"real"}
    assert set(frame["series_id"]) == {
        "AWHMAN",
        "CES0500000003",
        "INDPRO",
        "IPMANSICS",
        "CUMFNS",
        "ICSA",
        "PAYEMS",
        "PPIACO",
        "CPIAUCSL",
        "RPI",
        "UNRATE",
        "CPILFESL",
        "DGS10",
        "EXJPUSx",
        "EXUSUKx",
        "HOUST",
        "CPATAX",
        "EXPGS",
        "GDPC1",
        "GPDIC1",
        "IMPGS",
        "S&P 500",
        "BAA",
        "TB3MS",
        "UMCSENTx",
    }

    paths = build_processed_panel(
        "US",
        date(2026, 3, 1),
        vintage_root=tmp_path / "vintages",
        processed_root=tmp_path / "processed",
    )
    monthly = pd.read_parquet(paths.monthly)
    quarterly = pd.read_parquet(paths.quarterly)
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))

    assert list(monthly.columns) == [
        "AWHMAN",
        "BAA",
        "CES0500000003",
        "CPIAUCSL",
        "CPILFESL",
        "CUMFNS",
        "DGS10",
        "EXJPUSx",
        "EXUSUKx",
        "HOUST",
        "ICSA",
        "INDPRO",
        "IPMANSICS",
        "PAYEMS",
        "PPIACO",
        "RPI",
        "S&P 500",
        "TB3MS",
        "UMCSENTx",
        "UNRATE",
    ]
    assert list(quarterly.columns) == ["CPATAX", "EXPGS", "GDPC1", "GPDIC1", "IMPGS"]
    assert manifest["monthly_series"] == 20
    assert manifest["quarterly_series"] == 5
    assert manifest["monthly_rows"] > 0
    assert manifest["quarterly_rows"] > 0
    assert monthly.index.is_monotonic_increasing

    vintage_manifest = json.loads(vintage_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert vintage_manifest["series_count"] == 25
    assert vintage_manifest["sources"]["fred_md"].endswith("current.csv")
