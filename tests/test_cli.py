from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from nowcast.pipeline import parse_as_of
from nowcast.schemas import validate_publish_dir


def test_parse_as_of_accepts_month_or_date() -> None:
    assert parse_as_of("2026-03").isoformat() == "2026-03-31"
    assert parse_as_of("2026-03-14").isoformat() == "2026-03-14"
    assert parse_as_of(None) is None


def test_package_cli_creates_valid_country_output(tmp_path: Path) -> None:
    publish_dir = tmp_path / "site-data"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nowcast.cli",
            "run",
            "--country",
            "us",
            "--publish-dir",
            str(publish_dir),
            "--input-path",
            "tests/fixtures/us/model_input.csv",
            "--as-of",
            "2026-03",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    validation = validate_publish_dir(publish_dir, countries=["us"])
    assert validation.errors == ()
