from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from nowcast.us_model import INDICATOR_SERIES, TARGET_SERIES, run_us_gdp_nowcast


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
    assert len({row["as_of_date"] for row in rows}) > 6
    statuses_by_date = {}
    for row in rows:
        statuses_by_date.setdefault(row["as_of_date"], set()).add(row["release_status"])
    assert all("new_release" in statuses for statuses in statuses_by_date.values())
    assert rows[-1]["release_status"] in {"new_release", "carried_forward"}
    assert {row["series_code"] for row in rows[-5:]} == {series_id.lower() for series_id in INDICATOR_SERIES}

    summary = json.loads((input_dir / "model_summary.json").read_text(encoding="utf-8"))
    assert summary["target"] == "GDPC1 real GDP QoQ saar"
    assert summary["latest_reference_period"] == "2026Q2"
    assert summary["training_rows"] >= 8


def _write_source_fixture(source_dir: Path) -> None:
    source_dir.mkdir(parents=True)
    quarters = _quarter_dates(2023, 1, 2026, 1)
    gdpc1_values = [100.0 + index * 0.7 for index, _ in enumerate(quarters)]
    _write_fred_csv(source_dir / f"{TARGET_SERIES}.csv", TARGET_SERIES, zip(quarters, gdpc1_values))

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
