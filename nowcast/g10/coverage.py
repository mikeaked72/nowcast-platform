"""Validate country config coverage against assembled vintages."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from nowcast.g10.config import load_country_config


@dataclass(frozen=True)
class ConfigCoverage:
    iso: str
    vintage_date: date
    configured_targets: int
    configured_panel_series: int
    available_series: int
    missing_targets: tuple[str, ...]
    missing_panel_series: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_targets and not self.missing_panel_series

    @property
    def configured_series(self) -> int:
        return self.configured_targets + self.configured_panel_series

    @property
    def missing_series(self) -> int:
        return len(self.missing_targets) + len(self.missing_panel_series)

    @property
    def coverage_ratio(self) -> float:
        if self.configured_series == 0:
            return 1.0
        return round((self.configured_series - self.missing_series) / self.configured_series, 4)

    def status(self, *, warning_threshold: float = 0.8) -> str:
        if self.ok:
            return "ok"
        if self.coverage_ratio >= warning_threshold:
            return "warning"
        return "error"


def check_config_coverage(
    iso: str,
    vintage_date: date,
    *,
    config_dir: Path | str = "config/countries",
    vintage_root: Path | str = "data/vintages",
) -> ConfigCoverage:
    config = load_country_config(iso, config_dir)
    vintage_path = Path(vintage_root) / iso.upper() / f"{vintage_date.isoformat()}.parquet"
    frame = pd.read_parquet(vintage_path)
    available = {str(item) for item in frame["series_id"].unique()}
    targets = {
        str(item["series"])
        for item in config.get("targets", {}).values()
        if isinstance(item, dict) and "series" in item
    }
    panel = {
        str(item["series"])
        for item in [*config.get("panel", []), *config.get("panel_quarterly", [])]
        if isinstance(item, dict) and "series" in item
    }
    return ConfigCoverage(
        iso=iso.upper(),
        vintage_date=vintage_date,
        configured_targets=len(targets),
        configured_panel_series=len(panel),
        available_series=len(available),
        missing_targets=tuple(sorted(targets - available)),
        missing_panel_series=tuple(sorted(panel - available)),
    )


def build_coverage_matrix(
    iso: str,
    vintage_date: date,
    *,
    config_dir: Path | str = "config/countries",
    vintage_root: Path | str = "data/vintages",
) -> list[dict[str, str]]:
    config = load_country_config(iso, config_dir)
    vintage_path = Path(vintage_root) / iso.upper() / f"{vintage_date.isoformat()}.parquet"
    frame = pd.read_parquet(vintage_path)
    available = {str(item) for item in frame["series_id"].unique()}
    rows: list[dict[str, str]] = []
    for target_code, item in sorted(config.get("targets", {}).items()):
        if isinstance(item, dict) and "series" in item:
            rows.append(_coverage_row(iso, vintage_date, "target", str(target_code), str(item["series"]), available))
    for item in [*config.get("panel", []), *config.get("panel_quarterly", [])]:
        if isinstance(item, dict) and "series" in item:
            rows.append(_coverage_row(iso, vintage_date, "panel", "", str(item["series"]), available))
    return rows


def write_coverage_matrix(
    iso: str,
    vintage_date: date,
    output_path: Path | str,
    *,
    config_dir: Path | str = "config/countries",
    vintage_root: Path | str = "data/vintages",
) -> Path:
    rows = build_coverage_matrix(iso, vintage_date, config_dir=config_dir, vintage_root=vintage_root)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["iso", "vintage_date", "role", "target_code", "series", "status"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def _coverage_row(
    iso: str,
    vintage_date: date,
    role: str,
    target_code: str,
    series: str,
    available: set[str],
) -> dict[str, str]:
    return {
        "iso": iso.upper(),
        "vintage_date": vintage_date.isoformat(),
        "role": role,
        "target_code": target_code,
        "series": series,
        "status": "present" if series in available else "missing",
    }
