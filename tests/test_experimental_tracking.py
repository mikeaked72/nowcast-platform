from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from nowcast.experimental_tracking import build_tracking_run
from nowcast.publish import publish_sample_country


def test_tracking_run_uses_existing_processed_data_without_future_dates() -> None:
    run = build_tracking_run("au", "gdp", max_as_of=date(2026, 4, 16))

    assert run.latest.as_of_date <= date(2026, 4, 16)
    assert run.latest.source_observations
    assert all(item.release_date <= run.latest.as_of_date for item in run.latest.source_observations)
    assert {item.series_code for item in run.latest.source_observations} >= {"aus_m3", "aus_comm_usd"}


def test_publish_uses_tracking_outputs_for_au_inflation(tmp_path: Path) -> None:
    publish_sample_country("au", tmp_path)

    latest = json.loads((tmp_path / "au" / "inflation" / "latest.json").read_text(encoding="utf-8"))
    metadata = json.loads((tmp_path / "au" / "inflation" / "metadata.json").read_text(encoding="utf-8"))

    assert latest["model_status"] == "warning"
    assert latest["model_version"] == "tracking-0.1.0"
    assert latest["as_of_date"] <= date.today().isoformat()
    assert "Experimental data-backed tracker" in metadata["methodology"]
