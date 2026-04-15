"""
bdf_ingest.py — Fetch data from Banque de France WebStat SDMX API.

Banque de France publishes a free SDMX REST API at:
    https://webstat.banque-france.fr/ws_wsen/rest/data/{flow}/{key}

No authentication required.

Common dataflows:
    BSI1   — Balance sheet items, monthly
    IRS    — Interest rates
    EXR    — Exchange rates
    LOANS  — Loans to households / non-financial corporations

Usage:
    from bdf_ingest import fetch
    df = fetch("IRS", "M.FR.B.A2C.AM.R.A.2240.EUR.N")
"""

from __future__ import annotations

import os
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

try:
    from common import add_common_args, configure_logging, retry_call
except ImportError:
    from pipeline.ingest.common import add_common_args, configure_logging, retry_call


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_BDF = Path(__file__).resolve().parents[2] / "store" / "raw" / "bdf"
RAW_BDF.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://webstat.banque-france.fr/ws_wsen/rest/data"
HEADERS = {
    "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


def fetch(flow: str, series_key: str, start_period: str | None = None,
          label: str | None = None) -> pd.DataFrame | None:
    url = f"{BASE_URL}/{flow}/{series_key}"
    params = {}
    if start_period:
        params["startPeriod"] = start_period

    try:
        headers = dict(HEADERS)
        client_id = os.environ.get("BDF_CLIENT_ID")
        client_secret = os.environ.get("BDF_CLIENT_SECRET")
        if client_id and client_secret:
            headers["client_id"] = client_id
            headers["client_secret"] = client_secret
        r = retry_call(lambda: requests.get(url, headers=headers, params=params, timeout=60),
                       label=f"BdF {flow}/{series_key}")
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BdF {series_key}: {e}", file=sys.stderr)
        return None

    if not r.text.strip():
        return None

    try:
        df = pd.read_csv(StringIO(r.text))
    except Exception as e:
        print(f"  [ERROR] parse {series_key}: {e}", file=sys.stderr)
        return None

    if df.empty:
        return None

    fname = label or series_key.replace(".", "_")[:120]
    out_path = RAW_BDF / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# Curated Banque de France series mirroring FRED concepts.
BDF_SERIES = [
    # ── Group 6: Interest rates ──────────────────────────────────────────────
    ("FR_OAT_10Y",   "FM",   "M.FR.D.GOV.10Y.YLD",
        "France 10-year sovereign yield (OAT)"),

    # ── Group 5: Money & Credit ──────────────────────────────────────────────
    ("FR_HH_LOANS",  "BSI1", "M.FR.N.A.A20T.A.1.U2.2240.Z01.E",
        "France household loans"),
    ("FR_NFC_LOANS", "BSI1", "M.FR.N.A.A20T.A.1.U2.2240.Z01.E",
        "France non-financial corp loans"),
]


if __name__ == "__main__":
    parser = add_common_args(__import__("argparse").ArgumentParser())
    args = parser.parse_args()
    configure_logging(args.verbose)
    if not (os.environ.get("BDF_CLIENT_ID") and os.environ.get("BDF_CLIENT_SECRET")):
        print("BDF_CLIENT_ID/BDF_CLIENT_SECRET not set; Banque de France API returned 401 without credentials.")
        raise SystemExit(0 if args.dry_run else 1)
    print(f"RAW_BDF: {RAW_BDF}\n")
    for local_id, flow, key, desc in BDF_SERIES:
        print(f"  {local_id:15} {desc}")
        df = fetch(flow, key, start_period="2000", label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {len(df):,} rows")
        else:
            print(f"    FAILED")
