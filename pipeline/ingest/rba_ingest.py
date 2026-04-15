"""
rba_ingest.py — Download RBA statistical tables and extract series.

The RBA publishes statistical tables at stable URLs in CSV and XLSX form.
The CSV format is tricky: rows 0-10 are metadata (Title, Description,
Frequency, Type, Units, Source, Publication, Series ID), data starts after.

Usage:
    from rba_ingest import fetch_table, fetch_series
    raw_df = fetch_table("f1")                  # raw download (metadata + data)
    df = fetch_series("f1", "FIRMMCRTD")        # clean date/value DataFrame
"""

import csv
import os
import re
import sys
from io import StringIO, BytesIO
from pathlib import Path

import pandas as pd
import requests


def _parse_ragged_csv(text: str) -> pd.DataFrame:
    """Parse a CSV whose rows have differing field counts (RBA metadata header)."""
    rows = list(csv.reader(StringIO(text)))
    if not rows:
        return pd.DataFrame()
    max_len = max(len(r) for r in rows)
    rows = [r + [""] * (max_len - len(r)) for r in rows]
    return pd.DataFrame(rows, dtype=str)


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_RBA = Path(__file__).resolve().parents[2] / "store" / "raw" / "rba"
RAW_RBA.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/csv, application/vnd.ms-excel, application/octet-stream, */*",
}

# Known RBA CSV table URLs — we try CSV first, fall back to XLSX
RBA_CSV_URLS = {
    "f1":   "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv",
    "f1.1": "https://www.rba.gov.au/statistics/tables/csv/f1.1-data.csv",
    "f2":   "https://www.rba.gov.au/statistics/tables/csv/f2-data.csv",
    "f2.1": "https://www.rba.gov.au/statistics/tables/csv/f2.1-data.csv",
    "f5":   "https://www.rba.gov.au/statistics/tables/csv/f5-data.csv",
    "f11":  "https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv",
    "f11.1":"https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv",
    "d2":   "https://www.rba.gov.au/statistics/tables/csv/d2-data.csv",
    "d3":   "https://www.rba.gov.au/statistics/tables/csv/d3-data.csv",
    "i2":   "https://www.rba.gov.au/statistics/tables/csv/i2-data.csv",
    "g1":   "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv",
    "h3":   "https://www.rba.gov.au/statistics/tables/csv/h3-data.csv",
}

RBA_XLSX_URLS = {
    "f1":   "https://www.rba.gov.au/statistics/tables/xls/f01d.xlsx",
    "f1.1": "https://www.rba.gov.au/statistics/tables/xls/f01hist.xlsx",
    "f2":   "https://www.rba.gov.au/statistics/tables/xls/f02d.xlsx",
    "f2.1": "https://www.rba.gov.au/statistics/tables/xls/f02hist.xlsx",
    "f11":  "https://www.rba.gov.au/statistics/tables/xls/f11hist.xls",
    "f11.1":"https://www.rba.gov.au/statistics/tables/xls/f11hist.xls",
    "i2":   "https://www.rba.gov.au/statistics/tables/xls/i02hist.xlsx",
}


def _download(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  [ERROR] download {url}: {e}", file=sys.stderr)
        return None


def fetch_table(table_id: str) -> pd.DataFrame | None:
    """
    Download an RBA table. Tries CSV first, then XLSX fallback.
    Saves raw bytes to raw\\rba\\{table_id}.{csv|xlsx}.
    Returns a DataFrame with headers as data (no assumed header row).
    """
    key = table_id.lower()

    # Try CSV first
    csv_url = RBA_CSV_URLS.get(key)
    if csv_url:
        raw = _download(csv_url)
        if raw is not None:
            out_path = RAW_RBA / f"{key}.csv"
            out_path.write_bytes(raw)
            try:
                df = _parse_ragged_csv(raw.decode("utf-8-sig"))
                if not df.empty:
                    return df
            except Exception as e:
                print(f"  [WARN] CSV parse {key}: {e}", file=sys.stderr)

    # XLSX fallback
    xlsx_url = RBA_XLSX_URLS.get(key)
    if xlsx_url:
        raw = _download(xlsx_url)
        if raw is not None:
            ext = "xlsx" if xlsx_url.endswith(".xlsx") else "xls"
            out_path = RAW_RBA / f"{key}.{ext}"
            out_path.write_bytes(raw)
            try:
                df = pd.read_excel(BytesIO(raw), sheet_name=0, header=None,
                                   dtype=str, engine="openpyxl" if ext == "xlsx" else None)
                return df
            except Exception as e:
                print(f"  [WARN] XLSX parse {key}: {e}", file=sys.stderr)

    return None


def _find_series_column(df: pd.DataFrame, series_id: str) -> int | None:
    """Find the column index matching a Series ID. Search first 20 rows."""
    target = series_id.strip().upper()
    max_row = min(25, len(df))
    for row_idx in range(max_row):
        row = df.iloc[row_idx]
        for col_idx, val in enumerate(row):
            if pd.isna(val):
                continue
            sval = str(val).strip().upper()
            if sval == target:
                return col_idx
    return None


def _find_data_start_row(df: pd.DataFrame) -> int:
    """Find the first row where column 0 parses as a date."""
    max_row = min(30, len(df))
    for i in range(max_row):
        val = df.iloc[i, 0]
        if pd.isna(val) or str(val).strip() == "":
            continue
        try:
            d = pd.to_datetime(str(val), errors="raise", dayfirst=True)
            if pd.notna(d):
                return i
        except Exception:
            continue
    return 11  # fallback to known RBA default


def fetch_series(table_id: str, series_id: str) -> pd.DataFrame | None:
    """
    Extract a clean date/value DataFrame for a single RBA series.
    Saves to raw\\rba\\{table_id}_{series_id}.csv.
    """
    raw_df = fetch_table(table_id)
    if raw_df is None:
        print(f"  [ERROR] {series_id}: table {table_id} could not be downloaded",
              file=sys.stderr)
        return None

    col_idx = _find_series_column(raw_df, series_id)
    if col_idx is None:
        print(f"  [ERROR] {series_id}: not found in table {table_id} "
              f"(scanned {min(25, len(raw_df))} rows, {raw_df.shape[1]} cols)",
              file=sys.stderr)
        return None

    data_start = _find_data_start_row(raw_df)

    try:
        dates = pd.to_datetime(raw_df.iloc[data_start:, 0],
                               errors="coerce", dayfirst=True)
        values = pd.to_numeric(raw_df.iloc[data_start:, col_idx], errors="coerce")
        clean = pd.DataFrame({
            "date": dates.dt.strftime("%Y-%m-%d"),
            "value": values,
        }).dropna().reset_index(drop=True)

        if clean.empty:
            print(f"  [WARN]  {series_id}: empty after clean", file=sys.stderr)
            return None

        out_path = RAW_RBA / f"{table_id.lower()}_{series_id}.csv"
        clean.to_csv(out_path, index=False)
        return clean

    except Exception as e:
        print(f"  [ERROR] clean {series_id}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    print(f"RAW_RBA: {RAW_RBA}")
    tests = [
        ("f1",  "FIRMMCRTD",   "RBA Cash Rate"),
        ("f2",  "FCMYGBAG10D", "AUS 10Y Bond"),
        ("f11", "FXRUSD",      "AUD/USD"),
        ("i2",  "GRCPBCUSD",   "Bulk Commodities USD (iron ore proxy)"),
    ]
    for table, sid, label in tests:
        print(f"\n{label} ({table}:{sid})")
        df = fetch_series(table, sid)
        if df is not None:
            print(f"  OK: {len(df):,} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
        else:
            print("  FAILED")
