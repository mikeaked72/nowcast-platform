"""
ecb_ingest.py — Fetch data from the ECB Data Portal SDMX 2.1 REST API.

Base URL (verified 2026):
    https://data-api.ecb.europa.eu/service/data/{flow_ref}/{key}

The old host `sdw-wsrest.ecb.europa.eu` was redirected to the new one until
October 2025 — anything written against the legacy host should now use
`data-api.ecb.europa.eu/service` directly.

flow_ref: {dataflow_id}   e.g. "FM", "EXR", "BSI", "ICP"
key:      dimension filter, e.g. "D.U2.EUR.4F.KR.DFR.LEV"

Pass a single combined string of the form "FLOW/KEY" to fetch().

Common ECB datasets:
    FM       Financial Markets (rates, yields, spreads)
    EXR      Exchange Rates
    ICP      Harmonised Index of Consumer Prices (HICP)
    BSI      Balance Sheet Items (monetary aggregates, MFI loans)
    MIR      MFI Interest Rates
    MNA      National Accounts
    LFSI     Labour Force Survey Indicators
    STS      Short-term statistics

Usage:
    from ecb_ingest import fetch
    df = fetch("FM/D.U2.EUR.4F.KR.DFR.LEV", start_period="2000")
    df = fetch("EXR/D.USD.EUR.SP00.A",      start_period="2000")
"""

from __future__ import annotations

import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_ECB = Path(__file__).resolve().parents[2] / "store" / "raw" / "ecb"
RAW_ECB.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://data-api.ecb.europa.eu/service/data"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# ECB accepts several SDMX-CSV variants. Try each in order — ECB sometimes
# returns 406 for stricter content-type negotiation.
ACCEPT_HEADERS = [
    "application/vnd.sdmx.data+csv;version=1.0.0",
    "application/vnd.sdmx.data+csv",
    "text/csv",
]


def fetch(series_key: str, start_period: str | None = None,
          end_period: str | None = None,
          label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch an ECB series. series_key is "DATAFLOW/KEY".

    Returns DataFrame (SDMX-CSV columns include TIME_PERIOD + OBS_VALUE +
    dimension columns).
    """
    url = f"{BASE_URL}/{series_key}"
    params: dict[str, str] = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    response = None
    last_err = None
    for accept in ACCEPT_HEADERS:
        headers = {"Accept": accept, "User-Agent": UA}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=90)
        except Exception as e:
            last_err = str(e)
            continue
        if r.status_code == 200 and r.text.strip():
            response = r
            break
        last_err = f"HTTP {r.status_code}"
        # ECB returns 404 when a series key is wrong — no point retrying accept
        if r.status_code in (400, 404):
            break

    if response is None:
        print(f"  [ERROR] ECB {series_key}: {last_err}", file=sys.stderr)
        return None

    try:
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        print(f"  [ERROR] parse {series_key}: {e}", file=sys.stderr)
        print(f"  First 300: {response.text[:300]}", file=sys.stderr)
        return None

    if df.empty:
        return None

    safe_key = series_key.replace("/", "_").replace(".", "_")[:150]
    fname = label or safe_key
    out_path = RAW_ECB / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# Common ECB series references
ECB_SERIES = {
    "ECB_DFR":   ("FM/D.U2.EUR.4F.KR.DFR.LEV",    "ECB Deposit Facility Rate"),
    "ECB_MRO":   ("FM/D.U2.EUR.4F.KR.MRR_FR.LEV", "ECB Main Refi Rate"),
    "DE_BUND10": ("YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "Germany 10Y Bund"),
    "EA_HICP":   ("ICP/M.U2.N.000000.4.ANR",      "Euro Area HICP All-items YoY"),
    "EA_UNEMP":  ("LFSI/M.I9.S.UNEHRT.TOTAL0.15_74.T",
                  "Euro Area Unemployment Rate"),
    "EUR_USD":   ("EXR/D.USD.EUR.SP00.A",         "EUR/USD Reference Rate"),
    "EUR_GBP":   ("EXR/D.GBP.EUR.SP00.A",         "EUR/GBP Reference Rate"),
    "EUR_JPY":   ("EXR/D.JPY.EUR.SP00.A",         "EUR/JPY Reference Rate"),
    "DEU_HH_CREDIT": (
        "BSI/M.DE.N.A.A20.A.1.U2.2250.Z01.E",
        "Germany MFI loans to households",
    ),
    "DEU_NFC_CREDIT": (
        "BSI/M.DE.N.A.A20.A.1.U2.2240.Z01.E",
        "Germany MFI loans to non-financial corporations",
    ),
}


if __name__ == "__main__":
    print(f"RAW_ECB: {RAW_ECB}\n")
    for local_id, (key, desc) in ECB_SERIES.items():
        print(f"  {local_id:12} {desc}")
        df = fetch(key, start_period="2000", label=local_id)
        if df is not None:
            print(f"    OK: {len(df)} rows, {df.shape[1]} cols")
        else:
            print("    FAILED")
