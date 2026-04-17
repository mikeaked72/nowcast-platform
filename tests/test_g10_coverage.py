from __future__ import annotations

import shutil
import csv
from datetime import date
from pathlib import Path

from nowcast.g10.assemble import assemble_us_vintage
from nowcast.g10.coverage import check_config_coverage, write_coverage_matrix


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "g10_us"


def test_config_coverage_reports_missing_series(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)

    coverage = check_config_coverage("US", date(2026, 4, 1), vintage_root=vintage_root)

    assert coverage.available_series == 17
    assert coverage.missing_targets == ()
    assert "IPMANSICS" not in coverage.missing_panel_series
    assert "DGS10" in coverage.missing_panel_series
    assert coverage.coverage_ratio == 0.7576
    assert coverage.status() == "error"
    assert coverage.status(warning_threshold=0.7) == "warning"


def test_write_coverage_matrix(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)

    path = write_coverage_matrix("US", date(2026, 4, 1), tmp_path / "coverage.csv", vintage_root=vintage_root)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert any(row["role"] == "target" and row["series"] == "GDPC1" and row["status"] == "present" for row in rows)
    assert any(row["role"] == "panel" and row["series"] == "DGS10" and row["status"] == "missing" for row in rows)
