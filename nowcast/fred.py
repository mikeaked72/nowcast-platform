"""Download public FRED CSV series used by the US nowcast scaffold."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


FRED_GRAPH_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


@dataclass(frozen=True)
class FredSeries:
    series_id: str
    name: str
    category: str
    units: str
    frequency: str


US_FRED_SERIES = {
    "GDPC1": FredSeries("GDPC1", "Real Gross Domestic Product", "target", "percent", "quarterly"),
    "INDPRO": FredSeries("INDPRO", "Industrial Production Index", "production", "percent", "monthly"),
    "PAYEMS": FredSeries("PAYEMS", "All Employees, Total Nonfarm", "labor", "percent", "monthly"),
    "RSAFS": FredSeries("RSAFS", "Advance Retail Sales", "demand", "percent", "monthly"),
    "HOUST": FredSeries("HOUST", "Housing Starts", "housing", "percent", "monthly"),
    "DSPIC96": FredSeries("DSPIC96", "Real Disposable Personal Income", "income", "percent", "monthly"),
}


def download_us_fred_series(
    output_dir: Path | str = "runs/source/us/fred",
    *,
    observation_start: str = "1990-01-01",
) -> list[Path]:
    """Download the US FRED series as raw CSV files."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for series_id in US_FRED_SERIES:
        path = root / f"{series_id}.csv"
        download_fred_csv(series_id, path, observation_start=observation_start)
        paths.append(path)
    return paths


def download_fred_csv(series_id: str, output_path: Path | str, *, observation_start: str) -> Path:
    """Download one FRED graph CSV without requiring an API key."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    query = urlencode({"id": series_id, "cosd": observation_start})
    url = f"{FRED_GRAPH_CSV_URL}?{query}"
    with urlopen(url, timeout=60) as response:
        payload = response.read()
    path.write_bytes(payload)
    return path


def read_fred_series(path: Path | str, series_id: str) -> list[tuple[date, float]]:
    """Read a downloaded FRED CSV into dated numeric observations."""

    rows: list[tuple[date, float]] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header row")
        date_column = "DATE" if "DATE" in reader.fieldnames else "observation_date"
        if date_column not in reader.fieldnames or series_id not in reader.fieldnames:
            raise ValueError(f"{path}: expected DATE or observation_date and {series_id} columns")
        for row in reader:
            raw_value = row[series_id].strip()
            if not raw_value or raw_value == ".":
                continue
            rows.append((date.fromisoformat(row[date_column]), float(raw_value)))
    if not rows:
        raise ValueError(f"{path}: no numeric observations for {series_id}")
    return rows
