from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from nowcast.publish import publish_sample_country
from nowcast.schemas import validate_publish_dir


def test_publish_sample_country_writes_required_contract_files(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    indicator_dir = tmp_path / "us" / "gdp"
    assert (tmp_path / "countries.json").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (indicator_dir / "latest.json").exists()
    assert (indicator_dir / "history.csv").exists()
    assert (indicator_dir / "contributions.csv").exists()
    assert (indicator_dir / "release_impacts.csv").exists()
    assert (indicator_dir / "metadata.json").exists()

    result = validate_publish_dir(tmp_path, countries=["us"])
    assert result.errors == ()


def test_nowcast_latest_contains_required_fields(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    payload = json.loads((tmp_path / "us" / "gdp" / "latest.json").read_text(encoding="utf-8"))

    assert payload["country_code"] == "us"
    assert payload["country_name"] == "United States"
    assert payload["indicator_code"] == "gdp"
    assert payload["indicator_name"] == "GDP"
    assert payload["schema_version"] == 1
    assert payload["model_status"] == "ok"
    assert payload["delta_vs_prior"] == 0.3


def test_publish_uses_downloaded_input_when_present(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    country_input = input_dir / "us"
    country_input.mkdir(parents=True)
    (country_input / "model_input.csv").write_text(
        "\n".join(
            [
                "as_of_date,reference_period,baseline_nowcast,series_code,series_name,release_date,actual_value,expected_value,impact_weight,category,units",
                "2026-04-10,2026Q2,2.45,durable_goods,Durable goods,2026-04-09,1.0,0.5,0.4,demand,percent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    publish_sample_country("us", tmp_path / "publish", input_dir=input_dir)

    payload = json.loads((tmp_path / "publish" / "us" / "gdp" / "latest.json").read_text(encoding="utf-8"))
    assert payload["as_of_date"] == "2026-04-10"
    assert payload["reference_period"] == "2026Q2"
    assert payload["estimate_value"] == 2.65
    assert payload["prior_estimate_value"] is None
    assert payload["delta_vs_prior"] is None


def test_csv_outputs_include_required_columns(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    with (tmp_path / "us" / "gdp" / "history.csv").open(newline="", encoding="utf-8") as handle:
        history_columns = set(csv.DictReader(handle).fieldnames or [])
    assert {"as_of_date", "reference_period", "estimate_value", "prior_estimate_value", "delta_vs_prior", "model_version"} <= history_columns

    with (tmp_path / "us" / "gdp" / "release_impacts.csv").open(newline="", encoding="utf-8") as handle:
        news_columns = set(csv.DictReader(handle).fieldnames or [])
    assert {
        "release_name",
        "release_date",
        "indicator_code",
        "reference_period",
        "actual_value",
        "expected_value",
        "surprise",
        "impact",
        "direction",
        "latest_as_of_date",
        "prior_as_of_date",
        "source",
        "source_url",
    } <= news_columns


def test_validator_rejects_missing_schema_version(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    latest_path = tmp_path / "us" / "gdp" / "latest.json"
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    payload.pop("schema_version")
    latest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_publish_dir(tmp_path, countries=["us"])
    assert any("schema_version" in error for error in result.errors)


def test_validator_rejects_missing_payload_file(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")
    (tmp_path / "us" / "gdp" / "latest.json").unlink()

    result = validate_publish_dir(tmp_path, countries=["us"])
    assert any("latest.json" in error for error in result.errors)


def test_validator_rejects_stale_schema_version(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    latest_path = tmp_path / "us" / "gdp" / "latest.json"
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 0
    latest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_publish_dir(tmp_path, countries=["us"])
    assert any("schema_version must be 1" in error for error in result.errors)


def test_validator_rejects_malformed_history_header(tmp_path: Path) -> None:
    publish_sample_country("us", tmp_path, input_path="tests/fixtures/us/model_input.csv")

    history_path = tmp_path / "us" / "gdp" / "history.csv"
    text = history_path.read_text(encoding="utf-8")
    history_path.write_text(text.replace("model_version", "model_build", 1), encoding="utf-8")

    result = validate_publish_dir(tmp_path, countries=["us"])
    assert any("history.csv" in error and "model_version" in error for error in result.errors)


def test_workflow_script_smoke_run_and_validation(tmp_path: Path) -> None:
    publish_dir = tmp_path / "publish" / "us"

    run_result = subprocess.run(
        [
            sys.executable,
            "scripts/run_country.py",
            "--country",
            "us",
            "--publish-dir",
            str(publish_dir),
            "--input-path",
            "tests/fixtures/us/model_input.csv",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr

    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_outputs.py",
            "--country",
            "us",
            "--publish-dir",
            str(publish_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert validate_result.returncode == 0, validate_result.stderr
