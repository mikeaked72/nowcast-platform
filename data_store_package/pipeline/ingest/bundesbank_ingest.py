"""
bundesbank_ingest.py — Fetch data from the Deutsche Bundesbank statistical API.

The Bundesbank publishes a SDMX REST API at:
    https://api.statistiken.bundesbank.de/rest/data/{flow}/{key}

No authentication required. Data is also available as CSV with a simpler URL:
    https://api.statistiken.bundesbank.de/rest/data/{flow}/{key}?format=csv&lang=en

Common dataflows used here:
    BBK01     — Capital market interest rates (German bund yields, money market)
    BBNZ1     — Macro indicators (national accounts contributions)
    BBSIS     — Statistical interactive system (legacy alias)
    BBKRT     — Banking and credit aggregates
    BBSSE     — Securities markets and yields

Series codes are dot-separated within each dataflow. The "key" is essentially
the full series identifier minus the dataflow prefix.

Usage:
    from bundesbank_ingest import fetch
    df = fetch("BBK01", "BBK01.WT3110")  # 10Y German Bund yield
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_BUBA = Path(__file__).resolve().parents[2] / "store" / "raw" / "bundesbank"
RAW_BUBA.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.statistiken.bundesbank.de/rest/data"
HEADERS = {
    "Accept": "text/csv",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


def fetch(flow: str, series_key: str, start_period: str | None = None,
          label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a Bundesbank series. Returns DataFrame with date, value columns.
    """
    url = f"{BASE_URL}/{flow}/{series_key}"
    params = {"format": "csv", "lang": "en"}
    if start_period:
        params["startPeriod"] = start_period

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BUBA {series_key}: {e}", file=sys.stderr)
        return None

    if not r.text.strip():
        print(f"  [WARN] BUBA {series_key}: empty response", file=sys.stderr)
        return None

    try:
        # Bundesbank CSVs have ~9 metadata rows; the actual data table starts
        # below them. Find the row that begins with a date-like value.
        lines = r.text.splitlines()
        data_start = 0
        for i, line in enumerate(lines):
            first = line.split(",")[0].strip().strip('"')
            if len(first) >= 7 and (first[:4].isdigit() and first[4] in "-/."):
                data_start = i
                break
        data_text = "\n".join(lines[data_start:])
        df = pd.read_csv(StringIO(data_text), header=None,
                         names=["date", "value"], usecols=[0, 1])
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().reset_index(drop=True)
    except Exception as e:
        print(f"  [ERROR] parse {series_key}: {e}", file=sys.stderr)
        return None

    if df.empty:
        return None

    fname = label or series_key.replace(".", "_")
    out_path = RAW_BUBA / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# Curated map of German series mirroring FRED-MD/QD concepts.
BUBA_SERIES = [
    # ── Group 6: Interest rates (Bund yields, ECB-set rates filtered to DE) ─
    ("DE_BUND_3M",   "BBK01", "BBK01.ST0316",  "DE 3-month interbank rate"),
    ("DE_BUND_2Y",   "BBK01", "BBK01.WT3210",  "DE 2-year Bund yield"),
    ("DE_BUND_5Y",   "BBK01", "BBK01.WT3510",  "DE 5-year Bund yield"),
    ("DE_BUND_10Y",  "BBK01", "BBK01.WT3110",  "DE 10-year Bund yield (Umlaufrendite)"),
    ("DE_BUND_30Y",  "BBK01", "BBK01.WT3030",  "DE 30-year Bund yield"),

    # ── Group 5: Money & Credit (legacy DE M-aggregates) ────────────────────
    ("DE_HH_LOANS",  "BBKRT", "BBKRT.M.U.NS.A.A.A.AB.A.A.PUR.A.A",
        "DE household loans (legacy)"),
    ("DE_NFC_LOANS", "BBKRT", "BBKRT.M.U.NS.A.A.A.NF.A.A.PUR.A.A",
        "DE non-financial corp loans (legacy)"),
]


if __name__ == "__main__":
    print(f"RAW_BUBA: {RAW_BUBA}\n")
    for local_id, flow, key, desc in BUBA_SERIES:
        print(f"  {local_id:15} {desc}")
        df = fetch(flow, key, start_period="2000", label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {len(df):,} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
        else:
            print(f"    FAILED")
