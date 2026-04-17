"""Thin wrapper around statsmodels DynamicFactorMQ."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from nowcast.g10.config import load_country_config


@dataclass(frozen=True)
class DFMOptions:
    factor_orders: int = 2
    standardize: bool = True
    idiosyncratic_ar1: bool = True
    maxiter: int = 500
    tolerance: float = 1e-6


def build_factor_mapping(series_blocks: dict[str, list[str]]) -> dict[str, list[str]]:
    """Ensure each series loads on the global factor plus configured blocks."""

    factors: dict[str, list[str]] = {}
    for series_id, blocks in series_blocks.items():
        ordered = ["global", *[block for block in blocks if block != "global"]]
        factors[series_id] = list(dict.fromkeys(ordered))
    return factors


def fit_dynamic_factor_mq(
    monthly: Any,
    *,
    quarterly: Any | None = None,
    factors: dict[str, list[str]] | None = None,
    factor_multiplicities: dict[str, int] | None = None,
    options: DFMOptions | None = None,
) -> Any:
    """Fit the spec-approved mixed-frequency DFM.

    Statsmodels is imported lazily so the rest of the repo can run lightweight
    contract/site tests in environments where the heavy model dependency has
    not yet been installed.
    """

    try:
        from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
    except ImportError as exc:
        raise RuntimeError(
            "statsmodels>=0.14 is required for the G10 DynamicFactorMQ model. "
            "Install project dependencies with `pip install -e .`."
        ) from exc

    resolved = options or DFMOptions()
    model = DynamicFactorMQ(
        monthly,
        endog_quarterly=quarterly,
        factors=factors,
        factor_multiplicities=factor_multiplicities,
        factor_orders=resolved.factor_orders,
        idiosyncratic_ar1=resolved.idiosyncratic_ar1,
        standardize=resolved.standardize,
    )
    return model.fit(maxiter=resolved.maxiter, tolerance=resolved.tolerance, disp=False)


def load_panel_and_fit(
    *,
    monthly_path: str,
    quarterly_path: str | None = None,
    series_blocks: dict[str, list[str]] | None = None,
    options: DFMOptions | None = None,
) -> Any:
    """Load processed panel files and fit the approved DFM wrapper."""

    monthly = _monthly_index(pd.read_parquet(monthly_path))
    quarterly = _quarterly_index(pd.read_parquet(quarterly_path)) if quarterly_path else None
    factors = build_factor_mapping(series_blocks or {column: [] for column in monthly.columns})
    return fit_dynamic_factor_mq(monthly, quarterly=quarterly, factors=factors, options=options)


def series_blocks_from_country_config(config: dict[str, Any], available_series: list[str]) -> dict[str, list[str]]:
    configured = {}
    for item in [*config.get("panel", []), *config.get("panel_quarterly", [])]:
        if isinstance(item, dict) and item.get("series") in available_series:
            configured[str(item["series"])] = [str(block) for block in item.get("blocks", [])]
    return {series: configured.get(series, []) for series in available_series}


def load_country_panel_and_fit(
    iso: str,
    *,
    vintage_date: str,
    processed_root: Path | str = "data/processed",
    config_dir: Path | str = "config/countries",
    options: DFMOptions | None = None,
    max_monthly_series: int | None = None,
    max_quarterly_series: int | None = None,
) -> Any:
    root = Path(processed_root) / iso.upper()
    monthly_path = root / f"monthly_{vintage_date}.parquet"
    quarterly_path = root / f"quarterly_{vintage_date}.parquet"
    monthly = _monthly_index(pd.read_parquet(monthly_path))
    quarterly = _quarterly_index(pd.read_parquet(quarterly_path)) if quarterly_path.exists() else None
    if max_monthly_series is not None:
        monthly = monthly.iloc[:, :max_monthly_series]
    if quarterly is not None and max_quarterly_series is not None:
        quarterly = quarterly.iloc[:, :max_quarterly_series]
    config = load_country_config(iso, config_dir)
    series_blocks = series_blocks_from_country_config(config, list(monthly.columns) + ([] if quarterly is None else list(quarterly.columns)))
    return fit_dynamic_factor_mq(
        monthly,
        quarterly=quarterly if quarterly is not None and not quarterly.empty else None,
        factors=build_factor_mapping(series_blocks),
        options=options,
    )


def statsmodels_available() -> bool:
    try:
        from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ  # noqa: F401
    except ImportError:
        return False
    return True


def _monthly_index(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output.index = pd.to_datetime(output.index).to_period("M")
    return output.sort_index()


def _quarterly_index(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output.index = pd.to_datetime(output.index).to_period("Q")
    return output.sort_index()
