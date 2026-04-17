from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from nowcast.g10.assemble import assemble_us_vintage
from nowcast.g10.experimental_publish import (
    ProxyWeights,
    estimate_experimental_gdp_proxy,
    publish_experimental_g10_gdp,
    publish_experimental_g10_gdp_replay,
)
from nowcast.g10.panel import build_processed_panel
from nowcast.g10.smoke import run_dfm_smoke
from nowcast.publish import publish_sample_country
from nowcast.schemas import validate_publish_dir


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "g10_us"


def test_publish_experimental_g10_gdp_writes_valid_site_payload(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    artifact_root = tmp_path / "artifacts"
    publish_root = tmp_path / "site-data"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)
    run_dfm_smoke("US", "2026-04-01", processed_root=processed_root, artifact_root=artifact_root, maxiter=2)

    result = publish_experimental_g10_gdp(
        "US",
        vintage_date=date(2026, 4, 1),
        processed_root=processed_root,
        vintage_root=vintage_root,
        artifact_root=artifact_root,
        publish_dir=publish_root,
    )

    validation = validate_publish_dir(publish_root, countries=["us"])
    assert validation.errors == ()
    latest = json.loads((result.indicator_dir / "latest.json").read_text(encoding="utf-8"))
    metadata = json.loads((result.indicator_dir / "metadata.json").read_text(encoding="utf-8"))
    summary = json.loads((result.indicator_dir / "g10_experimental_summary.json").read_text(encoding="utf-8"))
    with (result.indicator_dir / "release_impacts.csv").open(newline="", encoding="utf-8") as handle:
        release_rows = list(csv.DictReader(handle))
    with (result.indicator_dir / "contributions.csv").open(newline="", encoding="utf-8") as handle:
        contribution_rows = list(csv.DictReader(handle))

    assert latest["indicator_code"] == "gdp_experimental"
    assert latest["model_status"] == "warning"
    assert latest["estimate_value"] == 0.9469
    assert "g10_experimental_summary.json" in metadata["downloads"]
    assert summary["method"] == "blend:GDPC1+monthly_activity"
    assert summary["proxy_details"]["quarterly_series"] == "GDPC1"
    assert summary["proxy_details"]["weights"] == {"monthly": 0.3, "quarterly": 0.7}
    assert any(item["status"] == "available" for item in summary["source_availability"])
    assert {item["frequency"] for item in summary["impact_by_frequency"]} >= {"monthly"}
    assert (result.indicator_dir / "g10_smoke.json").exists()
    assert any(row["notes"] == "new_release" for row in release_rows)
    assert any(row["source"] == "prior_g10_proxy" and row["notes"] == "carried_forward" for row in release_rows)
    assert not any(row["notes"] == "pending" and row["category"] == "missing input" for row in release_rows)
    new_release_categories = {row["category"] for row in release_rows if row["notes"] == "new_release"}
    assert "monthly" not in new_release_categories
    assert "quarterly" not in new_release_categories
    assert new_release_categories & {"production", "investment", "output", "imports", "exports", "profits"}
    current_contribution = sum(
        float(row["contribution"])
        for row in contribution_rows
        if row["as_of_date"] == latest["as_of_date"]
    )
    assert current_contribution == pytest.approx(latest["delta_vs_prior"])


def test_estimate_experimental_gdp_proxy_blends_quarterly_gdp_and_monthly_activity(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)

    estimate = estimate_experimental_gdp_proxy("US", vintage_date=date(2026, 4, 1), processed_root=processed_root)

    assert estimate.nowcast_value == 0.9469
    assert estimate.prior_nowcast_value == 1.3487
    assert estimate.method == "blend:GDPC1+monthly_activity"


def test_estimate_experimental_gdp_proxy_accepts_custom_weights(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)

    estimate = estimate_experimental_gdp_proxy(
        "US",
        vintage_date=date(2026, 4, 1),
        processed_root=processed_root,
        weights=ProxyWeights(quarterly=1.0, monthly=0.0),
    )

    assert estimate.nowcast_value == 0.9709
    assert estimate.prior_nowcast_value == 1.4742


def test_publish_experimental_does_not_overwrite_existing_us_gdp(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    publish_root = tmp_path / "site-data"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)
    publish_sample_country("us", publish_root, input_path="tests/fixtures/us/model_input.csv")
    gdp_latest = publish_root / "us" / "gdp" / "latest.json"
    before = gdp_latest.read_text(encoding="utf-8")

    publish_experimental_g10_gdp(
        "US",
        vintage_date=date(2026, 4, 1),
        processed_root=processed_root,
        vintage_root=vintage_root,
        artifact_root=tmp_path / "artifacts",
        publish_dir=publish_root,
    )

    assert gdp_latest.read_text(encoding="utf-8") == before


def test_publish_experimental_reports_missing_smoke_artifact(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    publish_root = tmp_path / "site-data"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)

    result = publish_experimental_g10_gdp(
        "US",
        vintage_date=date(2026, 4, 1),
        processed_root=processed_root,
        vintage_root=vintage_root,
        artifact_root=tmp_path / "missing-artifacts",
        publish_dir=publish_root,
    )
    summary = json.loads((result.indicator_dir / "g10_experimental_summary.json").read_text(encoding="utf-8"))

    assert validate_publish_dir(publish_root, countries=["us"]).errors == ()
    assert "g10_smoke.json" in summary["missing_artifacts"]
    assert summary["smoke_converged"] is None
    assert not (result.indicator_dir / "g10_smoke.json").exists()


def test_publish_experimental_reports_missing_processed_manifest(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    publish_root = tmp_path / "site-data"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    assemble_us_vintage(date(2026, 4, 1), raw_root=raw_root, vintage_root=vintage_root)
    panel_paths = build_processed_panel("US", date(2026, 4, 1), vintage_root=vintage_root, processed_root=processed_root)
    panel_paths.manifest.unlink()

    result = publish_experimental_g10_gdp(
        "US",
        vintage_date=date(2026, 4, 1),
        processed_root=processed_root,
        vintage_root=vintage_root,
        artifact_root=tmp_path / "missing-artifacts",
        publish_dir=publish_root,
    )
    summary = json.loads((result.indicator_dir / "g10_experimental_summary.json").read_text(encoding="utf-8"))

    assert validate_publish_dir(publish_root, countries=["us"]).errors == ()
    assert "g10_processed_manifest.json" in summary["missing_artifacts"]
    assert not (result.indicator_dir / "g10_processed_manifest.json").exists()


def test_publish_experimental_replay_writes_multi_vintage_history(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    vintage_root = tmp_path / "vintages"
    processed_root = tmp_path / "processed"
    publish_root = tmp_path / "site-data"
    shutil.copytree(FIXTURE_ROOT, raw_root)
    for vintage in (date(2026, 3, 1), date(2026, 4, 1)):
        assemble_us_vintage(vintage, raw_root=raw_root, vintage_root=vintage_root)
        build_processed_panel("US", vintage, vintage_root=vintage_root, processed_root=processed_root)

    result = publish_experimental_g10_gdp_replay(
        "US",
        vintage_dates=[date(2026, 4, 1), date(2026, 3, 1)],
        processed_root=processed_root,
        vintage_root=vintage_root,
        artifact_root=tmp_path / "artifacts",
        publish_dir=publish_root,
    )

    validation = validate_publish_dir(publish_root, countries=["us"])
    assert validation.errors == ()
    with (result.indicator_dir / "history.csv").open(newline="", encoding="utf-8") as handle:
        history_rows = list(csv.DictReader(handle))
    with (result.indicator_dir / "release_impacts.csv").open(newline="", encoding="utf-8") as handle:
        impact_rows = list(csv.DictReader(handle))
    summary = json.loads((result.indicator_dir / "g10_experimental_summary.json").read_text(encoding="utf-8"))

    assert [row["as_of_date"] for row in history_rows] == ["2026-03-01", "2026-04-01"]
    assert history_rows[-1]["prior_estimate_value"] == history_rows[0]["estimate_value"]
    assert any(row["latest_as_of_date"] == "2026-04-01" and row["prior_as_of_date"] == "2026-03-01" for row in impact_rows)
    assert summary["replay_vintages"] == ["2026-03-01", "2026-04-01"]


def test_g10_run_experimental_us_cli_creates_valid_payload(tmp_path: Path) -> None:
    publish_root = tmp_path / "site-data"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nowcast.cli",
            "g10-run-experimental-us",
            "--vintage-date",
            "2026-04-01",
            "--raw-root",
            "tests/fixtures/g10_us",
            "--vintage-root",
            str(tmp_path / "vintages"),
            "--processed-root",
            str(tmp_path / "processed"),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--publish-dir",
            str(publish_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "validation ok" in result.stdout
    assert validate_publish_dir(publish_root, countries=["us"]).errors == ()
    latest = json.loads((publish_root / "us" / "gdp_experimental" / "latest.json").read_text(encoding="utf-8"))
    assert latest["estimate_value"] == 0.9469


def test_g10_replay_experimental_us_cli_creates_multi_vintage_payload(tmp_path: Path) -> None:
    publish_root = tmp_path / "site-data"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nowcast.cli",
            "g10-replay-experimental-us",
            "--vintage-dates",
            "2026-03-01,2026-04-01",
            "--raw-root",
            "tests/fixtures/g10_us",
            "--vintage-root",
            str(tmp_path / "vintages"),
            "--processed-root",
            str(tmp_path / "processed"),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--publish-dir",
            str(publish_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "validation ok" in result.stdout
    with (publish_root / "us" / "gdp_experimental" / "history.csv").open(newline="", encoding="utf-8") as handle:
        history_rows = list(csv.DictReader(handle))
    assert [row["as_of_date"] for row in history_rows] == ["2026-03-01", "2026-04-01"]
