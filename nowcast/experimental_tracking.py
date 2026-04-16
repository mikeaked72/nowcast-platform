"""Data-backed experimental tracking outputs for early site coverage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from nowcast.model_input import ModelRun, ModelSnapshot, SourceObservation


MODEL_VERSION = "tracking-0.1.0"


@dataclass(frozen=True)
class TrackingSeries:
    column: str
    name: str
    category: str
    frequency: str
    weight: float
    transform: str
    release_lag_days: int


@dataclass(frozen=True)
class TrackingSpec:
    country_code: str
    indicator_code: str
    reference_period: str
    units: str
    methodology: str
    series: tuple[TrackingSeries, ...]


TRACKING_SPECS = {
    ("us", "inflation"): TrackingSpec(
        "us",
        "inflation",
        "2026Q1",
        "percent annualized",
        "Experimental data-backed tracker using existing FRED CPI, core PCE price, and producer price series. Monthly source changes are converted to annualized rates and combined with fixed transparent weights.",
        (
            TrackingSeries("CPIAUCSL", "Consumer Price Index", "prices", "monthly", 0.45, "mom_annualized", 14),
            TrackingSeries("PCEPILFE", "Core PCE Price Index", "prices", "monthly", 0.35, "mom_annualized", 30),
            TrackingSeries("PPIACO", "Producer Price Index", "prices", "monthly", 0.20, "mom_annualized", 14),
        ),
    ),
    ("us", "exports"): TrackingSpec(
        "us",
        "exports",
        "2026Q1",
        "percent QoQ SAAR",
        "Experimental data-backed tracker using existing FRED industrial production, trade-weighted dollar, and broad demand proxies. It is a transparent proxy until direct trade source series are added.",
        (
            TrackingSeries("INDPRO", "Industrial Production Index", "production", "monthly", 0.45, "mom_annualized", 16),
            TrackingSeries("DTWEXBGS", "Trade Weighted U.S. Dollar Index", "fx", "daily", -0.30, "mom_annualized", 1),
            TrackingSeries("PAYEMS", "Nonfarm Payrolls", "labor", "monthly", 0.25, "mom_annualized", 7),
        ),
    ),
    ("us", "imports"): TrackingSpec(
        "us",
        "imports",
        "2026Q1",
        "percent QoQ SAAR",
        "Experimental data-backed tracker using existing FRED retail sales, employment, and dollar series as domestic-demand and relative-price proxies until direct import source series are added.",
        (
            TrackingSeries("RSAFS", "Advance Retail Sales", "demand", "monthly", 0.45, "mom_annualized", 14),
            TrackingSeries("PAYEMS", "Nonfarm Payrolls", "labor", "monthly", 0.30, "mom_annualized", 7),
            TrackingSeries("DTWEXBGS", "Trade Weighted U.S. Dollar Index", "fx", "daily", 0.25, "mom_annualized", 1),
        ),
    ),
    ("au", "gdp"): TrackingSpec(
        "au",
        "gdp",
        "2026Q1",
        "percent QoQ SAAR",
        "Experimental data-backed tracker using existing RBA money, short-rate, and commodity-price series. It is a transparent activity proxy until an Australia-specific GDP bridge model is added.",
        (
            TrackingSeries("AUS_M3", "M3 money", "money", "monthly", 0.30, "mom_annualized", 30),
            TrackingSeries("AUS_BROADMNY", "Broad money", "money", "monthly", 0.25, "mom_annualized", 30),
            TrackingSeries("AUS_BBSW90", "90-day bank bill swap rate", "financial", "monthly", -0.25, "level_change", 5),
            TrackingSeries("AUS_COMM_USD", "RBA commodity price index", "trade", "monthly", 0.20, "mom_annualized", 5),
        ),
    ),
    ("au", "inflation"): TrackingSpec(
        "au",
        "inflation",
        "2026Q1",
        "percent annualized",
        "Experimental data-backed tracker using existing ABS quarterly CPI and RBA commodity-price data. CPI receives most of the weight; commodity prices provide a timely cost-pressure proxy.",
        (
            TrackingSeries("AUS_CPI", "ABS CPI", "prices", "quarterly", 0.70, "qoq_annualized", 28),
            TrackingSeries("AUS_COMM_USD", "RBA commodity price index", "prices", "monthly", 0.30, "mom_annualized", 5),
        ),
    ),
}


def has_tracking_run(country_code: str, indicator_code: str) -> bool:
    return (country_code, indicator_code) in TRACKING_SPECS


def tracking_methodology(country_code: str, indicator_code: str) -> str:
    return TRACKING_SPECS[(country_code, indicator_code)].methodology


def build_tracking_run(
    country_code: str,
    indicator_code: str,
    *,
    processed_dir: Path | str = "store/processed",
    history_start: date = date(2026, 1, 1),
    max_as_of: date | None = None,
) -> ModelRun:
    spec = TRACKING_SPECS[(country_code, indicator_code)]
    max_as_of = max_as_of or date.today()
    panels = _load_panels(Path(processed_dir))
    transformed = {
        item.column: _transformed_series(panels[item.frequency][item.column], item.transform)
        for item in spec.series
    }
    release_calendar = sorted({
        period.date() + timedelta(days=item.release_lag_days)
        for item in spec.series
        for period in transformed[item.column].dropna().index
        if period.date() + timedelta(days=item.release_lag_days) >= history_start
        and period.date() + timedelta(days=item.release_lag_days) <= max_as_of
    })
    snapshots: list[ModelSnapshot] = []
    for as_of_date in release_calendar:
        observations = []
        for item in spec.series:
            source = transformed[item.column]
            release_dates = pd.Series(
                [period.date() + timedelta(days=item.release_lag_days) for period in source.index],
                index=source.index,
            )
            as_of_timestamp = pd.Timestamp(as_of_date)
            available = source[
                (release_dates <= as_of_date)
                & (source.index >= as_of_timestamp - pd.DateOffset(months=6))
            ].dropna()
            if available.empty:
                continue
            actual_period = available.index[-1]
            release_date = actual_period.date() + timedelta(days=item.release_lag_days)
            actual = float(available.iloc[-1])
            history = source[source.index < actual_period].dropna().tail(36)
            expected = float(history.mean()) if not history.empty else actual
            observations.append(
                SourceObservation(
                    as_of_date=as_of_date,
                    reference_period=_quarter_label(as_of_date),
                    baseline_nowcast=0.0,
                    series_code=item.column.lower(),
                    series_name=item.name,
                    release_date=release_date,
                    actual_value=actual,
                    expected_value=expected,
                    impact_weight=item.weight,
                    category=item.category,
                    units=spec.units,
                    release_status="new_release" if release_date == as_of_date else "carried_forward",
                )
            )
        if not observations:
            continue
        baseline = sum(item.expected_value * item.impact_weight for item in observations)
        observations = [
            SourceObservation(
                as_of_date=item.as_of_date,
                reference_period=item.reference_period,
                baseline_nowcast=baseline,
                series_code=item.series_code,
                series_name=item.series_name,
                release_date=item.release_date,
                actual_value=item.actual_value,
                expected_value=item.expected_value,
                impact_weight=item.impact_weight,
                category=item.category,
                units=item.units,
                release_status=item.release_status,
            )
            for item in observations
        ]
        nowcast = baseline + sum(item.impact_on_nowcast for item in observations)
        snapshots.append(
            ModelSnapshot(
                as_of_date=as_of_date,
                reference_period=_quarter_label(as_of_date),
                nowcast_value=round(nowcast, 10),
                prior_nowcast_value=snapshots[-1].nowcast_value if snapshots else None,
                source_observations=tuple(sorted(observations, key=lambda item: item.series_code)),
            )
        )
    if not snapshots:
        raise ValueError(f"no tracking snapshots for {country_code}/{indicator_code}")
    return ModelRun(tuple(snapshots))


def _load_panels(processed_dir: Path) -> dict[str, pd.DataFrame]:
    panels = {
        "monthly": pd.read_parquet(processed_dir / "monthly.parquet"),
        "quarterly": pd.read_parquet(processed_dir / "quarterly.parquet"),
        "daily": pd.read_parquet(processed_dir / "daily.parquet").resample("ME").mean(),
    }
    return panels


def _transformed_series(series: pd.Series, transform: str) -> pd.Series:
    clean = series.dropna().astype(float)
    if transform == "mom_annualized":
        return 1200.0 * clean.div(clean.shift(1)).map(_safe_log)
    if transform == "qoq_annualized":
        return 400.0 * clean.div(clean.shift(1)).map(_safe_log)
    if transform == "level_change":
        return clean.diff()
    raise ValueError(f"unsupported transform {transform}")


def _safe_log(value: float) -> float:
    if value <= 0 or math.isnan(value):
        return float("nan")
    return math.log(value)


def _quarter_label(day: date) -> str:
    quarter = (day.month - 1) // 3 + 1
    return f"{day.year}Q{quarter}"
