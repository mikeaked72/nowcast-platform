"""
ons_ingest.py — Fetch UK data from ONS + Bank of England.

TWO SOURCES IN ONE FILE (both UK, different APIs):

1. ONS Time Series API (no auth, JSON):
     https://api.ons.gov.uk/timeseries/{cdid}/dataset/{dataset}/data
   Returns JSON with months/quarters/years arrays.

2. Bank of England IADB (no auth, CSV):
     https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes
       &SeriesCodes={codes}&Datefrom={DD/MMM/YYYY}&Dateto={DD/MMM/YYYY}
       &CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N
   Returns CSV with dates in rows, series in columns.

Common ONS cdid codes (case-insensitive):
    D7BT / MM23  — CPIH All Items (2015=100)
    L55O / MM23  — CPI All Items
    MGSX / LMS   — Unemployment rate (ILO, 16+)
    MGRZ / LMS   — Employment rate
    BCAJ / LMS   — PAYE employees
    IHYP / QNA   — GDP quarterly (chained volume)
    K222 / DIOP  — Index of Production
    J5EK / RSI   — Retail Sales Index volume

Common BoE series codes:
    IUMABEDR     — Bank Rate (official)
    IUDMNZC      — 10-year nominal gilt yield
    IUDMNB4      — 2-year nominal gilt yield
    IUAAMNPY     — 10-year gilt annual avg yield
    IUMBV34      — Sterling effective exchange rate
    LPMAUZI      — Net lending to individuals (monthly)
    LPMAVAA      — Mortgage approvals

Usage:
    from ons_ingest import fetch_ons_timeseries, fetch_boe_series
    df = fetch_ons_timeseries("L55O", "MM23")  # CPI all items
    df = fetch_boe_series(["IUMABEDR", "IUDMNZC"])  # Bank Rate + 10y gilt
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_ONS = Path(__file__).resolve().parents[2] / "store" / "raw" / "ons"
RAW_ONS.mkdir(parents=True, exist_ok=True)
RAW_BOE = Path(__file__).resolve().parents[2] / "store" / "raw" / "boe"
RAW_BOE.mkdir(parents=True, exist_ok=True)

ONS_API_BASE = "https://api.ons.gov.uk"
ONS_PUBLIC_BASE = "https://www.ons.gov.uk"
BOE_BASE = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

ONS_PUBLIC_PATHS = {
    "MM23": "economy/inflationandpriceindices",
    "LMS": {
        "MGSX": "employmentandlabourmarket/peoplenotinwork/unemployment",
        "MGRZ": "employmentandlabourmarket/peopleinwork/employmentandemployeetypes",
        "BCAJ": "employmentandlabourmarket/peopleinwork/employmentandemployeetypes",
    },
    "QNA": "economy/grossdomesticproductgdp",
    "DIOP": "economy/economicoutputandproductivity/output",
    "DRSI": "businessindustryandtrade/retailindustry",
}


# ── ONS Time Series API ──────────────────────────────────────────────────────

def fetch_ons_timeseries(cdid: str, dataset: str,
                         label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch an ONS time series by its CDID code and dataset ID.

    Args:
        cdid:    ONS series identifier (e.g. "L55O", "MGSX", "IHYP")
        dataset: ONS dataset ID (e.g. "MM23", "LMS", "QNA", "DIOP")
        label:   filename override

    Returns DataFrame with date, value columns.
    """
    headers = {"User-Agent": UA, "Accept": "application/json"}
    candidates = [
        f"{ONS_API_BASE}/timeseries/{cdid.lower()}/dataset/{dataset.lower()}/data"
    ]
    public_path = ONS_PUBLIC_PATHS.get(dataset.upper())
    if isinstance(public_path, dict):
        public_path = public_path.get(cdid.upper())
    if public_path:
        candidates.append(
            f"{ONS_PUBLIC_BASE}/{public_path}/timeseries/{cdid.lower()}/{dataset.lower()}/data"
        )

    last_err = None
    try:
        data = None
        for url in candidates:
            r = requests.get(url, headers=headers, timeout=60)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                data = r.json()
                break
            last_err = f"{r.status_code} {url}"
        if data is None:
            raise RuntimeError(last_err or "no ONS endpoint returned JSON")
    except Exception as e:
        print(f"  [ERROR] ONS {cdid}/{dataset}: {e}", file=sys.stderr)
        return None

    # ONS JSON response has 'months', 'quarters', 'years' arrays
    rows = []
    for freq_key in ("months", "quarters", "years"):
        items = data.get(freq_key, [])
        for item in items:
            date_str = item.get("date")
            val = item.get("value")
            if not date_str or val is None or val == "":
                continue
            try:
                if freq_key == "months":
                    d = pd.to_datetime(date_str, format="%Y %b", errors="coerce")
                elif freq_key == "quarters":
                    # "2026 Q1" → "2026-03-31"
                    d = pd.to_datetime(
                        date_str.replace(" Q1", "-03-31")
                                .replace(" Q2", "-06-30")
                                .replace(" Q3", "-09-30")
                                .replace(" Q4", "-12-31"),
                        errors="coerce")
                else:  # years
                    d = pd.to_datetime(date_str.strip() + "-12-31", errors="coerce")

                if pd.notna(d):
                    rows.append({"date": d.strftime("%Y-%m-%d"),
                                 "value": pd.to_numeric(val, errors="coerce")})
            except Exception:
                continue

    if not rows:
        print(f"  [WARN] ONS {cdid}: no parseable observations", file=sys.stderr)
        return None

    df = pd.DataFrame(rows).dropna().sort_values("date").reset_index(drop=True)

    fname = label or f"{cdid}_{dataset}"
    out_path = RAW_ONS / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# ── Bank of England IADB ─────────────────────────────────────────────────────

def fetch_boe_series(series_codes: list[str] | str,
                     start: str = "01/Jan/1960",
                     end: str | None = None,
                     label: str | None = None) -> pd.DataFrame | None:
    """
    Download BoE IADB series as CSV.

    Args:
        series_codes: single code or list (e.g. ["IUMABEDR", "IUDMNZC"])
        start: DD/MMM/YYYY  (e.g. "01/Jan/2000")
        end:   DD/MMM/YYYY  (default: today)
        label: filename override

    Returns DataFrame with Date index and one column per series code.
    """
    if isinstance(series_codes, str):
        series_codes = [series_codes]

    if end is None:
        from datetime import datetime
        end = datetime.now().strftime("%d/%b/%Y")

    params = {
        "csv.x": "yes",
        "Datefrom": start,
        "Dateto": end,
        "SeriesCodes": ",".join(series_codes),
        "CSVF": "TN",       # tabular, no titles
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }

    try:
        r = requests.get(BOE_BASE, params=params,
                         headers={"User-Agent": UA}, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] BoE {series_codes}: {e}", file=sys.stderr)
        return None

    text = r.text
    if not text.strip() or "No data available" in text:
        print(f"  [WARN] BoE {series_codes}: empty/no data", file=sys.stderr)
        return None

    try:
        df = pd.read_csv(StringIO(text))
    except Exception as e:
        print(f"  [ERROR] BoE parse: {e}", file=sys.stderr)
        return None

    if df.empty:
        return None

    # BoE CSV typically has "DATE" as first column, then series code columns
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
        df = df.rename(columns={"DATE": "date"})
    elif df.columns[0].upper().startswith("DATE"):
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], dayfirst=True, errors="coerce")
        df = df.rename(columns={df.columns[0]: "date"})

    fname = label or "_".join(series_codes[:5])
    out_path = RAW_BOE / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# ── curated catalog ───────────────────────────────────────────────────────────

# ONS series: (local_id, cdid, dataset, description)
UK_ONS_SERIES = [
    # Group 7: Prices
    ("UK_CPI",       "L55O", "MM23", "UK CPI All Items"),
    ("UK_CPIH",      "D7BT", "MM23", "UK CPIH All Items (inc owner-occupier housing)"),
    ("UK_CPI_CORE",  "DKO8", "MM23", "UK CPI ex energy, food, alcohol, tobacco"),

    # Group 2: Labour market
    ("UK_UNEMP",     "MGSX", "LMS",  "UK ILO unemployment rate (16+)"),
    ("UK_EMPRATE",   "MGRZ", "LMS",  "UK employment rate"),
    ("UK_PAYE",      "BCAJ", "LMS",  "UK PAYE employees (monthly)"),

    # Group 1: Output
    ("UK_GDP_Q",     "IHYP", "QNA",  "UK GDP quarterly growth (chained vol)"),
    ("UK_IP",        "K22A", "DIOP", "UK Index of Production"),

    # Group 4: Retail
    ("UK_RETAIL",    "J5C4", "DRSI", "UK Retail Sales Index, volume, SA"),
]

# BoE series: (local_id, series_codes_list, description)
UK_BOE_SERIES = [
    # Group 6: Interest rates
    ("UK_BANK_RATE",  ["IUMABEDR"],   "Bank of England Bank Rate"),
    ("UK_GILT_10Y",   ["IUDMNZC"],    "UK 10-year nominal gilt yield"),
    ("UK_MORT_RATE",  ["IUMBV37"],    "UK standard variable mortgage rate"),
    ("UK_SONIA",      ["IUDSOIA"],    "Sterling Overnight Index Average (SONIA)"),

    # Group 6: Exchange rates
    ("UK_ERI",        ["IUMBV34"],    "Sterling effective exchange rate index"),

    # Group 5: Money & Credit
    ("UK_M4",         ["LPMVWYR"],    "UK M4 money supply (annual growth)"),
    ("UK_MORT_APPROVALS", ["LPMAVAA"], "UK mortgage approvals, monthly"),
    ("UK_CONS_CREDIT", ["LPMAUZI"],   "UK net lending to individuals"),
]

UK_BOE_DISCOVERY_SERIES = [
    # These curve-tenor codes currently route to a BoE error page and need
    # current IADB code discovery before returning to the production catalog.
    ("UK_GILT_2Y",    ["IUDMNB4"],    "UK 2-year nominal gilt yield"),
    ("UK_GILT_5Y",    ["IUDMNB9"],    "UK 5-year nominal gilt yield"),
    ("UK_GILT_30Y",   ["IUDMNC4"],    "UK 30-year nominal gilt yield"),
]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_ONS: {RAW_ONS}")
    print(f"RAW_BOE: {RAW_BOE}\n")

    ok = fail = 0

    print("[ONS Time Series]")
    for local_id, cdid, dataset, desc in UK_ONS_SERIES:
        print(f"  {local_id:14} {cdid:5}/{dataset:5} {desc}")
        df = fetch_ons_timeseries(cdid, dataset, label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {len(df):,} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
            ok += 1
        else:
            print(f"    FAILED")
            fail += 1

    print("\n[Bank of England IADB]")
    for local_id, codes, desc in UK_BOE_SERIES:
        print(f"  {local_id:20} {','.join(codes):12} {desc}")
        df = fetch_boe_series(codes, start="01/Jan/1990", label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {df.shape[0]:,} rows, {df.shape[1]} cols")
            ok += 1
        else:
            print(f"    FAILED")
            fail += 1

    print(f"\nTotal: {ok} OK, {fail} FAILED")
