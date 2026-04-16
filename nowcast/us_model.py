"""A transparent first-pass US GDP component nowcast model."""

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
TRAINING_START_QUARTER = "1992Q1"
MODEL_VERSION = "us_gdp_component_bridge_v0.2.0"


@dataclass(frozen=True)
class ComponentSpec:
    code: str
    name: str
    target_series: str
    category: str
    features: tuple[str, ...]
    sign: float = 1.0
    target_transform: str = "growth"


@dataclass(frozen=True)
class BridgeModel:
    component: ComponentSpec
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    feature_means: tuple[float, ...]
    expected_component_value: float
    aggregation_weight: float
    training_rows: int
    training_start: str
    training_end: str

    @property
    def intercept(self) -> float:
        return self.coefficients[0]


COMPONENTS = (
    ComponentSpec("pce_durables", "Consumer spending: durable goods", "PCDGCC96", "consumer spending", ("RSAFS", "DSPIC96", "PAYEMS")),
    ComponentSpec("pce_nondurables", "Consumer spending: nondurable goods", "PCNDGC96", "consumer spending", ("RSAFS", "DSPIC96", "CMRMTSPL")),
    ComponentSpec("pce_services", "Consumer spending: services", "PCESVC96", "consumer spending", ("DSPIC96", "PAYEMS")),
    ComponentSpec("nonres_fixed_investment", "Nonresidential fixed investment", "PNFI", "investment", ("DGORDER", "AMTMNO", "TLNRESCONS", "INDPRO")),
    ComponentSpec("residential_investment", "Residential investment", "PRFI", "investment", ("HOUST", "PERMIT", "TLRESCONS")),
    ComponentSpec("private_inventories", "Change in private inventories", "A014RE1Q156NBEA", "inventories", ("BUSINV", "ISRATIO", "AMTMNO"), target_transform="contribution"),
    ComponentSpec("exports", "Exports", "EXPGSC1", "trade", ("INDPRO", "CMRMTSPL", "DTWEXBGS")),
    ComponentSpec("imports", "Imports", "IMPGSC1", "trade", ("RSAFS", "CMRMTSPL", "DTWEXBGS"), sign=-1.0),
    ComponentSpec("federal_government", "Federal government spending", "FGCEC1", "government", ("PAYEMS", "FEDFUNDS")),
    ComponentSpec("state_local_government", "State and local government spending", "SLCEC1", "government", ("PAYEMS", "FEDFUNDS")),
)

INDICATOR_SERIES = tuple(sorted({feature for component in COMPONENTS for feature in component.features}))

SERIES_RELEASE_LAGS = {
    "PAYEMS": 7,
    "RSAFS": 14,
    "INDPRO": 16,
    "HOUST": 20,
    "DSPIC96": 30,
    "PERMIT": 20,
    "DGORDER": 24,
    "AMTMNO": 24,
    "BUSINV": 45,
    "ISRATIO": 45,
    "TTLCONS": 31,
    "TLRESCONS": 31,
    "TLNRESCONS": 31,
    "CMRMTSPL": 45,
    "DTWEXBGS": 1,
    "FEDFUNDS": 1,
}


def run_us_gdp_nowcast(
    *,
    source_dir: Path | str = "runs/source/us/fred",
    input_dir: Path | str = "runs/input/us",
    download: bool = True,
    observation_start: str = "1990-01-01",
) -> Path:
    """Download FRED data, estimate component bridges, and write model input CSV."""

    source_root = Path(source_dir)
    if download:
        download_us_fred_series(source_root, observation_start=observation_start)

    needed_series = {TARGET_SERIES, *INDICATOR_SERIES, *(component.target_series for component in COMPONENTS)}
    series = {
        series_id: read_fred_series(source_root / f"{series_id}.csv", series_id)
        for series_id in sorted(needed_series)
    }

    target_growth = _growth(series[TARGET_SERIES])
    latest_target_quarter = max(target_growth)
    target_quarter = _next_quarter(latest_target_quarter)
    indicator_growth = {series_id: _growth(series[series_id]) for series_id in INDICATOR_SERIES}
    models = [
        _fit_component_model(component, series, indicator_growth, target_quarter)
        for component in COMPONENTS
    ]

    rows = _historical_model_input_rows(
        models,
        series,
        indicator_growth,
        target_quarter=target_quarter,
        history_start=date(2026, 1, 1),
        max_as_of=date.today(),
    )

    output_path = Path(input_dir) / "model_input.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_model_input(output_path, rows)
    _write_summary(output_path.parent / "model_summary.json", models, target_quarter, rows)
    return output_path


def _fit_component_model(
    component: ComponentSpec,
    series: dict[str, list[tuple[date, float]]],
    indicator_growth: dict[str, dict[str, tuple[float, date]]],
    target_quarter: str,
) -> BridgeModel:
    target_values = _component_target_values(series[component.target_series], component.target_transform)
    training_quarters = [
        quarter
        for quarter in sorted(set(target_values) & set(_feature_quarters({feature: indicator_growth[feature] for feature in component.features})))
        if quarter >= TRAINING_START_QUARTER and quarter < target_quarter
    ]
    if len(training_quarters) < len(component.features) + 3:
        raise ValueError(f"not enough history to estimate {component.code}")

    x_train = [[indicator_growth[feature][quarter][0] for feature in component.features] for quarter in training_quarters]
    y_train = [target_values[quarter] for quarter in training_quarters]
    feature_means = tuple(_average(row[index] for row in x_train) for index in range(len(component.features)))
    design = [[1.0, *row] for row in x_train]
    coefficients = _solve_ridge_normal_equations(design, y_train, ridge=0.50)
    expected_component_value = coefficients[0] + sum(
        coefficient * expected
        for coefficient, expected in zip(coefficients[1:], feature_means)
    )
    weight = _aggregation_weight(component, series)
    return BridgeModel(
        component=component,
        feature_names=component.features,
        coefficients=tuple(coefficients),
        feature_means=feature_means,
        expected_component_value=expected_component_value,
        aggregation_weight=weight,
        training_rows=len(y_train),
        training_start=training_quarters[0],
        training_end=training_quarters[-1],
    )


def _historical_model_input_rows(
    models: list[BridgeModel],
    series: dict[str, list[tuple[date, float]]],
    indicator_growth: dict[str, dict[str, tuple[float, date]]],
    *,
    target_quarter: str,
    history_start: date,
    max_as_of: date,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    snapshot_dates = [
        release_date
        for release_date in _target_quarter_release_dates(series, target_quarter)
        if history_start <= release_date <= max_as_of
    ]
    if not snapshot_dates:
        latest_date = max(
            _release_date(series_id, period)
            for series_id in INDICATOR_SERIES
            for period, _ in series[series_id]
            if _release_date(series_id, period) <= max_as_of
        )
        snapshot_dates = [latest_date]

    for snapshot_date in snapshot_dates:
        rows.extend(_model_input_rows_as_of(models, indicator_growth, target_quarter, snapshot_date))
    return rows


def _model_input_rows_as_of(
    models: list[BridgeModel],
    indicator_growth: dict[str, dict[str, tuple[float, date]]],
    target_quarter: str,
    as_of_date: date,
) -> list[dict[str, object]]:
    component_forecasts = [
        _component_forecast_as_of(model, indicator_growth, target_quarter, as_of_date)
        for model in models
    ]
    baseline_nowcast = sum(model.expected_component_value * model.aggregation_weight for model in models)
    return [
        {
            "as_of_date": as_of_date.isoformat(),
            "reference_period": target_quarter,
            "baseline_nowcast": round(baseline_nowcast, 10),
            "series_code": model.component.code,
            "series_name": model.component.name,
            "release_date": release_date.isoformat(),
            "actual_value": round(forecast_value, 10),
            "expected_value": round(model.expected_component_value, 10),
            "impact_weight": round(model.aggregation_weight, 10),
            "category": model.component.category,
            "units": "percentage points" if model.component.target_transform == "contribution" else "percent",
            "release_status": release_status,
        }
        for model, (forecast_value, release_date, release_status) in zip(models, component_forecasts)
    ]


def _component_forecast_as_of(
    model: BridgeModel,
    indicator_growth: dict[str, dict[str, tuple[float, date]]],
    target_quarter: str,
    as_of_date: date,
) -> tuple[float, date, str]:
    feature_values = []
    release_dates = []
    released_any = False
    for feature, expected in zip(model.feature_names, model.feature_means):
        actual_value, release_date, released = _feature_value_as_of(
            feature,
            indicator_growth[feature],
            target_quarter,
            as_of_date,
            expected,
        )
        feature_values.append(actual_value)
        release_dates.append(release_date)
        released_any = released_any or released
    forecast = model.intercept + sum(
        coefficient * value
        for coefficient, value in zip(model.coefficients[1:], feature_values)
    )
    latest_release = max(release_dates)
    if not released_any:
        release_status = "pending"
    elif latest_release == as_of_date:
        release_status = "new_release"
    else:
        release_status = "carried_forward"
    return forecast, latest_release, release_status


def _feature_value_as_of(
    series_id: str,
    growth: dict[str, tuple[float, date]],
    target_quarter: str,
    as_of_date: date,
    expected_value: float,
) -> tuple[float, date, bool]:
    values = [
        (release_date, value)
        for quarter, (value, period) in growth.items()
        if quarter == target_quarter
        for release_date in [_release_date(series_id, period)]
        if release_date <= as_of_date
    ]
    if not values:
        return expected_value, as_of_date, False
    release_date, value = max(values, key=lambda item: item[0])
    return value, release_date, True


def _component_target_values(observations: list[tuple[date, float]], transform: str) -> dict[str, float]:
    if transform == "growth":
        return _growth(observations, include_release_date=False)
    if transform == "contribution":
        return {_quarter_label(period): value for period, value in observations}
    raise ValueError(f"unsupported component transform {transform}")


def _growth(observations: list[tuple[date, float]], *, include_release_date: bool = True) -> dict[str, tuple[float, date]] | dict[str, float]:
    rows = sorted(observations)
    growth = {}
    quarter_values: dict[str, list[tuple[date, float]]] = {}
    for period, value in rows:
        quarter_values.setdefault(_quarter_label(period), []).append((period, value))

    sorted_quarters = sorted(quarter_values)
    for quarter, prior_quarter in zip(sorted_quarters[1:], sorted_quarters[:-1]):
        current_average = _average(value for _, value in quarter_values[quarter])
        prior_average = _average(value for _, value in quarter_values[prior_quarter])
        if current_average <= 0 or prior_average <= 0:
            continue
        value = 400.0 * math.log(current_average / prior_average)
        latest_period = max(period for period, _ in quarter_values[quarter])
        growth[quarter] = (value, latest_period) if include_release_date else value
    return growth


def _feature_quarters(indicator_growth: dict[str, dict[str, tuple[float, date]]]) -> list[str]:
    quarters: set[str] | None = None
    for values in indicator_growth.values():
        if quarters is None:
            quarters = set(values)
        else:
            quarters &= set(values)
    return sorted(quarters or set())


def _aggregation_weight(component: ComponentSpec, series: dict[str, list[tuple[date, float]]]) -> float:
    if component.target_transform == "contribution":
        return 1.0
    component_level = series[component.target_series][-1][1]
    gdp_level = series[TARGET_SERIES][-1][1]
    return component.sign * component_level / gdp_level


def _target_quarter_release_dates(series: dict[str, list[tuple[date, float]]], target_quarter: str) -> list[date]:
    dates = {
        _release_date(series_id, period)
        for series_id in INDICATOR_SERIES
        for period, _ in series[series_id]
        if _quarter_label(period) == target_quarter
        and US_FRED_SERIES[series_id].frequency != "daily"
    }
    return sorted(dates)


def _release_date(series_id: str, period: date) -> date:
    return period + timedelta(days=SERIES_RELEASE_LAGS[series_id])


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


def _write_summary(path: Path, models: list[BridgeModel], target_quarter: str, rows: list[dict[str, object]]) -> None:
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
        "model": MODEL_VERSION,
        "target": "GDPC1 real GDP QoQ saar",
        "target_quarter": target_quarter,
        "latest_reference_period": latest_rows[0]["reference_period"],
        "latest_as_of_date": latest_rows[0]["as_of_date"],
        "nowcast_value": round(nowcast_value, 10),
        "training_rows": min(model.training_rows for model in models),
        "training_start": min(model.training_start for model in models),
        "training_end": max(model.training_end for model in models),
        "components": [
            {
                "code": model.component.code,
                "target_series": model.component.target_series,
                "features": list(model.feature_names),
                "aggregation_weight": model.aggregation_weight,
                "training_rows": model.training_rows,
            }
            for model in models
        ],
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


def _average(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items)
