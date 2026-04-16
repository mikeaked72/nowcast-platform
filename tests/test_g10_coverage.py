from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from nowcast.g10.assemble import assemble_us_vintage
from nowcast.g10.coverage import check_config_coverage


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "g10_us"


def test_config_coverage_reports_missing_series(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)

    coverage = check_config_coverage("US", date(2026, 4, 1), vintage_root=vintage_root)

    assert coverage.available_series == 8
    assert "CPATAX" in coverage.missing_targets
    assert "IPMANSICS" in coverage.missing_panel_series

