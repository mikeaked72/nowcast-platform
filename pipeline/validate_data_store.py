"""
Validate the macro data store manifest and processed parquet coverage.

Usage:
    python pipeline/validate_data_store.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store"
MANIFEST = STORE / "manifest.json"
PROCESSED = STORE / "processed"

COUNTRIES = {
    "USA": ["DFF", "FEDFUNDS", "CPIAUCSL", "UNRATE", "DGS10", "DEXUSEU"],
    "AUS": ["AUS_CASHRATE", "AUS_CPI", "AUS_UNEMP", "AUDUSD", "AUS_GDP_REAL"],
    "CAN": ["CAN_OVERNIGHT", "CAN_CPI", "CAN_UNEMP", "USDCAD", "CAN_GDP_REAL"],
    "EA": ["ECB_DFR", "EA_HICP", "EA_UNEMP", "EA_GDP_REAL", "EUR_USD"],
    "GBR": ["UK_BANK_RATE", "UK_GILT_5Y", "UK_GILT_10Y", "UK_GILT_20Y", "UK_CPI", "UK_UNEMP", "UK_GDP_Q"],
    "DEU": [
        "DE_BUND10", "DE_BUND_2Y", "DE_BUND_10Y", "DEU_HICP_YOY_M",
        "DEU_UNEMP_M", "DEU_GDP_REAL_Q", "DEU_HH_CREDIT",
        "DEU_NFC_CREDIT", "DEU_INDPRO_M",
    ],
    "BRA": ["BRA_CPI", "BRA_POLICY_RATE", "BRA_EXCHANGE_RATE", "BRA_BROAD_MONEY"],
    "FRA": ["FRA_HICP_YOY_M", "FRA_UNEMP_M", "FRA_GDP_REAL_Q"],
    "ITA": ["ITA_HICP_YOY_M", "ITA_UNEMP_M", "ITA_GDP_REAL_Q"],
    "ESP": ["ESP_HICP_YOY_M", "ESP_UNEMP_M", "ESP_GDP_REAL_Q"],
    "NLD": ["NLD_HICP_YOY_M", "NLD_UNEMP_M", "NLD_GDP_REAL_Q"],
    "SWE": ["SWE_HICP_YOY_M", "SWE_UNEMP_M", "SWE_GDP_REAL_Q"],
    "CHE": ["CHE_HICP_YOY_M", "CHE_UNEMP_M", "CHE_GDP_REAL_Q"],
    "JPN": ["JPN_CPI_INFLATION", "JPN_GDP_REAL", "JP_CGPI", "JP_CURRENT_ACCOUNT"],
}


def load_manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def processed_columns() -> dict[str, set[str]]:
    cols: dict[str, set[str]] = {}
    for path in PROCESSED.glob("*.parquet"):
        df = pd.read_parquet(path)
        cols[path.stem] = set(df.columns)
    return cols


def main() -> int:
    manifest = load_manifest()
    series = manifest.get("series", {})
    status_counts: dict[str, int] = {}
    for item in series.values():
        status = item.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    cols = processed_columns()
    all_cols = set().union(*cols.values()) if cols else set()

    print("Data-store validation")
    print("=" * 60)
    print(f"Manifest series: {len(series)}")
    print("Statuses: " + ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
    for freq, names in sorted(cols.items()):
        print(f"{freq:10} columns={len(names):4}")

    print("\nCoverage matrix")
    print("-" * 60)
    for country, expected in COUNTRIES.items():
        flags = []
        for name in expected:
            in_manifest = name in series and series[name].get("status") == "OK"
            in_processed = name in all_cols
            flags.append(f"{name}:{'Y' if in_manifest or in_processed else 'n'}")
        print(f"{country:4} " + "  ".join(flags))

    suspicious = []
    for name, item in sorted(series.items()):
        rows = int(item.get("rows") or 0)
        if item.get("status") == "OK" and rows < 5:
            suspicious.append(f"{name} rows={rows}")
    if suspicious:
        print("\nShort OK series")
        print("-" * 60)
        for row in suspicious[:25]:
            print(row)
        if len(suspicious) > 25:
            print(f"... {len(suspicious) - 25} more")

    print("\nValidation completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
