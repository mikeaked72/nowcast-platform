"""A transparent first-pass US GDP bridge nowcast model."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from nowcast.fred import US_FRED_SERIES, download_us_fred_series, read_fred_series


TARGET_SERIES = "GDPC1"
INDICATOR_SERIES = ("INDPRO", "PAYEMS", "RSAFS", "HOUST", "DSPIC96")
TRAINING_START_QUARTER = "1992Q1"
SERIES_RELEASE_LAGS = {
    "PAYEMS": 7,
    "RSAFS": 14,
    "INDPRO": 16,
    "HOUST": 20,
    "DSPIC96": 30,
}


@dataclass(frozen=True)
class BridgeModel:
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    feature_means: tuple[float, ...]
    training_rows: int
    training_start: str
    training_end: str

    @property
    def intercept(self) -> float:
        return self.coefficients[0]


def run_us_gdp_nowcast(
    *,
    source_dir: Path | str = "runs/source/us/fred",
    input_dir: Path | str = "runs/input/us",
    download: bool = True,
    observation_start: str = "1990-01-01",
) -> Path:
    """Download FRED data, estimate the bridge model, and write model input CSV."""

    source_root = Path(source_dir)
    if download:
        download_us_fred_series(source_root, observation_start=observation_start)

    series = {
        series_id: read_fred_series(source_root / f"{series_id}.csv", series_id)
        for series_id in (TARGET_SERIES, *INDICATOR_SERIES)
    }
    target_growth = _target_growth(series[TARGET_SERIES])
    indicator_growth = {
        series_id: _indicator_growth(series[series_id])
        for series_id in INDICATOR_SERIES
    }

    latest_target_quarter = max(target_growth)
    target_quarter = _next_quarter(latest_target_quarter)
    feature_quarters = _feature_quarters(indicator_growth)
    training_quarters = [
        quarter
        for quarter in sorted(set(target_growth) & set(feature_quarters))
        if quarter >= TRAINING_START_QUARTER and quarter < target_quarter
    ]
    if len(training_quarters) < len(INDICATOR_SERIES) + 3:
        raise ValueError("not enough overlapping FRED history to estimate US GDP model")

    x_train = [[indicator_growth[series_id][quarter][0] for series_id in INDICATOR_SERIES] for quarter in training_quarters]
    y_train = [target_growth[quarter] for quarter in training_quarters]
    model = _fit_bridge_model(x_train, y_train, training_quarters)

    rows = _historical_model_input_rows(
        model,
        series,
        target_quarter=target_quarter,
        history_start=date(2026, 1, 1),
    )

    output_path = Path(input_dir) / "model_input.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_model_input(output_path, rows)
    _write_summary(output_path.parent / "model_summary.json", model, target_quarter, rows)
    return output_path


def _target_growth(observations: list[tuple[date, float]]) -> dict[str, float]:
    rows = sorted(observations)
    growth: dict[str, float] = {}
    for (period, value), (_, prior_value) in zip(rows[1:], rows[:-1]):
        growth[_quarter_label(period)] = 400.0 * math.log(value / prior_value)
    return growth


def _indicator_growth(observations: list[tuple[date, float]]) -> dict[str, tuple[float, date]]:
    quarter_values: dict[str, list[tuple[date, float]]] = {}
    for period, value in observations:
        quarter_values.setdefault(_quarter_label(period), []).append((period, value))

    growth: dict[str, tuple[float, date]] = {}
    sorted_quarters = sorted(quarter_values)
    for quarter, prior_quarter in zip(sorted_quarters[1:], sorted_quarters[:-1]):
        current_average = _average(value for _, value in quarter_values[quarter])
        prior_average = _average(value for _, value in quarter_values[prior_quarter])
        latest_release_date = max(period for period, _ in quarter_values[quarter])
        growth[quarter] = (400.0 * math.log(current_average / prior_average), latest_release_date)
    return growth


def _feature_quarters(indicator_growth: dict[str, dict[str, tuple[float, date]]]) -> list[str]:
    quarters: set[str] | None = None
    for values in indicator_growth.values():
        if quarters is None:
            quarters = set(values)
        else:
            quarters &= set(values)
    return sorted(quarters or set())


def _fit_bridge_model(x_train: list[list[float]], y_train: list[float], quarters: list[str]) -> BridgeModel:
    feature_means = tuple(_average(row[index] for row in x_train) for index in range(len(INDICATOR_SERIES)))
    design = [[1.0, *row] for row in x_train]
    coefficients = _solve_ridge_normal_equations(design, y_train, ridge=0.25)
    return BridgeModel(
        feature_names=INDICATOR_SERIES,
        coefficients=tuple(coefficients),
        feature_means=feature_means,
        training_rows=len(y_train),
        training_start=quarters[0],
        training_end=quarters[-1],
    )


def _historical_model_input_rows(
    model: BridgeModel,
    series: dict[str, list[tuple[date, float]]],
    *,
    target_quarter: str,
    history_start: date,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    latest_indicator_date = max(
        _release_date(series_id, period)
        for series_id in INDICATOR_SERIES
        for period, _ in series[series_id]
    )
    snapshot_dates = [
        release_date
        for release_date in _target_quarter_release_dates(series, target_quarter)
        if release_date >= history_start and release_date <= latest_indicator_date
    ]
    if not snapshot_dates:
        snapshot_dates = [latest_indicator_date]

    for snapshot_date in snapshot_dates:
        rows.extend(_model_input_rows_as_of(model, series, target_quarter, snapshot_date))

    if not rows:
        rows = _model_input_rows(
            model,
            {
                series_id: _indicator_growth(series[series_id])
                for series_id in INDICATOR_SERIES
            },
            [target_quarter],
        )
    return rows


def _model_input_rows_as_of(
    model: BridgeModel,
    series: dict[str, list[tuple[date, float]]],
    target_quarter: str,
    as_of_date: date,
) -> list[dict[str, object]]:
    baseline_nowcast = model.intercept + sum(
        coefficient * expected
        for coefficient, expected in zip(model.coefficients[1:], model.feature_means)
    )
    rows: list[dict[str, object]] = []
    for series_id, coefficient, expected_value in zip(
        INDICATOR_SERIES,
        model.coefficients[1:],
        model.feature_means,
    ):
        actual_value, release_date, release_status = _quarter_growth_as_of(
            series_id,
            series[series_id],
            target_quarter,
            as_of_date,
            expected_value,
        )
        metadata = US_FRED_SERIES[series_id]
        rows.append(
            {
                "as_of_date": as_of_date.isoformat(),
                "reference_period": target_quarter,
                "baseline_nowcast": round(baseline_nowcast, 10),
                "series_code": series_id.lower(),
                "series_name": metadata.name,
                "release_date": release_date.isoformat(),
                "actual_value": round(actual_value, 10),
                "expected_value": round(expected_value, 10),
                "impact_weight": round(coefficient, 10),
                "category": metadata.category,
                "units": metadata.units,
                "release_status": release_status,
            }
        )
    return rows


def _quarter_growth_as_of(
    series_id: str,
    observations: list[tuple[date, float]],
    target_quarter: str,
    as_of_date: date,
    expected_value: float,
) -> tuple[float, date, str]:
    prior_quarter = _previous_quarter(target_quarter)
    current_values = [
        (period, value)
        for period, value in observations
        if _quarter_label(period) == target_quarter and _release_date(series_id, period) <= as_of_date
    ]
    if not current_values:
        return expected_value, as_of_date, "pending"
    prior_values = [
        value
        for period, value in observations
        if _quarter_label(period) == prior_quarter
    ]
    if not prior_values:
        return expected_value, as_of_date, "pending"
    current_average = _average(value for _, value in current_values)
    prior_average = _average(prior_values)
    latest_release_date = max(_release_date(series_id, period) for period, _ in current_values)
    release_status = "new_release" if latest_release_date == as_of_date else "carried_forward"
    return 400.0 * math.log(current_average / prior_average), latest_release_date, release_status


def _target_quarter_release_dates(series: dict[str, list[tuple[date, float]]], target_quarter: str) -> list[date]:
    dates = {
        _release_date(series_id, period)
        for series_id in INDICATOR_SERIES
        for period, _ in series[series_id]
        if _quarter_label(period) == target_quarter
    }
    return sorted(dates)


def _release_date(series_id: str, period: date) -> date:
    return period + timedelta(days=SERIES_RELEASE_LAGS[series_id])


def _model_input_rows(
    model: BridgeModel,
    indicator_growth: dict[str, dict[str, tuple[float, date]]],
    quarters: list[str],
    *,
    as_of_date: date | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for quarter in quarters:
        feature_values = [indicator_growth[series_id][quarter][0] for series_id in INDICATOR_SERIES]
        baseline_nowcast = model.intercept + sum(
            coefficient * expected
            for coefficient, expected in zip(model.coefficients[1:], model.feature_means)
        )
        row_as_of_date = as_of_date or max(indicator_growth[series_id][quarter][1] for series_id in INDICATOR_SERIES)
        for series_id, coefficient, expected_value, actual_value in zip(
            INDICATOR_SERIES,
            model.coefficients[1:],
            model.feature_means,
            feature_values,
        ):
            metadata = US_FRED_SERIES[series_id]
            rows.append(
                {
                    "as_of_date": row_as_of_date.isoformat(),
                    "reference_period": quarter,
                    "baseline_nowcast": round(baseline_nowcast, 10),
                    "series_code": series_id.lower(),
                    "series_name": metadata.name,
                    "release_date": indicator_growth[series_id][quarter][1].isoformat(),
                    "actual_value": round(actual_value, 10),
                    "expected_value": round(expected_value, 10),
                    "impact_weight": round(coefficient, 10),
                    "category": metadata.category,
                    "units": metadata.units,
                }
            )
    return rows


def _write_model_input(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "as_of_date",
        "reference_period",
        "baseline_nowcast",
        "series_code",
        "series_name",
        "release_date",
        "actual_value",
        "expected_value",
        "impact_weight",
        "category",
        "units",
        "release_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, model: BridgeModel, target_quarter: str, rows: list[dict[str, object]]) -> None:
    latest_as_of_date = rows[-1]["as_of_date"]
    latest_rows = [
        row
        for row in rows
        if row["reference_period"] == rows[-1]["reference_period"] and row["as_of_date"] == latest_as_of_date
    ]
    nowcast_value = float(latest_rows[0]["baseline_nowcast"]) + sum(
        (float(row["actual_value"]) - float(row["expected_value"])) * float(row["impact_weight"])
        for row in latest_rows
    )
    payload = {
        "model": "us_gdp_bridge_v1",
        "target": "GDPC1 real GDP QoQ saar",
        "target_quarter": target_quarter,
        "latest_reference_period": latest_rows[0]["reference_period"],
        "latest_as_of_date": latest_rows[0]["as_of_date"],
        "nowcast_value": round(nowcast_value, 10),
        "training_rows": model.training_rows,
        "training_start": model.training_start,
        "training_end": model.training_end,
        "features": list(model.feature_names),
        "coefficients": list(model.coefficients),
        "feature_means": list(model.feature_means),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _solve_ridge_normal_equations(x: list[list[float]], y: list[float], *, ridge: float) -> list[float]:
    width = len(x[0])
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, target in zip(x, y):
        for left in range(width):
            xty[left] += row[left] * target
            for right in range(width):
                xtx[left][right] += row[left] * row[right]
    for index in range(1, width):
        xtx[index][index] += ridge
    return _solve_linear_system(xtx, xty)


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for pivot_index in range(size):
        best_row = max(range(pivot_index, size), key=lambda row: abs(augmented[row][pivot_index]))
        if abs(augmented[best_row][pivot_index]) < 1e-12:
            raise ValueError("model matrix is singular")
        augmented[pivot_index], augmented[best_row] = augmented[best_row], augmented[pivot_index]
        pivot = augmented[pivot_index][pivot_index]
        augmented[pivot_index] = [value / pivot for value in augmented[pivot_index]]
        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            augmented[row_index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row_index], augmented[pivot_index])
            ]
    return [row[-1] for row in augmented]


def _quarter_label(period: date) -> str:
    quarter = (period.month - 1) // 3 + 1
    return f"{period.year}Q{quarter}"


def _next_quarter(quarter: str) -> str:
    year = int(quarter[:4])
    quarter_number = int(quarter[-1])
    if quarter_number == 4:
        return f"{year + 1}Q1"
    return f"{year}Q{quarter_number + 1}"


def _previous_quarter(quarter: str) -> str:
    year = int(quarter[:4])
    quarter_number = int(quarter[-1])
    if quarter_number == 1:
        return f"{year - 1}Q4"
    return f"{year}Q{quarter_number - 1}"


def _month_start_dates(start: date, end: date) -> list[date]:
    dates: list[date] = []
    current = date(start.year, start.month, 1)
    while current <= end:
        dates.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return dates


def _average(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items)
