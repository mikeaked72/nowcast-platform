"""
statcan_ingest.py — Fetch Statistics Canada data via their Web Data Service API.

No authentication required. StatCan publishes a REST API that returns
JSON data for any published table or vector series.

Docs: https://www.statcan.gc.ca/en/developers/wds/user-guide

Two endpoints used:
    POST getDataFromVectorsAndLatestNPeriods — get latest N observations for a vector
    GET  getFullTableDownloadCSV — download full table as CSV (zipped)

Common vector IDs (Statistics Canada):
    v41690973 — Overnight rate (Bank of Canada)
    v80691323 — CPI All-items, monthly (not SA)
    v2062815  — Unemployment rate (LFS)
    v41552796 — GDP at basic prices, monthly
    v122558   — Canada 10Y bond yield

Bank of Canada has its own valet API:
    https://www.bankofcanada.ca/valet/observations/{series}/csv
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_CA = Path(__file__).resolve().parents[2] / "store" / "raw" / "statcan"
RAW_CA.mkdir(parents=True, exist_ok=True)
RAW_BOC = Path(__file__).resolve().parents[2] / "store" / "raw" / "boc"
RAW_BOC.mkdir(parents=True, exist_ok=True)

STATCAN_BASE = "https://www150.statcan.gc.ca/t1/wds/rest"
BOC_BASE = "https://www.bankofcanada.ca/valet/observations"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


def fetch_statcan_vector(vector_id: int, n: int = 5000,
                         label: str | None = None) -> pd.DataFrame | None:
    """Fetch latest N observations for a Statistics Canada vector series."""
    url = f"{STATCAN_BASE}/getDataFromVectorsAndLatestNPeriods"
    payload = [{"vectorId": vector_id, "latestN": n}]

    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] StatCan v{vector_id}: {e}", file=sys.stderr)
        return None

    if not data or not isinstance(data, list):
        return None

    obj = data[0]
    if obj.get("status") != "SUCCESS":
        print(f"  [ERROR] StatCan v{vector_id}: {obj.get('status')}", file=sys.stderr)
        return None

    obs = obj.get("object", {}).get("vectorDataPoint", [])
    if not obs:
        return None

    df = pd.DataFrame([
        {"date": o["refPer"], "value": o["value"]}
        for o in obs
    ])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.dropna().reset_index(drop=True)

    fname = label or f"v{vector_id}"
    out_path = RAW_CA / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_boc_series(series_id: str, label: str | None = None) -> pd.DataFrame | None:
    """Fetch a Bank of Canada Valet API series as CSV."""
    url = f"{BOC_BASE}/{series_id}/csv"

    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BoC {series_id}: {e}", file=sys.stderr)
        return None

    # Valet CSVs have a metadata header — find "OBSERVATIONS" marker
    text = r.text
    marker = "\"OBSERVATIONS\""
    idx = text.find(marker)
    if idx == -1:
        # Try alternate marker
        marker = "OBSERVATIONS"
        idx = text.find(marker)

    if idx == -1:
        # No marker; try parsing whole thing
        data_text = text
    else:
        # Skip past the marker line
        data_text = text[idx:]
        nl = data_text.find("\n")
        data_text = data_text[nl + 1:]

    try:
        df = pd.read_csv(StringIO(data_text))
        # Standard BoC CSV columns: date, series_id
        if "date" not in df.columns and df.columns[0].lower() == "date":
            df.columns = ["date"] + list(df.columns[1:])
        df = df.rename(columns={df.columns[0]: "date"})
        value_col = df.columns[1] if len(df.columns) > 1 else None
        if value_col:
            df = df[["date", value_col]].rename(columns={value_col: "value"})
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna().reset_index(drop=True)
    except Exception as e:
        print(f"  [ERROR] BoC parse {series_id}: {e}", file=sys.stderr)
        return None

    fname = label or series_id
    out_path = RAW_BOC / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# Catalog of Canadian series we want
CANADA_CATALOG = [
    # (local_id, source, series_id_or_vector, description)
    ("CAN_OVERNIGHT",  "boc", "V39079", "Bank of Canada Overnight Rate Target"),
    ("CAN_10Y",        "boc", "BD.CDN.10YR.DQ.YLD", "Canada 10Y Gov Bond"),
    ("CAN_2Y",         "boc", "BD.CDN.2YR.DQ.YLD",  "Canada 2Y Gov Bond"),
    ("USDCAD",         "boc", "FXUSDCAD",           "USD/CAD Exchange Rate"),
    ("CAN_CPI",        "statcan", 41690973, "Canada CPI All-items"),
    ("CAN_UNEMP",      "statcan", 2062815,  "Canada Unemployment Rate"),
]


if __name__ == "__main__":
    print(f"RAW_CA: {RAW_CA}")
    print(f"RAW_BOC: {RAW_BOC}\n")

    for local_id, source, sid, desc in CANADA_CATALOG:
        print(f"  {local_id:15} {desc}")
        if source == "statcan":
            df = fetch_statcan_vector(sid, label=local_id)
        elif source == "boc":
            df = fetch_boc_series(sid, label=local_id)
        else:
            continue

        if df is not None and not df.empty:
            print(f"    OK: {len(df)} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
        else:
            print(f"    FAILED")
