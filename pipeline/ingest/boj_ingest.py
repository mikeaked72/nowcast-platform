"""
boj_ingest.py — Fetch data from the Bank of Japan Time-Series Data Search API.

API docs: https://www.stat-search.boj.or.jp/info/api_manual_en.pdf
Endpoint: https://www.stat-search.boj.or.jp/api/v1

No authentication required. The API launched in February 2026.
Outputs JSON or CSV. Contains 200,000+ time-series from the BoJ.

Series codes follow the pattern: {series_code}
    Example: "MADR1Z@D" — call rate daily
    Example: "FM08'MABASE1@M" — monetary base monthly

Common BoJ statistical categories:
    IR01  — Interest Rates (call rate, TIBOR, etc.)
    MD01  — Monetary Base
    MD02  — Money Stock
    BS01  — BOJ Balance Sheet
    BP01  — Balance of Payments
    PR01  — Price Indexes (CGPI)
    CO    — Corporate Goods Price Index

You can also download pre-built flat CSV files:
    https://www.stat-search.boj.or.jp/info/dload_en.html

Usage:
    from boj_ingest import fetch_series, fetch_flatfile
    df = fetch_series("MADR1Z@D")  # Call rate daily
    df = fetch_flatfile("ir")       # All interest rate flat files
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_BOJ = Path(__file__).resolve().parents[2] / "store" / "raw" / "boj"
RAW_BOJ.mkdir(parents=True, exist_ok=True)

API_URL = "https://www.stat-search.boj.or.jp/api/v1"
FLATFILE_BASE = "https://www.stat-search.boj.or.jp/ssi/mtshtml"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_series(series_code: str, start_period: str | None = None,
                 end_period: str | None = None,
                 freq: str = "M",
                 label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a BoJ time series by its series code.

    Args:
        series_code: e.g. "MADR1Z@D" (call rate daily), "FM08'MABASE1@M" (monetary base monthly)
        start_period: "200001" (YYYYMM) or "20000101" (YYYYMMDD)
        end_period: same format
        freq: "D" daily, "M" monthly, "Q" quarterly, "A" annual
        label: filename override

    Returns DataFrame with date/value or None on failure.
    """
    url = f"{API_URL}/search"
    params = {
        "code": series_code,
        "format": "csv",
    }
    if start_period:
        params["from"] = start_period
    if end_period:
        params["to"] = end_period

    headers = {"User-Agent": UA, "Accept": "text/csv, */*"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BoJ {series_code}: {e}", file=sys.stderr)
        return None

    text = r.text
    if not text.strip():
        print(f"  [WARN] BoJ {series_code}: empty response", file=sys.stderr)
        return None

    # BoJ CSV may have metadata rows — try parsing as-is first
    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        # Try skipping header rows — look for first line starting with a date
        lines = text.strip().splitlines()
        data_start = 0
        for i, line in enumerate(lines):
            first = line.split(",")[0].strip().strip('"')
            if len(first) >= 6 and first[:4].isdigit():
                data_start = i
                break
        try:
            df = pd.read_csv(StringIO("\n".join(lines[data_start:])))
        except Exception as e:
            print(f"  [ERROR] BoJ parse {series_code}: {e}", file=sys.stderr)
            return None

    if df.empty:
        return None

    # Save raw
    fname = label or series_code.replace("'", "_").replace("@", "_")
    out_path = RAW_BOJ / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_flatfile(category: str, label: str | None = None) -> pd.DataFrame | None:
    """
    Download a pre-built BoJ flat file (CSV) by category.

    Categories: ir (interest rates), md (money/deposits), bp (balance of payments),
                pr (prices), bs (BoJ balance sheet), co (CGPI), tn (TANKAN)
    """
    # BoJ flat files are at known URLs — the exact filenames vary
    url_map = {
        "ir": f"{FLATFILE_BASE}/IR01_en.csv",
        "md": f"{FLATFILE_BASE}/MD01_en.csv",
        "bs": f"{FLATFILE_BASE}/BS01_en.csv",
        "pr": f"{FLATFILE_BASE}/PR01_en.csv",
        "co": f"{FLATFILE_BASE}/CO01_en.csv",
    }

    url = url_map.get(category.lower())
    if not url:
        print(f"  [ERROR] BoJ flatfile: unknown category '{category}'", file=sys.stderr)
        return None

    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BoJ flatfile {category}: {e}", file=sys.stderr)
        return None

    # Save raw bytes
    fname = label or f"boj_flatfile_{category}"
    out_path = RAW_BOJ / f"{fname}.csv"
    out_path.write_bytes(r.content)

    # Parse
    try:
        df = pd.read_csv(StringIO(r.content.decode("utf-8-sig", errors="replace")),
                         low_memory=False)
    except Exception as e:
        print(f"  [ERROR] parse flatfile {category}: {e}", file=sys.stderr)
        return None

    return df


# ── curated catalog ───────────────────────────────────────────────────────────

BOJ_SERIES = [
    # (local_id, series_code, freq, description)
    ("JP_CALL_RATE",      "MADR1Z@D",        "D", "Japan call rate (uncollateralised overnight)"),
    ("JP_TIBOR_3M",       "IR02'TIBORDD3M@D","D", "Japan TIBOR 3-month daily"),
    ("JP_MONETARY_BASE",  "MD01'MABASE1@M",  "M", "Japan monetary base monthly"),
    ("JP_M2",             "MD02'M2@M",       "M", "Japan M2 money stock monthly"),
    ("JP_CGPI",           "PR01'IALL@M",     "M", "Japan Corporate Goods Price Index (all commodities)"),
]

BOJ_FLATFILES = [
    ("JP_BOJ_IR",     "ir", "BoJ interest rates (flat file)"),
    ("JP_BOJ_MD",     "md", "BoJ monetary data (flat file)"),
    ("JP_BOJ_PR",     "pr", "BoJ price data (flat file)"),
]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_BOJ: {RAW_BOJ}\n")

    # Try the API first
    print("[BoJ API series]")
    for local_id, code, freq, desc in BOJ_SERIES:
        print(f"  {local_id:20} {desc}")
        df = fetch_series(code, start_period="200001", label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {df.shape[0]:,} rows, {df.shape[1]} cols")
        else:
            print(f"    FAILED — will try flat files")

    # Try flat file fallback
    print("\n[BoJ flat files]")
    for local_id, cat, desc in BOJ_FLATFILES:
        print(f"  {local_id:20} {desc}")
        df = fetch_flatfile(cat, label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {df.shape[0]:,} rows, {df.shape[1]} cols")
        else:
            print(f"    FAILED")
