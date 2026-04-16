"""Validation helpers for the published site payload contract."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = 1
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ALLOWED_MODEL_STATUSES = {"ok", "sample", "warning", "error", "stale"}
ALLOWED_UNITS = {
    "index",
    "percent",
    "percent annualized",
    "percent QoQ SAAR",
    "percentage points",
}
COUNTRIES_REQUIRED_FIELDS = {"code", "name", "default_target", "enabled", "indicators"}
MANIFEST_REQUIRED_FIELDS = {
    "schema_version",
    "generated_at_utc",
    "country_count",
    "indicator_count",
    "artifact_count",
    "countries",
}
INDICATOR_REQUIRED_FILES = {
    "latest.json",
    "history.csv",
    "contributions.csv",
    "release_impacts.csv",
    "metadata.json",
}
LATEST_REQUIRED_FIELDS = {
    "schema_version",
    "country_code",
    "country_name",
    "indicator_code",
    "indicator_name",
    "as_of_date",
    "next_update_date",
    "reference_period",
    "estimate_value",
    "unit",
    "prior_estimate_value",
    "delta_vs_prior",
    "model_status",
    "model_version",
    "last_updated_utc",
}
METADATA_REQUIRED_FIELDS = {
    "country_code",
    "country_name",
    "indicator_code",
    "display_name",
    "unit",
    "decimals",
    "default_chart_type",
    "explanatory_text",
    "update_cadence_label",
}
HISTORY_REQUIRED_COLUMNS = {
    "as_of_date",
    "reference_period",
    "estimate_value",
    "prior_estimate_value",
    "delta_vs_prior",
    "model_status",
    "model_version",
}
CONTRIBUTIONS_REQUIRED_COLUMNS = {
    "as_of_date",
    "component_code",
    "component_name",
    "reference_period",
    "contribution",
    "direction",
    "category",
    "unit",
}
RELEASE_IMPACTS_REQUIRED_COLUMNS = {
    "latest_as_of_date",
    "prior_as_of_date",
    "as_of_date",
    "release_date",
    "release_name",
    "indicator_code",
    "indicator_name",
    "reference_period",
    "actual_value",
    "expected_value",
    "surprise",
    "impact",
    "direction",
    "category",
    "unit",
    "notes",
    "source",
    "source_url",
}
ALLOWED_DIRECTIONS = {"positive", "negative", "neutral"}


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_publish_dir(
    publish_dir: Path | str,
    *,
    countries: list[str] | None = None,
) -> ValidationResult:
    """Validate the static country/indicator publish contract."""

    root = Path(publish_dir)
    errors: list[str] = []
    countries_path = _countries_path(root)
    manifest_path = countries_path.parent / "manifest.json"
    country_entries = _validate_countries_json(countries_path, errors, countries)
    _validate_manifest_json(manifest_path, errors, country_entries)

    for entry in country_entries:
        country_code = entry["code"]
        country_dir = _country_dir(root, country_code)
        indicators = [indicator["code"] for indicator in entry["indicators"]]
        for indicator_code in indicators:
            _validate_indicator_payload(country_dir / indicator_code, country_code, indicator_code, errors)

    return ValidationResult(tuple(errors))


def _countries_path(root: Path) -> Path:
    if (root / "countries.json").exists():
        return root / "countries.json"
    return root.parent / "countries.json"


def _country_dir(root: Path, country_code: str) -> Path:
    if root.name == country_code:
        return root
    return root / country_code


def _validate_countries_json(
    countries_path: Path,
    errors: list[str],
    requested_countries: list[str] | None,
) -> list[dict[str, Any]]:
    if not countries_path.exists():
        errors.append(f"missing countries.json at {countries_path}")
        return []

    try:
        countries_payload = json.loads(countries_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{countries_path}: invalid JSON: {exc}")
        return []

    if not isinstance(countries_payload, list):
        errors.append(f"{countries_path}: expected a list")
        return []

    entries: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for index, entry in enumerate(countries_payload):
        if not isinstance(entry, dict):
            errors.append(f"{countries_path}: entry {index} must be an object")
            continue

        missing = COUNTRIES_REQUIRED_FIELDS - set(entry)
        if missing:
            errors.append(f"{countries_path}: entry {index} missing fields {sorted(missing)}")
            continue

        code = entry["code"]
        if not isinstance(code, str) or not re.fullmatch(r"[a-z]{2}", code):
            errors.append(f"{countries_path}: entry {index} code must be a lowercase ISO alpha-2 code")
            continue
        if code in seen_codes:
            errors.append(f"{countries_path}: duplicate country code {code}")
        seen_codes.add(code)

        if requested_countries and code not in requested_countries:
            continue
        if not isinstance(entry["enabled"], bool):
            errors.append(f"{countries_path}: {code} enabled must be boolean")
        if not isinstance(entry["indicators"], list) or not entry["indicators"]:
            errors.append(f"{countries_path}: {code} indicators must be a non-empty list")
            continue
        for indicator in entry["indicators"]:
            if not isinstance(indicator, dict) or not isinstance(indicator.get("code"), str):
                errors.append(f"{countries_path}: {code} has invalid indicator entry")
        if entry["enabled"]:
            entries.append(entry)

    if requested_countries:
        missing_requested = sorted(set(requested_countries) - seen_codes)
        if missing_requested:
            errors.append(f"{countries_path}: missing requested countries {missing_requested}")

    return entries


def _validate_manifest_json(
    manifest_path: Path,
    errors: list[str],
    country_entries: list[dict[str, Any]],
) -> None:
    if not manifest_path.exists():
        errors.append(f"missing manifest.json at {manifest_path}")
        return
    payload = _read_json_object(manifest_path, errors)
    if payload is None:
        return
    missing = MANIFEST_REQUIRED_FIELDS - set(payload)
    if missing:
        errors.append(f"{manifest_path}: missing fields {sorted(missing)}")
    _validate_schema_version(manifest_path, payload.get("schema_version"), errors)
    _validate_iso_datetime(manifest_path, "generated_at_utc", payload.get("generated_at_utc"), errors)
    for field in ("country_count", "indicator_count", "artifact_count"):
        _validate_number(manifest_path, field, payload.get(field), errors)
    countries = payload.get("countries")
    if not isinstance(countries, list):
        errors.append(f"{manifest_path}: countries must be a list")
        return
    country_codes = {entry["code"] for entry in country_entries}
    manifest_codes = {entry.get("code") for entry in countries if isinstance(entry, dict)}
    missing_codes = sorted(country_codes - manifest_codes)
    if missing_codes:
        errors.append(f"{manifest_path}: missing enabled countries {missing_codes}")


def _validate_indicator_payload(
    indicator_dir: Path,
    country_code: str,
    indicator_code: str,
    errors: list[str],
) -> None:
    for filename in sorted(INDICATOR_REQUIRED_FILES):
        path = indicator_dir / filename
        if not path.exists():
            errors.append(f"missing required file {path}")

    if (indicator_dir / "latest.json").exists():
        _validate_latest(indicator_dir / "latest.json", country_code, indicator_code, errors)
    if (indicator_dir / "metadata.json").exists():
        _validate_metadata(indicator_dir / "metadata.json", country_code, indicator_code, errors)
    if (indicator_dir / "history.csv").exists():
        _validate_history(indicator_dir / "history.csv", errors)
    if (indicator_dir / "contributions.csv").exists():
        _validate_contributions(indicator_dir / "contributions.csv", errors)
    if (indicator_dir / "release_impacts.csv").exists():
        _validate_release_impacts(indicator_dir / "release_impacts.csv", indicator_code, errors)


def _validate_latest(path: Path, country_code: str, indicator_code: str, errors: list[str]) -> None:
    payload = _read_json_object(path, errors)
    if payload is None:
        return
    missing = LATEST_REQUIRED_FIELDS - set(payload)
    if missing:
        errors.append(f"{path}: missing fields {sorted(missing)}")
    if payload.get("country_code") != country_code:
        errors.append(f"{path}: country_code must match folder name {country_code}")
    if payload.get("indicator_code") != indicator_code:
        errors.append(f"{path}: indicator_code must match folder name {indicator_code}")
    _validate_schema_version(path, payload.get("schema_version"), errors)
    _validate_iso_date(path, "as_of_date", payload.get("as_of_date"), errors)
    _validate_iso_date(path, "next_update_date", payload.get("next_update_date"), errors)
    _validate_iso_datetime(path, "last_updated_utc", payload.get("last_updated_utc"), errors)
    _validate_model_status(path, "model_status", payload.get("model_status"), errors)
    _validate_unit(path, "unit", payload.get("unit"), errors)
    _validate_number(path, "estimate_value", payload.get("estimate_value"), errors)
    _validate_nullable_number(path, "prior_estimate_value", payload.get("prior_estimate_value"), errors)
    _validate_nullable_number(path, "delta_vs_prior", payload.get("delta_vs_prior"), errors)


def _validate_metadata(path: Path, country_code: str, indicator_code: str, errors: list[str]) -> None:
    payload = _read_json_object(path, errors)
    if payload is None:
        return
    missing = METADATA_REQUIRED_FIELDS - set(payload)
    if missing:
        errors.append(f"{path}: missing fields {sorted(missing)}")
    if payload.get("country_code") != country_code:
        errors.append(f"{path}: country_code must match folder name {country_code}")
    if payload.get("indicator_code") != indicator_code:
        errors.append(f"{path}: indicator_code must match folder name {indicator_code}")
    _validate_number(path, "decimals", payload.get("decimals"), errors)
    _validate_unit(path, "unit", payload.get("unit"), errors)


def _validate_history(path: Path, errors: list[str]) -> None:
    rows = _read_csv(path, errors)
    if rows is None:
        return
    fieldnames, records = rows
    _require_columns(path, fieldnames, HISTORY_REQUIRED_COLUMNS, errors)
    if not records:
        errors.append(f"{path}: history must contain at least one row")
    dates: list[date] = []
    for index, row in enumerate(records, start=2):
        parsed_date = _parse_iso_date(row.get("as_of_date"))
        if parsed_date is None:
            errors.append(f"{path}: row {index} has invalid as_of_date")
        else:
            dates.append(parsed_date)
        _validate_number(path, f"row {index} estimate_value", row.get("estimate_value"), errors)
        _validate_csv_nullable_number(path, f"row {index} prior_estimate_value", row.get("prior_estimate_value"), errors)
        _validate_csv_nullable_number(path, f"row {index} delta_vs_prior", row.get("delta_vs_prior"), errors)
        _validate_model_status(path, f"row {index} model_status", row.get("model_status"), errors)
    if dates != sorted(dates):
        errors.append(f"{path}: rows must be ordered ascending by as_of_date")


def _validate_contributions(path: Path, errors: list[str]) -> None:
    rows = _read_csv(path, errors)
    if rows is None:
        return
    fieldnames, records = rows
    _require_columns(path, fieldnames, CONTRIBUTIONS_REQUIRED_COLUMNS, errors)
    for index, row in enumerate(records, start=2):
        if _parse_iso_date(row.get("as_of_date")) is None:
            errors.append(f"{path}: row {index} has invalid as_of_date")
        _validate_number(path, f"row {index} contribution", row.get("contribution"), errors)
        _validate_direction(path, index, row.get("direction"), errors)
        _validate_unit(path, f"row {index} unit", row.get("unit"), errors)


def _validate_release_impacts(path: Path, indicator_code: str, errors: list[str]) -> None:
    rows = _read_csv(path, errors)
    if rows is None:
        return
    fieldnames, records = rows
    _require_columns(path, fieldnames, RELEASE_IMPACTS_REQUIRED_COLUMNS, errors)
    for index, row in enumerate(records, start=2):
        if _parse_iso_date(row.get("as_of_date")) is None:
            errors.append(f"{path}: row {index} has invalid as_of_date")
        if _parse_iso_date(row.get("latest_as_of_date")) is None:
            errors.append(f"{path}: row {index} has invalid latest_as_of_date")
        if row.get("prior_as_of_date") and _parse_iso_date(row.get("prior_as_of_date")) is None:
            errors.append(f"{path}: row {index} has invalid prior_as_of_date")
        if row.get("indicator_code") != indicator_code:
            errors.append(f"{path}: row {index} indicator_code must be {indicator_code}")
        if _parse_iso_date(row.get("release_date")) is None:
            errors.append(f"{path}: row {index} has invalid release_date")
        for field in ("actual_value", "expected_value", "surprise", "impact"):
            _validate_number(path, f"row {index} {field}", row.get(field), errors)
        _validate_direction(path, index, row.get("direction"), errors)
        _validate_unit(path, f"row {index} unit", row.get("unit"), errors)


def _read_json_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path}: expected an object")
        return None
    return payload


def _read_csv(path: Path, errors: list[str]) -> tuple[list[str], list[dict[str, str]]] | None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            errors.append(f"{path}: missing header row")
            return None
        return reader.fieldnames, list(reader)


def _require_columns(path: Path, fieldnames: list[str], required: set[str], errors: list[str]) -> None:
    missing = required - set(fieldnames)
    if missing:
        errors.append(f"{path}: missing columns {sorted(missing)}")


def _validate_direction(path: Path, index: int, value: str | None, errors: list[str]) -> None:
    if value not in ALLOWED_DIRECTIONS:
        errors.append(f"{path}: row {index} direction must be one of {sorted(ALLOWED_DIRECTIONS)}")


def _validate_schema_version(path: Path, value: Any, errors: list[str]) -> None:
    if value != SCHEMA_VERSION:
        errors.append(f"{path}: schema_version must be {SCHEMA_VERSION}")


def _validate_model_status(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if value not in ALLOWED_MODEL_STATUSES:
        errors.append(f"{path}: {field} must be one of {sorted(ALLOWED_MODEL_STATUSES)}")


def _validate_unit(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if value not in ALLOWED_UNITS:
        errors.append(f"{path}: {field} must be one of {sorted(ALLOWED_UNITS)}")


def _validate_iso_date(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, str) or _parse_iso_date(value) is None:
        errors.append(f"{path}: {field} must be a YYYY-MM-DD date string")


def _validate_iso_datetime(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_RE.fullmatch(value):
        errors.append(f"{path}: {field} must be a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: {field} must be a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form")


def _validate_nullable_number(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if value is not None:
        _validate_number(path, field, value, errors)


def _validate_csv_nullable_number(path: Path, field: str, value: str | None, errors: list[str]) -> None:
    if value not in (None, ""):
        _validate_number(path, field, value, errors)


def _validate_number(path: Path, field: str, value: Any, errors: list[str]) -> None:
    if isinstance(value, bool):
        errors.append(f"{path}: {field} must be numeric")
        return
    try:
        float(value)
    except (TypeError, ValueError):
        errors.append(f"{path}: {field} must be numeric")


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
