"""Validate country config coverage against assembled vintages."""

from __future__ import annotations

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

