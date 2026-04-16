from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from nowcast.g10.assemble import assemble_us_vintage
from nowcast.g10.dfm import statsmodels_available
from nowcast.g10.panel import build_processed_panel
from nowcast.g10.smoke import run_dfm_smoke


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "g10_us"


@pytest.mark.skipif(not statsmodels_available(), reason="statsmodels is not installed")
def test_run_dfm_smoke_writes_artifact(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    artifact_root = tmp_path / "artifacts"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)

    artifact = run_dfm_smoke("US", "2026-04-01", processed_root=processed_root, artifact_root=artifact_root, maxiter=2)
    payload = json.loads(artifact.path.read_text(encoding="utf-8"))

    assert payload["iso"] == "US"
    assert payload["model_class"].endswith("DynamicFactorMQ")
    assert payload["monthly_shape"][1] == 6
    assert payload["quarterly_shape"][1] == 2

