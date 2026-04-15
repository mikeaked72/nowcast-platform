"""Publish model outputs into the static country/indicator site contract."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from nowcast.model_input import ModelRun, load_model_run, resolve_model_input_path
from nowcast.schemas import SCHEMA_VERSION


@dataclass(frozen=True)
class CountryPack:
    code: str
    name: str
    default_target: str
    target_code: str
    target_name: str
    units: str
    enabled: bool = True
    indicators: tuple[str, ...] = ("gdp",)


@dataclass(frozen=True)
class IndicatorMeta:
    code: str
    display_name: str
    unit: str
    decimals: int
    default_chart_type: str
    explanatory_text: str
    update_cadence_label: str


INDICATORS = {
    "gdp": IndicatorMeta(
        "gdp",
        "GDP",
        "percent QoQ SAAR",
        2,
        "line",
        "A quarterly growth estimate based on source releases available before the official estimate.",
        "Updated when major activity releases arrive",
    ),
    "inflation": IndicatorMeta(
        "inflation",
        "Inflation",
        "percent annualized",
        2,
        "line",
        "A near-term inflation estimate built from price and cost indicators.",
        "Updated after price releases",
    ),
    "exports": IndicatorMeta(
        "exports",
        "Exports",
        "percent QoQ SAAR",
        2,
        "line",
        "A trade-volume estimate tracking export-related source data.",
        "Updated after trade releases",
    ),
    "imports": IndicatorMeta(
        "imports",
        "Imports",
        "percent QoQ SAAR",
        2,
        "line",
        "A trade-volume estimate tracking import-related source data.",
        "Updated after trade releases",
    ),
}


def load_country_pack(country_code: str, packs_dir: Path | str = "country_packs") -> CountryPack:
    """Load country metadata from a country pack JSON file."""

    path = Path(packs_dir) / country_code / "country.json"
    if not path.exists():
        raise FileNotFoundError(f"missing country pack: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"code", "name", "default_target", "target_code", "target_name", "units", "enabled"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"{path} missing fields {sorted(missing)}")
    if payload["code"] != country_code:
        raise ValueError(f"{path} code must match requested country {country_code}")

    return CountryPack(
        code=payload["code"],
        name=payload["name"],
        default_target=payload["default_target"],
        target_code=payload["target_code"],
        target_name=payload["target_name"],
        units=payload["units"],
        enabled=payload["enabled"],
        indicators=tuple(payload.get("indicators", ["gdp"])),
    )


def validate_country_pack(country_code: str, packs_dir: Path | str = "country_packs") -> None:
    """Validate that a country pack can be loaded."""

    pack = load_country_pack(country_code, packs_dir)
    if not pack.enabled:
        raise ValueError(f"country pack {country_code} is disabled")
    unknown = sorted(set(pack.indicators) - set(INDICATORS))
    if unknown:
        raise ValueError(f"country pack {country_code} has unknown indicators {unknown}")


def publish_sample_country(
    country_code: str,
    publish_dir: Path | str,
    *,
    packs_dir: Path | str = "country_packs",
    input_dir: Path | str = "runs/input",
    input_path: Path | str | None = None,
    as_of: date | None = None,
) -> Path:
    """Publish all configured indicators for one country.

    US GDP uses model input when available. Other initial country/indicator
    combinations use deterministic sample data to exercise the future-facing
    contract without inventing country-specific econometrics.
    """

    pack = load_country_pack(country_code, packs_dir)
    root = Path(publish_dir)
    country_dir = _country_dir(root, country_code)
    country_dir.mkdir(parents=True, exist_ok=True)

    for indicator_code in pack.indicators:
        if country_code == "us" and indicator_code == "gdp":
            try:
                model_input_path = resolve_model_input_path(country_code, input_dir=input_dir, input_path=input_path)
                model_run = load_model_run(model_input_path, as_of=as_of)
                payload = _payload_from_model_run(pack, INDICATORS[indicator_code], model_run)
            except FileNotFoundError:
                payload = _sample_indicator_payload(pack, INDICATORS[indicator_code])
        else:
            payload = _sample_indicator_payload(pack, INDICATORS[indicator_code])
        _write_indicator_payload(country_dir / indicator_code, payload)

    write_countries_json(root, [pack])
    return country_dir


def write_countries_json(publish_dir: Path | str, packs: list[CountryPack]) -> Path:
    """Write the country and indicator index used by the static site."""

    root = Path(publish_dir)
    countries_path = root / "countries.json"
    if len(packs) == 1 and root.name == packs[0].code:
        countries_path = root.parent / "countries.json"

    payload = []
    for pack in sorted(packs, key=lambda item: item.code):
        payload.append(
            {
                "code": pack.code,
                "name": pack.name,
                "default_target": pack.default_target,
                "enabled": pack.enabled,
                "indicators": [
                    {
                        "code": indicator_code,
                        "display_name": INDICATORS[indicator_code].display_name,
                    }
                    for indicator_code in pack.indicators
                ],
            }
        )
    _write_json(countries_path, payload)
    return countries_path


def _payload_from_model_run(pack: CountryPack, meta: IndicatorMeta, model_run: ModelRun) -> dict[str, Any]:
    latest = model_run.latest
    prior_as_of_dates = _snapshot_prior_as_of_dates(model_run)
    return {
        "metadata": _metadata(pack, meta, latest.reference_period),
        "latest": {
            "schema_version": SCHEMA_VERSION,
            "country_code": pack.code,
            "country_name": pack.name,
            "indicator_code": meta.code,
            "indicator_name": meta.display_name,
            "as_of_date": latest.as_of_date.isoformat(),
            "next_update_date": (latest.as_of_date + timedelta(days=14)).isoformat(),
            "reference_period": latest.reference_period,
            "estimate_value": round(latest.nowcast_value, 10),
            "unit": meta.unit,
            "prior_estimate_value": _round_or_none(latest.prior_nowcast_value),
            "delta_vs_prior": _round_or_none(latest.delta_vs_prior),
            "model_status": "ok",
            "model_version": "0.1.0",
            "last_updated_utc": _utc_timestamp(latest.as_of_date),
        },
        "history": [
            {
                "as_of_date": snapshot.as_of_date.isoformat(),
                "reference_period": snapshot.reference_period,
                "estimate_value": round(snapshot.nowcast_value, 10),
                "prior_estimate_value": _csv_number(snapshot.prior_nowcast_value),
                "delta_vs_prior": _csv_number(snapshot.delta_vs_prior),
                "model_status": "ok",
                "model_version": "0.1.0",
            }
            for snapshot in model_run.snapshots
        ],
        "contributions": [
            {
                "as_of_date": snapshot.as_of_date.isoformat(),
                "component_code": observation.series_code,
                "component_name": observation.series_name,
                "reference_period": snapshot.reference_period,
                "contribution": round(observation.impact_on_nowcast, 10),
                "direction": _direction(observation.impact_on_nowcast),
                "category": observation.category,
                "unit": meta.unit,
            }
            for snapshot in model_run.snapshots
            for observation in snapshot.source_observations
        ],
        "release_impacts": [
            {
                "as_of_date": snapshot.as_of_date.isoformat(),
                "release_date": observation.release_date.isoformat(),
                "release_name": observation.series_name,
                "indicator_code": meta.code,
                "indicator_name": meta.display_name,
                "latest_as_of_date": snapshot.as_of_date.isoformat(),
                "prior_as_of_date": prior_as_of_dates.get(snapshot.as_of_date, ""),
                "reference_period": snapshot.reference_period,
                "actual_value": observation.actual_value,
                "expected_value": observation.expected_value,
                "surprise": round(observation.surprise, 10),
                "impact": round(observation.impact_on_nowcast, 10),
                "direction": _direction(observation.impact_on_nowcast),
                "category": observation.category,
                "unit": observation.units,
                "notes": observation.release_status,
                "source": observation.series_code,
                "source_url": "",
            }
            for snapshot in model_run.snapshots
            for observation in snapshot.source_observations
        ],
    }


def _sample_indicator_payload(pack: CountryPack, meta: IndicatorMeta) -> dict[str, Any]:
    base = _sample_base(pack.code, meta.code)
    periods = ["2026Q1", "2026Q2", "2026Q3"]
    dates = [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]
    values = [base - 0.35, base - 0.08, base]
    latest_date = dates[-1]
    history = []
    for index, value in enumerate(values):
        prior = values[index - 1] if index else None
        history.append(
            {
                "as_of_date": dates[index].isoformat(),
                "reference_period": periods[-1],
                "estimate_value": round(value, 10),
                "prior_estimate_value": _csv_number(prior),
                "delta_vs_prior": _csv_number(None if prior is None else value - prior),
                "model_status": "sample",
                "model_version": "0.1.0",
            }
        )

    components = _sample_components(meta.code)
    contributions = [
        {
            "as_of_date": latest_date.isoformat(),
            "component_code": code,
            "component_name": name,
            "reference_period": periods[-1],
            "contribution": contribution,
            "direction": _direction(contribution),
            "category": category,
            "unit": meta.unit,
        }
        for code, name, category, contribution in components
    ]
    release_impacts = [
        {
            "as_of_date": latest_date.isoformat(),
            "release_date": (latest_date - timedelta(days=offset)).isoformat(),
            "release_name": name,
            "indicator_code": meta.code,
            "indicator_name": meta.display_name,
            "latest_as_of_date": latest_date.isoformat(),
            "prior_as_of_date": dates[-2].isoformat(),
            "reference_period": periods[-1],
            "actual_value": round(base + contribution, 10),
            "expected_value": round(base, 10),
            "surprise": contribution,
            "impact": contribution,
            "direction": _direction(contribution),
            "category": category,
            "unit": meta.unit,
            "notes": "sample",
            "source": code,
            "source_url": "",
        }
        for offset, (code, name, category, contribution) in enumerate(components, start=1)
    ]

    return {
        "metadata": _metadata(pack, meta, periods[-1]),
        "latest": {
            "schema_version": SCHEMA_VERSION,
            "country_code": pack.code,
            "country_name": pack.name,
            "indicator_code": meta.code,
            "indicator_name": meta.display_name,
            "as_of_date": latest_date.isoformat(),
            "next_update_date": (latest_date + timedelta(days=14)).isoformat(),
            "reference_period": periods[-1],
            "estimate_value": round(values[-1], 10),
            "unit": meta.unit,
            "prior_estimate_value": round(values[-2], 10),
            "delta_vs_prior": round(values[-1] - values[-2], 10),
            "model_status": "sample",
            "model_version": "0.1.0",
            "last_updated_utc": _utc_timestamp(latest_date),
        },
        "history": history,
        "contributions": contributions,
        "release_impacts": release_impacts,
    }


def _write_indicator_payload(indicator_dir: Path, payload: dict[str, Any]) -> None:
    indicator_dir.mkdir(parents=True, exist_ok=True)
    _write_json(indicator_dir / "latest.json", payload["latest"])
    _write_json(indicator_dir / "metadata.json", payload["metadata"])
    _write_csv(indicator_dir / "history.csv", payload["history"])
    _write_csv(indicator_dir / "contributions.csv", payload["contributions"])
    _write_csv(indicator_dir / "release_impacts.csv", payload["release_impacts"])


def _metadata(pack: CountryPack, meta: IndicatorMeta, default_period: str) -> dict[str, Any]:
    methodology = "Published values are generated by the model pipeline and converted into static files for the site."
    faq = [
        {
            "question": "Is this an official forecast?",
            "answer": "No. It is an automated nowcast intended for monitoring and development use.",
        },
        {
            "question": "When does it update?",
            "answer": meta.update_cadence_label,
        },
    ]
    if pack.code == "us" and meta.code == "gdp":
        methodology = (
            "US GDP uses a transparent bridge model. Public FRED series are converted to quarterly "
            "annualized growth rates, a small ridge-regularized regression is estimated against real GDP growth, "
            "and each run date incorporates source releases available by that date. Pending releases are held at "
            "their training-sample expected values until they arrive."
        )
        faq = [
            {
                "question": "What does new_release mean?",
                "answer": "The release became available on the selected run date and changed the nowcast on that run.",
            },
            {
                "question": "What does carried_forward mean?",
                "answer": "The release was already incorporated on an earlier run date and remains part of the current estimate.",
            },
            {
                "question": "What does pending mean?",
                "answer": "The source has not been released for the selected run date and is held at its expected value.",
            },
            {
                "question": "Is this an official forecast?",
                "answer": "No. It is a transparent automated nowcast scaffold for monitoring and development use.",
            },
        ]
    return {
        "country_code": pack.code,
        "country_name": pack.name,
        "indicator_code": meta.code,
        "display_name": meta.display_name,
        "unit": meta.unit,
        "decimals": meta.decimals,
        "default_chart_type": meta.default_chart_type,
        "explanatory_text": meta.explanatory_text,
        "update_cadence_label": meta.update_cadence_label,
        "default_period": default_period,
        "methodology": methodology,
        "faq": faq,
        "downloads": [
            "latest.json",
            "history.csv",
            "contributions.csv",
            "release_impacts.csv",
            "metadata.json",
        ],
    }


def _country_dir(root: Path, country_code: str) -> Path:
    if root.name == country_code:
        return root
    return root / country_code


def _sample_base(country_code: str, indicator_code: str) -> float:
    values = {
        ("us", "gdp"): 2.1,
        ("us", "inflation"): 2.8,
        ("us", "exports"): 1.2,
        ("us", "imports"): 1.7,
        ("au", "gdp"): 1.6,
        ("au", "inflation"): 3.0,
    }
    return values.get((country_code, indicator_code), 1.0)


def _sample_components(indicator_code: str) -> list[tuple[str, str, str, float]]:
    if indicator_code == "inflation":
        return [
            ("goods", "Goods prices", "prices", 0.12),
            ("services", "Services prices", "prices", 0.18),
            ("energy", "Energy prices", "prices", -0.08),
        ]
    if indicator_code in {"exports", "imports"}:
        return [
            ("goods_trade", "Goods trade", "trade", 0.21),
            ("services_trade", "Services trade", "trade", -0.06),
            ("prices", "Trade prices", "prices", 0.04),
        ]
    return [
        ("consumption", "Consumption", "demand", 0.22),
        ("investment", "Investment", "investment", -0.07),
        ("trade", "Net trade", "trade", 0.11),
    ]


def _utc_timestamp(day: date) -> str:
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC).replace(hour=9).isoformat().replace("+00:00", "Z")


def _snapshot_prior_as_of_dates(model_run: ModelRun) -> dict[date, str]:
    prior_dates: dict[date, str] = {}
    previous: date | None = None
    for snapshot in model_run.snapshots:
        prior_dates[snapshot.as_of_date] = "" if previous is None else previous.isoformat()
        previous = snapshot.as_of_date
    return prior_dates


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 10)


def _csv_number(value: float | None) -> float | str:
    if value is None:
        return ""
    return round(value, 10)


def _direction(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
