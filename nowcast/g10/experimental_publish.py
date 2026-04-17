"""Publish experimental G10 outputs into the static site contract."""

from __future__ import annotations

import json
from shutil import copyfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.site_adapter import G10NewsImpact, G10NowcastPoint, g10_points_to_model_run
from nowcast.publish import load_existing_site_packs, publish_model_run_indicator, write_countries_json


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


@dataclass(frozen=True)
class ProxyWeights:
    quarterly: float = 0.7
    monthly: float = 0.3


def publish_experimental_g10_gdp(
    iso: str,
    *,
    vintage_date: date,
    nowcast_value: float | None = None,
    prior_nowcast_value: float | None = None,
    processed_root: Path | str = "data/processed",
    vintage_root: Path | str = "data/vintages",
    artifact_root: Path | str = "artifacts",
    proxy_weights: ProxyWeights | None = None,
    publish_dir: Path | str = "site/data",
    packs_dir: Path | str = "country_packs",
) -> ExperimentalPublishResult:
    """Publish an experimental G10 GDP nowcast as a normal site indicator."""

    country_code = iso.lower()
    method = "provided"
    proxy_details: dict[str, object] = {}
    if nowcast_value is None:
        estimate = estimate_experimental_gdp_proxy(
            iso,
            vintage_date=vintage_date,
            processed_root=processed_root,
            weights=proxy_weights,
        )
        nowcast_value = estimate.nowcast_value
        prior_nowcast_value = estimate.prior_nowcast_value if prior_nowcast_value is None else prior_nowcast_value
        method = estimate.method
        proxy_details = estimate.details or {}
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
    total_impact = 0.0 if prior_nowcast_value is None else nowcast_value - prior_nowcast_value
    news = _experimental_news(
        iso.upper(),
        vintage_date=vintage_date,
        processed_root=Path(processed_root),
        total_impact=total_impact,
    )
    news.extend(_carried_forward_impacts(vintage_date=vintage_date, prior_nowcast_value=prior_nowcast_value))
    news.extend(_pending_impacts(iso.upper(), vintage_date=vintage_date, vintage_root=Path(vintage_root)))
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
        proxy_details=proxy_details,
        total_impact=total_impact,
        nowcast_value=nowcast_value,
        prior_nowcast_value=prior_nowcast_value,
        processed_root=Path(processed_root),
        vintage_root=Path(vintage_root),
        artifact_root=Path(artifact_root),
    )
    write_countries_json(Path(publish_dir), load_existing_site_packs(publish_dir, packs_dir))
    return ExperimentalPublishResult(
        indicator_dir=indicator_dir,
        country_code=country_code,
        indicator_code="gdp_experimental",
        vintage_date=vintage_date.isoformat(),
    )


def publish_experimental_g10_gdp_replay(
    iso: str,
    *,
    vintage_dates: list[date],
    processed_root: Path | str = "data/processed",
    vintage_root: Path | str = "data/vintages",
    artifact_root: Path | str = "artifacts",
    proxy_weights: ProxyWeights | None = None,
    publish_dir: Path | str = "site/data",
    packs_dir: Path | str = "country_packs",
) -> ExperimentalPublishResult:
    """Publish an experimental multi-vintage G10 GDP replay."""

    ordered_dates = sorted(dict.fromkeys(vintage_dates))
    if not ordered_dates:
        raise ValueError("at least one vintage date is required")
    estimates = [
        estimate_experimental_gdp_proxy(
            iso,
            vintage_date=vintage,
            processed_root=processed_root,
            weights=proxy_weights,
        )
        for vintage in ordered_dates
    ]
    points = [
        G10NowcastPoint(
            iso=iso.upper(),
            target="gdp_experimental",
            vintage_date=vintage,
            impact_date=_reference_quarter(vintage),
            nowcast=estimate.nowcast_value,
        )
        for vintage, estimate in zip(ordered_dates, estimates, strict=True)
    ]
    news: dict[date, list[G10NewsImpact]] = {}
    previous_value: float | None = None
    for vintage, estimate in zip(ordered_dates, estimates, strict=True):
        total_impact = 0.0 if previous_value is None else estimate.nowcast_value - previous_value
        impacts = _experimental_news(
            iso.upper(),
            vintage_date=vintage,
            processed_root=Path(processed_root),
            total_impact=total_impact,
        )
        impacts.extend(_carried_forward_impacts(vintage_date=vintage, prior_nowcast_value=previous_value))
        impacts.extend(_pending_impacts(iso.upper(), vintage_date=vintage, vintage_root=Path(vintage_root)))
        if impacts:
            news[vintage] = impacts
        previous_value = estimate.nowcast_value
    model_run = g10_points_to_model_run(points, news=news)
    country_code = iso.lower()
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
    latest_date = ordered_dates[-1]
    latest_estimate = estimates[-1]
    prior_estimate = estimates[-2].nowcast_value if len(estimates) > 1 else latest_estimate.prior_nowcast_value
    _write_provenance_artifacts(
        indicator_dir,
        iso=iso.upper(),
        vintage_date=latest_date,
        method=f"replay:{latest_estimate.method}",
        proxy_details=latest_estimate.details or {},
        total_impact=0.0 if prior_estimate is None else latest_estimate.nowcast_value - prior_estimate,
        nowcast_value=latest_estimate.nowcast_value,
        prior_nowcast_value=prior_estimate,
        processed_root=Path(processed_root),
        vintage_root=Path(vintage_root),
        artifact_root=Path(artifact_root),
    )
    _append_replay_summary(indicator_dir, ordered_dates, estimates)
    write_countries_json(Path(publish_dir), load_existing_site_packs(publish_dir, packs_dir))
    return ExperimentalPublishResult(
        indicator_dir=indicator_dir,
        country_code=country_code,
        indicator_code="gdp_experimental",
        vintage_date=latest_date.isoformat(),
    )


def _write_provenance_artifacts(
    indicator_dir: Path,
    *,
    iso: str,
    vintage_date: date,
    method: str,
    proxy_details: dict[str, object],
    total_impact: float,
    nowcast_value: float,
    prior_nowcast_value: float | None,
    processed_root: Path,
    vintage_root: Path,
    artifact_root: Path,
) -> None:
    processed_manifest = processed_root / iso / f"panel_{vintage_date.isoformat()}.json"
    vintage_manifest = vintage_root / iso / f"{vintage_date.isoformat()}.json"
    smoke_artifact = artifact_root / iso / f"dfm_smoke_{vintage_date.isoformat()}.json"
    artifact_sources = {
        "g10_smoke.json": smoke_artifact,
        "g10_vintage_manifest.json": vintage_manifest,
        "g10_processed_manifest.json": processed_manifest,
    }
    smoke_payload = _read_optional_json(smoke_artifact)
    summary = {
        "iso": iso,
        "indicator_code": "gdp_experimental",
        "vintage_date": vintage_date.isoformat(),
        "model_version": MODEL_VERSION,
        "method": method,
        "proxy_details": proxy_details,
        "nowcast_value": nowcast_value,
        "prior_nowcast_value": prior_nowcast_value,
        "impact_by_frequency": _impact_by_frequency(
            iso,
            vintage_date=vintage_date,
            processed_root=processed_root,
            total_impact=total_impact,
        ),
        "processed_manifest": "g10_processed_manifest.json" if processed_manifest.exists() else None,
        "vintage_manifest": "g10_vintage_manifest.json" if vintage_manifest.exists() else None,
        "smoke_artifact": "g10_smoke.json" if smoke_artifact.exists() else None,
        "copied_artifacts": sorted(name for name, source in artifact_sources.items() if source.exists()),
        "missing_artifacts": sorted(name for name, source in artifact_sources.items() if not source.exists()),
        "smoke_converged": smoke_payload.get("converged") if smoke_payload else None,
        "smoke_llf": smoke_payload.get("llf") if smoke_payload else None,
        "smoke_maxiter": smoke_payload.get("maxiter") if smoke_payload else None,
        "source_availability": _source_availability(iso, vintage_date=vintage_date, processed_root=processed_root),
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
    for filename, source in artifact_sources.items():
        _copy_if_exists(source, indicator_dir / filename)


def _append_replay_summary(indicator_dir: Path, vintage_dates: list[date], estimates: list[ExperimentalEstimate]) -> None:
    path = indicator_dir / "g10_experimental_summary.json"
    payload = _read_optional_json(path) or {}
    payload["replay_vintages"] = [item.isoformat() for item in vintage_dates]
    payload["replay_estimates"] = [
        {
            "vintage_date": vintage.isoformat(),
            "nowcast_value": estimate.nowcast_value,
            "prior_nowcast_value": estimate.prior_nowcast_value,
            "method": estimate.method,
        }
        for vintage, estimate in zip(vintage_dates, estimates, strict=True)
    ]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _pending_impacts(iso: str, *, vintage_date: date, vintage_root: Path) -> list[G10NewsImpact]:
    try:
        from nowcast.g10.coverage import check_config_coverage

        coverage = check_config_coverage(iso, vintage_date, vintage_root=vintage_root)
    except (FileNotFoundError, KeyError, ValueError):
        return []
    missing = [*coverage.missing_targets, *coverage.missing_panel_series]
    return [
        G10NewsImpact(
            series_id=series_id,
            series_name=_series_label(series_id),
            release_date=vintage_date,
            actual_value=0.0,
            expected_value=0.0,
            impact=0.0,
            category="missing input",
            status="pending",
        )
        for series_id in sorted(dict.fromkeys(missing))[:8]
    ]


def _carried_forward_impacts(*, vintage_date: date, prior_nowcast_value: float | None) -> list[G10NewsImpact]:
    if prior_nowcast_value is None:
        return []
    return [
        G10NewsImpact(
            series_id="prior_g10_proxy",
            series_name="Prior G10 experimental proxy",
            release_date=_prior_month_date(vintage_date),
            actual_value=prior_nowcast_value,
            expected_value=prior_nowcast_value,
            impact=0.0,
            category="prior estimate",
            status="carried_forward",
        )
    ]


def _panel_movers(iso: str, *, vintage_date: date, processed_root: Path) -> list[dict[str, float | str]]:
    root = processed_root / iso
    rows: list[dict[str, float | str]] = []
    rows.extend(_frame_movers(root / f"quarterly_{vintage_date.isoformat()}.parquet", "quarterly"))
    rows.extend(_frame_movers(root / f"monthly_{vintage_date.isoformat()}.parquet", "monthly"))
    return sorted(rows, key=lambda item: abs(float(item["change"])), reverse=True)[:5]


def _source_availability(iso: str, *, vintage_date: date, processed_root: Path) -> list[dict[str, float | str]]:
    return [
        {
            "series_id": str(item["series_id"]),
            "series_name": str(item["series_name"]),
            "category": str(item["category"]),
            "frequency": str(item["frequency"]),
            "status": "available",
            "actual": float(item["actual"]),
            "expected": float(item["expected"]),
        }
        for item in _panel_movers(iso, vintage_date=vintage_date, processed_root=processed_root)
    ]


def _impact_by_frequency(
    iso: str,
    *,
    vintage_date: date,
    processed_root: Path,
    total_impact: float,
) -> list[dict[str, float | str]]:
    movers = _panel_movers(iso, vintage_date=vintage_date, processed_root=processed_root)
    signed_total = sum(float(item["change"]) for item in movers)
    weight_total = signed_total if abs(signed_total) > 1e-12 else sum(abs(float(item["change"])) for item in movers) or 1.0
    grouped: dict[str, float] = {}
    for item in movers:
        frequency = str(item["frequency"])
        grouped[frequency] = grouped.get(frequency, 0.0) + (total_impact * float(item["change"]) / weight_total)
    return [
        {"frequency": frequency, "impact": round(impact, 10)}
        for frequency, impact in sorted(grouped.items())
    ]


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
                "category": _series_category(str(series_id), category),
                "frequency": category,
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
        "DGS10": "10-year Treasury yield",
        "TB3MS": "3-month Treasury bill",
        "BAA": "BAA corporate bond yield",
        "S&P 500": "S&P 500",
        "EXUSUKx": "US dollar / British pound exchange rate",
        "EXJPUSx": "Yen / US dollar exchange rate",
        "HOUST": "Housing starts",
        "UMCSENTx": "Consumer sentiment",
    }
    return labels.get(series_id, series_id)


def _series_category(series_id: str, fallback: str) -> str:
    categories = {
        "GDPC1": "output",
        "GPDIC1": "investment",
        "CPATAX": "profits",
        "IMPGS": "imports",
        "EXPGS": "exports",
        "INDPRO": "production",
        "IPMANSICS": "production",
        "CUMFNS": "production",
        "PAYEMS": "labour market",
        "AWHMAN": "labour market",
        "ICSA": "labour market",
        "CES0500000003": "wages",
        "CPIAUCSL": "prices",
        "CPILFESL": "prices",
        "PPIACO": "prices",
        "RPI": "income",
        "UNRATE": "labour market",
        "DGS10": "financial",
        "TB3MS": "financial",
        "BAA": "financial",
        "S&P 500": "financial",
        "EXUSUKx": "external",
        "EXJPUSx": "external",
        "HOUST": "housing",
        "UMCSENTx": "sentiment",
    }
    return categories.get(series_id, fallback)


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        copyfile(source, destination)


def _read_optional_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


@dataclass(frozen=True)
class ExperimentalEstimate:
    nowcast_value: float
    prior_nowcast_value: float | None
    method: str
    details: dict[str, object] | None = None


def estimate_experimental_gdp_proxy(
    iso: str,
    *,
    vintage_date: date,
    processed_root: Path | str = "data/processed",
    weights: ProxyWeights | None = None,
) -> ExperimentalEstimate:
    """Derive a deterministic development nowcast from the processed G10 panel."""

    resolved_weights = weights or ProxyWeights()
    root = Path(processed_root) / iso.upper()
    quarterly_path = root / f"quarterly_{vintage_date.isoformat()}.parquet"
    monthly_path = root / f"monthly_{vintage_date.isoformat()}.parquet"
    if quarterly_path.exists():
        quarterly = pd.read_parquet(quarterly_path)
        for column in ("GDPC1", "GDP", "RGDP"):
            if column in quarterly.columns:
                series = quarterly[column].dropna()
                if not series.empty:
                    quarterly_latest = _scale_growth(series.iloc[-1])
                    quarterly_prior = _scale_growth(series.iloc[-2]) if len(series) > 1 else None
                    monthly = _monthly_activity_estimate(monthly_path)
                    if monthly is not None:
                        latest = _blend_scores(quarterly_latest, monthly.nowcast_value, resolved_weights)
                        prior = (
                            _blend_scores(quarterly_prior, monthly.prior_nowcast_value, resolved_weights)
                            if quarterly_prior is not None and monthly.prior_nowcast_value is not None
                            else quarterly_prior
                        )
                        return ExperimentalEstimate(
                            latest,
                            prior,
                            f"blend:{column}+monthly_activity",
                            {
                                "quarterly_series": column,
                                "quarterly_score": quarterly_latest,
                                "quarterly_prior_score": quarterly_prior,
                                "monthly_method": monthly.method,
                                "monthly_score": monthly.nowcast_value,
                                "monthly_prior_score": monthly.prior_nowcast_value,
                                "weights": {
                                    "quarterly": resolved_weights.quarterly,
                                    "monthly": resolved_weights.monthly,
                                },
                            },
                        )
                    return ExperimentalEstimate(
                        quarterly_latest,
                        quarterly_prior,
                        f"quarterly:{column}",
                        {"quarterly_series": column, "quarterly_score": quarterly_latest, "quarterly_prior_score": quarterly_prior},
                    )
    if monthly_path.exists():
        monthly = _monthly_activity_estimate(monthly_path)
        if monthly is not None:
            return monthly
    raise FileNotFoundError(f"no processed panel available for {iso.upper()} {vintage_date}")


def _scale_growth(value: float) -> float:
    numeric = float(value)
    if abs(numeric) < 1:
        numeric *= 100
    return round(numeric, 4)


def _monthly_activity_estimate(monthly_path: Path) -> ExperimentalEstimate | None:
    if not monthly_path.exists():
        return None
    monthly = pd.read_parquet(monthly_path).dropna(how="all")
    if monthly.empty:
        return None
    activity_columns = [column for column in ("INDPRO", "PAYEMS", "RPI") if column in monthly.columns]
    if not activity_columns:
        activity_columns = list(monthly.columns)
    row_scores = monthly[activity_columns].mean(axis=1, skipna=True).dropna()
    if row_scores.empty:
        return None
    latest = _scale_growth(row_scores.iloc[-1])
    prior = _scale_growth(row_scores.iloc[-2]) if len(row_scores) > 1 else None
    return ExperimentalEstimate(
        latest,
        prior,
        "monthly:activity_mean",
        {"monthly_columns": activity_columns, "monthly_score": latest, "monthly_prior_score": prior},
    )


def _blend_scores(quarterly_score: float, monthly_score: float, weights: ProxyWeights) -> float:
    total = weights.quarterly + weights.monthly
    if total == 0:
        raise ValueError("proxy weights must not sum to zero")
    quarterly_weight = weights.quarterly / total
    monthly_weight = weights.monthly / total
    return round((quarterly_weight * quarterly_score) + (monthly_weight * monthly_score), 4)


def _reference_quarter(day: date) -> str:
    quarter = ((day.month - 1) // 3) + 1
    return f"{day.year}Q{quarter}"


def _prior_month_date(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, min(day.day, 28))
    return date(day.year, day.month - 1, min(day.day, 28))
