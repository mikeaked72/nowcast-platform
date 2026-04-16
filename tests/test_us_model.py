from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from nowcast.us_model import COMPONENTS, INDICATOR_SERIES, MODEL_VERSION, TARGET_SERIES, run_us_gdp_nowcast


def test_us_model_writes_input_from_source_files(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    input_dir = tmp_path / "input"
    _write_source_fixture(source_dir)

    output_path = run_us_gdp_nowcast(source_dir=source_dir, input_dir=input_dir, download=False)

    assert output_path == input_dir / "model_input.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert rows[-1]["reference_period"] == "2026Q2"
    assert len({row["as_of_date"] for row in rows}) >= 4
    statuses_by_date = {}
    for row in rows:
        statuses_by_date.setdefault(row["as_of_date"], set()).add(row["release_status"])
    assert set().union(*statuses_by_date.values()) <= {"new_release", "carried_forward", "pending"}
    assert rows[-1]["release_status"] in {"new_release", "carried_forward", "pending"}
    latest_as_of_date = rows[-1]["as_of_date"]
    latest_rows = [row for row in rows if row["as_of_date"] == latest_as_of_date]
    assert {row["series_code"] for row in latest_rows} == {component.code for component in COMPONENTS}

    summary = json.loads((input_dir / "model_summary.json").read_text(encoding="utf-8"))
    assert summary["model"] == MODEL_VERSION
    assert summary["target"] == "GDPC1 real GDP QoQ saar"
    assert summary["latest_reference_period"] == "2026Q2"
    assert summary["training_rows"] >= 8
    assert {component["code"] for component in summary["components"]} == {component.code for component in COMPONENTS}


def _write_source_fixture(source_dir: Path) -> None:
    source_dir.mkdir(parents=True)
    quarters = _quarter_dates(2023, 1, 2026, 1)
    gdpc1_values = [100.0 + index * 0.7 for index, _ in enumerate(quarters)]
    _write_fred_csv(source_dir / f"{TARGET_SERIES}.csv", TARGET_SERIES, zip(quarters, gdpc1_values))
    for component_index, component in enumerate(COMPONENTS):
        if component.target_transform == "contribution":
            values = [0.05 + 0.01 * ((index + component_index) % 5) for index, _ in enumerate(quarters)]
        else:
            values = [
                80.0 + component_index * 9.0 + index * (0.5 + component_index * 0.03)
                for index, _ in enumerate(quarters)
            ]
        _write_fred_csv(source_dir / f"{component.target_series}.csv", component.target_series, zip(quarters, values))

    months = _month_dates(2023, 1, 2026, 6)
    for series_index, series_id in enumerate(INDICATOR_SERIES):
        values = [100.0 + series_index * 10.0 + month_index * (0.4 + series_index * 0.05) for month_index, _ in enumerate(months)]
        _write_fred_csv(source_dir / f"{series_id}.csv", series_id, zip(months, values))


def _write_fred_csv(path: Path, series_id: str, rows: object) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["DATE", series_id])
        for period, value in rows:
            writer.writerow([period.isoformat(), value])


def _quarter_dates(start_year: int, start_quarter: int, end_year: int, end_quarter: int) -> list:
    dates = []
    year = start_year
    quarter = start_quarter
    while (year, quarter) <= (end_year, end_quarter):
        dates.append(date(year, (quarter - 1) * 3 + 1, 1))
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1
    return dates


def _month_dates(start_year: int, start_month: int, end_year: int, end_month: int) -> list:
    dates = []
    year = start_year
    month = start_month
    while (year, month) <= (end_year, end_month):
        dates.append(date(year, month, 1))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return dates
