"""Publish experimental G10 outputs into the static site contract."""

from __future__ import annotations

import json
from shutil import copyfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.site_adapter import G10NewsImpact, G10NowcastPoint, g10_points_to_model_run
from nowcast.publish import publish_model_run_indicator


MODEL_VERSION = "g10_dfm_experimental_v0.1.0"
DOWNLOADS = (
    "g10_experimental_summary.json",
    "g10_smoke.json",
    "g10_vintage_manifest.json",
    "g10_processed_manifest.json",
)
METHODOLOGY = (
    "This experimental GDP path validates the G10 mixed-frequency DynamicFactorMQ pipeline. "
    "It uses assembled FRED-MD and FRED-QD vintage inputs, processed monthly and quarterly panels, "
    "and a small DFM smoke fit. The current published value is a deterministic development proxy "
    "until the full replay and production DFM target extraction are complete."
)


@dataclass(frozen=True)
class ExperimentalPublishResult:
    indicator_dir: Path
    country_code: str
    indicator_code: str
    vintage_date: str


def publish_experimental_g10_gdp(
    iso: str,
    *,
    vintage_date: date,
    nowcast_value: float | None = None,
    prior_nowcast_value: float | None = None,
    processed_root: Path | str = "data/processed",
    vintage_root: Path | str = "data/vintages",
    artifact_root: Path | str = "artifacts",
    publish_dir: Path | str = "site/data",
    packs_dir: Path | str = "country_packs",
) -> ExperimentalPublishResult:
    """Publish an experimental G10 GDP nowcast as a normal site indicator."""

    country_code = iso.lower()
    method = "provided"
    if nowcast_value is None:
        estimate = estimate_experimental_gdp_proxy(iso, vintage_date=vintage_date, processed_root=processed_root)
        nowcast_value = estimate.nowcast_value
        prior_nowcast_value = estimate.prior_nowcast_value if prior_nowcast_value is None else prior_nowcast_value
        method = estimate.method
    reference_period = _reference_quarter(vintage_date)
    points = []
    if prior_nowcast_value is not None:
        points.append(
            G10NowcastPoint(
                iso=iso.upper(),
                target="gdp_experimental",
                vintage_date=_prior_month_date(vintage_date),
                impact_date=reference_period,
                nowcast=prior_nowcast_value,
            )
        )
    points.append(
        G10NowcastPoint(
            iso=iso.upper(),
            target="gdp_experimental",
            vintage_date=vintage_date,
            impact_date=reference_period,
            nowcast=nowcast_value,
        )
    )
    news = _experimental_news(
        iso.upper(),
        vintage_date=vintage_date,
        processed_root=Path(processed_root),
        total_impact=0.0 if prior_nowcast_value is None else nowcast_value - prior_nowcast_value,
    )
    model_run = g10_points_to_model_run(points, news={vintage_date: news} if news else None)
    indicator_dir = publish_model_run_indicator(
        country_code,
        "gdp_experimental",
        model_run,
        publish_dir,
        packs_dir=packs_dir,
        model_status="warning",
        model_version=MODEL_VERSION,
        methodology=METHODOLOGY,
        extra_downloads=DOWNLOADS,
    )
    _write_provenance_artifacts(
        indicator_dir,
        iso=iso.upper(),
        vintage_date=vintage_date,
        method=method,
        nowcast_value=nowcast_value,
        prior_nowcast_value=prior_nowcast_value,
        processed_root=Path(processed_root),
        vintage_root=Path(vintage_root),
        artifact_root=Path(artifact_root),
    )
    return ExperimentalPublishResult(
        indicator_dir=indicator_dir,
        country_code=country_code,
        indicator_code="gdp_experimental",
        vintage_date=vintage_date.isoformat(),
    )


def _write_provenance_artifacts(
    indicator_dir: Path,
    *,
    iso: str,
    vintage_date: date,
    method: str,
    nowcast_value: float,
    prior_nowcast_value: float | None,
    processed_root: Path,
    vintage_root: Path,
    artifact_root: Path,
) -> None:
    processed_manifest = processed_root / iso / f"panel_{vintage_date.isoformat()}.json"
    vintage_manifest = vintage_root / iso / f"{vintage_date.isoformat()}.json"
    smoke_artifact = artifact_root / iso / f"dfm_smoke_{vintage_date.isoformat()}.json"
    summary = {
        "iso": iso,
        "indicator_code": "gdp_experimental",
        "vintage_date": vintage_date.isoformat(),
        "model_version": MODEL_VERSION,
        "method": method,
        "nowcast_value": nowcast_value,
        "prior_nowcast_value": prior_nowcast_value,
        "processed_manifest": str(processed_manifest),
        "vintage_manifest": str(vintage_manifest),
        "smoke_artifact": str(smoke_artifact),
        "limitations": [
            "development proxy, not a production GDPNow-equivalent estimate",
            "DFM target extraction and historical replay are not complete",
            "tiny smoke runs may not converge and should be interpreted as pipeline checks",
        ],
    }
    (indicator_dir / "g10_experimental_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _copy_if_exists(smoke_artifact, indicator_dir / "g10_smoke.json")
    _copy_if_exists(vintage_manifest, indicator_dir / "g10_vintage_manifest.json")
    _copy_if_exists(processed_manifest, indicator_dir / "g10_processed_manifest.json")


def _experimental_news(
    iso: str,
    *,
    vintage_date: date,
    processed_root: Path,
    total_impact: float,
) -> list[G10NewsImpact]:
    movers = _panel_movers(iso, vintage_date=vintage_date, processed_root=processed_root)
    if not movers:
        return []
    signed_total = sum(float(item["change"]) for item in movers)
    weight_total = signed_total if abs(signed_total) > 1e-12 else sum(abs(float(item["change"])) for item in movers) or 1.0
    return [
        G10NewsImpact(
            series_id=item["series_id"],
            series_name=item["series_name"],
            release_date=vintage_date,
            actual_value=item["actual"],
            expected_value=item["expected"],
            impact=round(total_impact * float(item["change"]) / weight_total, 10),
            category=item["category"],
            status="new_release",
        )
        for item in movers
    ]


def _panel_movers(iso: str, *, vintage_date: date, processed_root: Path) -> list[dict[str, float | str]]:
    root = processed_root / iso
    rows: list[dict[str, float | str]] = []
    rows.extend(_frame_movers(root / f"quarterly_{vintage_date.isoformat()}.parquet", "quarterly"))
    rows.extend(_frame_movers(root / f"monthly_{vintage_date.isoformat()}.parquet", "monthly"))
    return sorted(rows, key=lambda item: abs(float(item["change"])), reverse=True)[:5]


def _frame_movers(path: Path, category: str) -> list[dict[str, float | str]]:
    if not path.exists():
        return []
    frame = pd.read_parquet(path).dropna(how="all")
    if len(frame) < 2:
        return []
    latest = frame.iloc[-1]
    prior = frame.iloc[-2]
    rows = []
    for series_id in frame.columns:
        if pd.isna(latest[series_id]) or pd.isna(prior[series_id]):
            continue
        actual = float(latest[series_id])
        expected = float(prior[series_id])
        rows.append(
            {
                "series_id": str(series_id),
                "series_name": _series_label(str(series_id)),
                "actual": round(actual, 10),
                "expected": round(expected, 10),
                "change": round(actual - expected, 10),
                "category": category,
            }
        )
    return rows


def _series_label(series_id: str) -> str:
    labels = {
        "GDPC1": "Real GDP",
        "GPDIC1": "Gross private domestic investment",
        "INDPRO": "Industrial production",
        "PAYEMS": "Nonfarm payrolls",
        "CPIAUCSL": "Consumer prices",
        "CPILFESL": "Core consumer prices",
        "RPI": "Real personal income",
        "UNRATE": "Unemployment rate",
    }
    return labels.get(series_id, series_id)


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        copyfile(source, destination)


@dataclass(frozen=True)
class ExperimentalEstimate:
    nowcast_value: float
    prior_nowcast_value: float | None
    method: str


def estimate_experimental_gdp_proxy(
    iso: str,
    *,
    vintage_date: date,
    processed_root: Path | str = "data/processed",
) -> ExperimentalEstimate:
    """Derive a deterministic development nowcast from the processed G10 panel."""

    root = Path(processed_root) / iso.upper()
    quarterly_path = root / f"quarterly_{vintage_date.isoformat()}.parquet"
    monthly_path = root / f"monthly_{vintage_date.isoformat()}.parquet"
    if quarterly_path.exists():
        quarterly = pd.read_parquet(quarterly_path)
        for column in ("GDPC1", "GDP", "RGDP"):
            if column in quarterly.columns:
                series = quarterly[column].dropna()
                if not series.empty:
                    latest = _scale_growth(series.iloc[-1])
                    prior = _scale_growth(series.iloc[-2]) if len(series) > 1 else None
                    return ExperimentalEstimate(latest, prior, f"quarterly:{column}")
    if monthly_path.exists():
        monthly = pd.read_parquet(monthly_path).dropna(how="all")
        if not monthly.empty:
            row_scores = monthly.mean(axis=1, skipna=True).dropna()
            if not row_scores.empty:
                latest = _scale_growth(row_scores.iloc[-1])
                prior = _scale_growth(row_scores.iloc[-2]) if len(row_scores) > 1 else None
                return ExperimentalEstimate(latest, prior, "monthly:panel_mean")
    raise FileNotFoundError(f"no processed panel available for {iso.upper()} {vintage_date}")


def _scale_growth(value: float) -> float:
    numeric = float(value)
    if abs(numeric) < 1:
        numeric *= 100
    return round(numeric, 4)


def _reference_quarter(day: date) -> str:
    quarter = ((day.month - 1) // 3) + 1
    return f"{day.year}Q{quarter}"


def _prior_month_date(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, min(day.day, 28))
    return date(day.year, day.month - 1, min(day.day, 28))
