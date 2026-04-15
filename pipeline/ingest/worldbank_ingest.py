"""
worldbank_ingest.py — Fetch data from the World Bank Open Data API (v2).

Endpoint: https://api.worldbank.org/v2/country/{iso2}/indicator/{indicator}
No authentication required. Free. Covers ~260 countries.

Format: add ?format=json for JSON, ?format=csv (but CSV is less reliable).
Pagination: default 50 per page; use per_page=1000 for bulk downloads.

Key indicators mapped to FRED-MD/QD concepts:
    NY.GDP.MKTP.CD       — GDP (current US$)
    NY.GDP.MKTP.KD       — GDP (constant 2015 US$)
    NY.GDP.MKTP.KD.ZG    — GDP growth (annual %)
    NY.GDP.DEFL.KD.ZG    — GDP deflator (annual % change)
    FP.CPI.TOTL.ZG       — Inflation, consumer prices (annual %)
    FP.CPI.TOTL          — CPI (2010 = 100)
    SL.UEM.TOTL.ZS       — Unemployment, total (% of labor force, ILO)
    SL.UEM.TOTL.NE.ZS    — Unemployment, national estimate
    FR.INR.RINR           — Real interest rate (%)
    FR.INR.LNDP           — Interest rate spread (lending minus deposit)
    PA.NUS.FCRF           — Official exchange rate (LCU per US$)
    FM.LBL.BMNY.GD.ZS    — Broad money (% of GDP)
    BN.CAB.XOKA.CD       — Current account balance (BoP, current US$)
    BN.CAB.XOKA.GD.ZS    — Current account (% of GDP)
    NE.EXP.GNFS.ZS       — Exports of goods and services (% of GDP)
    NE.IMP.GNFS.ZS       — Imports of goods and services (% of GDP)
    GC.DOD.TOTL.GD.ZS    — Central government debt (% of GDP)
    SP.POP.TOTL           — Population, total

RELEASE TIMING NOTE:
    World Bank data is ANNUAL only for most indicators and arrives with
    a 6-12 month lag after the reference year ends. It is NOT suitable
    for high-frequency (monthly/quarterly) signal work.

    Use World Bank for:
    1. Structural/annual data that IMF IFS doesn't cover (debt ratios,
       trade shares, population, GDP per capita)
    2. Historical backfill going back to 1960 for most countries
    3. Countries not in IMF IFS at all (rare)

    For monthly/quarterly macro data, use IMF IFS instead.

Usage:
    from worldbank_ingest import fetch_indicator, fetch_multi_country
    df = fetch_indicator("BR", "FP.CPI.TOTL.ZG")
    df = fetch_multi_country(["BR","IN","CN","ZA"], "NY.GDP.MKTP.KD.ZG")
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_WB = Path(__file__).resolve().parents[2] / "store" / "raw" / "worldbank"
RAW_WB.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.worldbank.org/v2"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

_LAST_REQUEST = 0.0
_MIN_INTERVAL = 0.3


def _throttle():
    global _LAST_REQUEST
    now = time.time()
    wait = _MIN_INTERVAL - (now - _LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST = time.time()


# ── core fetch ────────────────────────────────────────────────────────────────

def fetch_indicator(country: str, indicator: str,
                    start_year: int = 1960,
                    end_year: int = 2026,
                    label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a World Bank indicator for a single country.

    Args:
        country:   ISO 2-letter code (e.g. "BR", "IN")
        indicator: WB indicator code (e.g. "FP.CPI.TOTL.ZG")
        start_year, end_year: date range
        label: filename override

    Returns DataFrame with date (year), value, country columns.
    """
    url = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    params = {
        "format": "json",
        "per_page": 1000,
        "date": f"{start_year}:{end_year}",
    }

    _throttle()
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA}, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] WB {country}/{indicator}: {e}", file=sys.stderr)
        return None

    # WB JSON returns [metadata, [observations]]
    if not isinstance(data, list) or len(data) < 2:
        print(f"  [WARN] WB {country}/{indicator}: unexpected response structure",
              file=sys.stderr)
        return None

    obs = data[1]
    if not obs:
        print(f"  [WARN] WB {country}/{indicator}: no observations", file=sys.stderr)
        return None

    rows = []
    for o in obs:
        if o.get("value") is not None:
            rows.append({
                "date": str(o.get("date", "")),
                "value": o["value"],
                "country": o.get("country", {}).get("id", country),
                "country_name": o.get("country", {}).get("value", ""),
            })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    fname = label or f"WB_{country}_{indicator.replace('.', '_')}"
    out_path = RAW_WB / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_multi_country(countries: list[str], indicator: str,
                        start_year: int = 1990,
                        end_year: int = 2026,
                        label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a single indicator for multiple countries.
    Countries joined with ";" in the URL (max ~60 in one call).
    """
    country_str = ";".join(countries)
    url = f"{BASE_URL}/country/{country_str}/indicator/{indicator}"
    params = {
        "format": "json",
        "per_page": 5000,
        "date": f"{start_year}:{end_year}",
    }

    _throttle()
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] WB multi/{indicator}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, list) or len(data) < 2:
        return None

    obs = data[1]
    if not obs:
        return None

    rows = []
    for o in obs:
        if o.get("value") is not None:
            rows.append({
                "date": str(o.get("date", "")),
                "value": o["value"],
                "country": o.get("country", {}).get("id", ""),
                "country_name": o.get("country", {}).get("value", ""),
            })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["indicator"] = indicator
    df = df.dropna(subset=["value"]).sort_values(["country", "date"]).reset_index(drop=True)

    safe_ind = indicator.replace(".", "_")[:60]
    fname = label or f"WB_multi_{safe_ind}"
    out_path = RAW_WB / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# ── curated catalog ───────────────────────────────────────────────────────────

# All countries — EM + DM
EM_COUNTRIES = [
    "CN", "IN", "BR", "KR", "MX", "ID", "TR", "ZA",
    "PL", "TH", "MY", "PH", "CL", "CO", "PE",
    "CZ", "HU", "RO", "IL", "AE", "SA",
]
DM_COUNTRIES = ["US", "GB", "AU", "JP", "DE", "FR", "CA", "CH", "NZ"]
ALL_COUNTRIES = EM_COUNTRIES + DM_COUNTRIES

# World Bank indicators (annual) — structural data IMF IFS doesn't cover well
WB_INDICATORS = [
    # (suffix, indicator_code, description)
    ("GDP_USD",         "NY.GDP.MKTP.CD",      "GDP, current US$"),
    ("GDP_REAL",        "NY.GDP.MKTP.KD",      "GDP, constant 2015 US$"),
    ("GDP_GROWTH",      "NY.GDP.MKTP.KD.ZG",   "GDP growth, annual %"),
    ("GDP_DEFLATOR",    "NY.GDP.DEFL.KD.ZG",   "GDP deflator, annual % change"),
    ("CPI_INFLATION",   "FP.CPI.TOTL.ZG",      "Inflation, consumer prices, annual %"),
    ("UNEMPLOYMENT",    "SL.UEM.TOTL.ZS",      "Unemployment, % of labor force (ILO)"),
    ("REAL_INTEREST",   "FR.INR.RINR",          "Real interest rate, %"),
    ("FX_OFFICIAL",     "PA.NUS.FCRF",          "Official exchange rate, LCU per US$"),
    ("BROAD_MONEY_GDP", "FM.LBL.BMNY.GD.ZS",   "Broad money, % of GDP"),
    ("CA_BALANCE_GDP",  "BN.CAB.XOKA.GD.ZS",   "Current account balance, % of GDP"),
    ("EXPORTS_GDP",     "NE.EXP.GNFS.ZS",      "Exports of goods & services, % of GDP"),
    ("IMPORTS_GDP",     "NE.IMP.GNFS.ZS",      "Imports of goods & services, % of GDP"),
    ("GOVT_DEBT_GDP",   "GC.DOD.TOTL.GD.ZS",   "Central govt debt, % of GDP"),
    ("GDP_PER_CAPITA",  "NY.GDP.PCAP.CD",       "GDP per capita, current US$"),
    ("POPULATION",      "SP.POP.TOTL",          "Population, total"),
]


# ── release timing comparison ─────────────────────────────────────────────────
#
# SOURCE PRIORITY (earliest release wins):
#
# | Concept        | Best source by country                              | WB useful? |
# |----------------|-----------------------------------------------------|------------|
# | Monthly CPI    | NSO direct (ABS, ONS, DESTATIS, etc.) → IMF IFS    | No (annual)|
# | Monthly IP     | NSO direct → IMF IFS                               | No (annual)|
# | Monthly unemp  | NSO direct (ABS LF, ONS LMS) → IMF IFS            | No (annual)|
# | Quarterly GDP  | NSO direct (ANA_AGG, QNA) → IMF IFS                | No (annual)|
# | Monthly rates  | Central bank direct (RBA, BoE, ECB, BoJ) → IMF IFS| No (annual)|
# | Monthly FX     | Central bank direct → IMF IFS                      | No (annual)|
# | Annual GDP     | NSO → IMF WEO → World Bank (6-12 mo lag)           | Yes, backfill|
# | Debt/GDP       | IMF → World Bank                                   | Yes        |
# | Trade shares   | IMF DOT → World Bank                               | Yes        |
# | Population     | World Bank → UN Population Division                 | Yes        |
# | CA balance     | IMF BOP → World Bank                               | Yes        |
#
# CONCLUSION: World Bank is the ANNUAL STRUCTURAL layer.
# IMF IFS is the MONTHLY/QUARTERLY CYCLICAL layer.
# NSO direct ingestors are the REAL-TIME layer (always fastest).


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_WB: {RAW_WB}\n")

    # Test with a few indicators across EM countries
    test_countries = ["BR", "IN", "ZA", "CN", "KR", "MX"]
    test_indicators = [
        ("NY.GDP.MKTP.KD.ZG", "GDP growth %"),
        ("FP.CPI.TOTL.ZG", "CPI inflation %"),
        ("SL.UEM.TOTL.ZS", "Unemployment %"),
        ("BN.CAB.XOKA.GD.ZS", "Current account % GDP"),
    ]

    ok = fail = 0
    for ind_code, desc in test_indicators:
        print(f"\n{desc} ({ind_code}) — {len(test_countries)} countries")
        df = fetch_multi_country(test_countries, ind_code,
                                 start_year=2015,
                                 label=f"test_{ind_code.replace('.','_')}")
        if df is not None and not df.empty:
            countries_found = df["country"].nunique()
            years = df["date"].nunique()
            print(f"  OK: {len(df):,} rows, {countries_found} countries, {years} years")
            ok += 1
        else:
            print(f"  FAILED")
            fail += 1

    print(f"\nTest: {ok} OK, {fail} FAILED")
