"""Tiny G10 DFM smoke run persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nowcast.g10.dfm import DFMOptions, load_country_panel_and_fit


@dataclass(frozen=True)
class SmokeArtifact:
    path: Path
    iso: str
    vintage_date: str


def run_dfm_smoke(
    iso: str,
    vintage_date: str,
    *,
    processed_root: Path | str = "data/processed",
    artifact_root: Path | str = "artifacts",
    maxiter: int = 2,
) -> SmokeArtifact:
    """Fit a deliberately tiny DFM smoke model and persist run metadata."""

    results = load_country_panel_and_fit(
        iso,
        vintage_date=vintage_date,
        processed_root=processed_root,
        options=DFMOptions(factor_orders=1, maxiter=maxiter, tolerance=1e-3),
        max_monthly_series=8,
        max_quarterly_series=5,
    )
    root = Path(artifact_root) / iso.upper()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"dfm_smoke_{vintage_date}.json"
    monthly_path = Path(processed_root) / iso.upper() / f"monthly_{vintage_date}.parquet"
    quarterly_path = Path(processed_root) / iso.upper() / f"quarterly_{vintage_date}.parquet"
    monthly = pd.read_parquet(monthly_path)
    quarterly = pd.read_parquet(quarterly_path) if quarterly_path.exists() else pd.DataFrame()
    payload = {
        "iso": iso.upper(),
        "vintage_date": vintage_date,
        "created_at_utc": datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "model_class": "statsmodels.tsa.statespace.DynamicFactorMQ",
        "monthly_shape": list(monthly.shape),
        "quarterly_shape": list(quarterly.shape),
        "fitted_monthly_series_cap": 8,
        "fitted_quarterly_series_cap": 5,
        "llf": float(getattr(results, "llf", float("nan"))),
        "converged": bool(getattr(getattr(results, "mle_retvals", {}), "get", lambda *_: False)("converged", False)),
        "maxiter": maxiter,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SmokeArtifact(path=path, iso=iso.upper(), vintage_date=vintage_date)
