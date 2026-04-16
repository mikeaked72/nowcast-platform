"""Export macro data-store coverage for the static site."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nowcast.schemas import SCHEMA_VERSION


COUNTRY_PREFIXES = {
    "au": ("AUS_", "AUD", "AGB", "IRON_ORE"),
    "br": ("BRA_",),
    "de": ("DEU_", "DE_BUND"),
    "us": ("USA_", "DFF", "FEDFUNDS", "CPIAUCSL", "UNRATE", "DGS", "DEXUS"),
}


def export_source_coverage(
    *,
    manifest_path: Path | str = "store/manifest.json",
    publish_dir: Path | str = "site/data",
    countries_path: Path | str | None = None,
) -> Path:
    """Write a compact source-coverage summary into the site data directory."""

    manifest_file = Path(manifest_path)
    root = Path(publish_dir)
    country_index = Path(countries_path) if countries_path else root / "countries.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    countries = json.loads(country_index.read_text(encoding="utf-8")) if country_index.exists() else []
    series = manifest.get("series", {})
    status_counts = Counter(str(item.get("status", "UNKNOWN")) for item in series.values())
    source_counts = Counter(str(item.get("source", "")).split(":", 1)[0] or "unknown" for item in series.values())

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _now_utc_timestamp(),
        "store_last_full_update": manifest.get("last_full_update"),
        "series_count": len(series),
        "status_counts": dict(sorted(status_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "processed": _processed_summary(manifest),
        "countries": [
            _country_summary(country, series)
            for country in countries
            if isinstance(country, dict) and country.get("enabled", False)
        ],
    }
    out_path = root / "source_coverage.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def _country_summary(country: dict[str, Any], series: dict[str, dict[str, Any]]) -> dict[str, Any]:
    code = country["code"]
    prefixes = COUNTRY_PREFIXES.get(code, (code.upper(),))
    matched = {
        local_id: item
        for local_id, item in series.items()
        if any(local_id.startswith(prefix) for prefix in prefixes)
    }
    ok_series = {
        local_id: item
        for local_id, item in matched.items()
        if item.get("status") == "OK"
    }
    top_series = sorted(
        (
            {
                "local_id": local_id,
                "rows": int(item.get("rows") or 0),
                "status": item.get("status", "UNKNOWN"),
                "source": item.get("source", ""),
            }
            for local_id, item in matched.items()
        ),
        key=lambda row: (row["status"] != "OK", -row["rows"], row["local_id"]),
    )[:12]
    return {
        "code": code,
        "name": country["name"],
        "series_count": len(matched),
        "ok_count": len(ok_series),
        "skipped_count": sum(1 for item in matched.values() if item.get("status") == "SKIPPED"),
        "top_series": top_series,
    }


def _processed_summary(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    processed = manifest.get("processed", {})
    return [
        {
            "frequency": frequency,
            "rows": int(item.get("rows") or 0),
            "columns": int(item.get("columns") or 0),
            "start": item.get("start"),
            "end": item.get("end"),
            "path": item.get("path"),
        }
        for frequency, item in sorted(processed.items())
        if isinstance(item, dict)
    ]


def _now_utc_timestamp() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
