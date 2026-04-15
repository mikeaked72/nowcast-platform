"""
imf_ingest.py — Fetch data from IMF International Financial Statistics (IFS)
and other IMF datasets via their SDMX JSON REST API.

Endpoint: http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/{database}/{dimensions}
No authentication required. Free. Covers ~200 countries.

Databases:
    IFS    — International Financial Statistics (the main macro database)
    DOT    — Direction of Trade
    BOP    — Balance of Payments
    GFS    — Government Finance Statistics
    WEO    — World Economic Outlook (semi-annual forecasts)
    CPI    — Consumer Price Index (dedicated)
    FSI    — Financial Soundness Indicators

IFS dimension structure: {freq}.{area}.{indicator}
    freq:      A (annual), Q (quarterly), M (monthly)
    area:      2-letter ISO code (US, GB, AU, JP, DE, CN, IN, BR, ZA, KR, MX, ID, etc.)
    indicator: IFS concept code (e.g. PCPI_IX for CPI, NGDP_XDC for nominal GDP)

Key IFS indicators (maps to FRED-MD/QD):
    PCPI_IX          — Consumer prices, all items, index
    PCPI_PC_CP_A_PT  — CPI, % change, period average
    NGDP_XDC         — GDP, national currency (nominal)
    NGDP_R_XDC       — GDP, real, national currency
    LUR_PT           — Unemployment rate, %
    ENDA_XDC_USD_RATE— Exchange rate, per USD, end of period
    FITB_PA          — Treasury bill rate, %
    FPOLM_PA         — Policy rate / money market rate, %
    FILR_PA          — Lending rate, %
    FIDR_PA          — Deposit rate, %
    FM3_XDC          — Broad money (M3)
    EREER_IX         — Real effective exchange rate, index

RELEASE TIMING NOTE:
    IMF data is sourced from national statistics offices and arrives with
    an additional 1-4 week lag. For countries where we have a direct NSO
    ingestor (US/FRED, AUS/ABS, UK/ONS, JP/e-Stat, DE/DESTATIS, FR/INSEE,
    CA/StatCan), the direct source is ALWAYS earlier. Use IMF only for
    countries without a direct ingestor — primarily emerging markets.

    Typical lag vs NSO: CPI ~2-4 weeks, GDP ~4-8 weeks, rates ~1-2 weeks.
    For EM countries without good APIs (e.g. Indonesia, Turkey, Argentina),
    IMF IFS is often the ONLY machine-readable source.

Usage:
    from imf_ingest import fetch_ifs, fetch_multi_country
    df = fetch_ifs("M", "BR", "PCPI_IX")  # Brazil CPI monthly
    df = fetch_multi_country("M", ["BR","IN","ZA","ID","MX","TR"], "PCPI_IX")
"""

from __future__ import annotations

import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_IMF = Path(__file__).resolve().parents[2] / "store" / "raw" / "imf"
RAW_IMF.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Rate limiting — IMF API limits to ~10 requests per second
_LAST_REQUEST = 0.0
_MIN_INTERVAL = 0.5  # seconds between requests


def _throttle():
    global _LAST_REQUEST
    now = time.time()
    wait = _MIN_INTERVAL - (now - _LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST = time.time()


# ── core fetch ────────────────────────────────────────────────────────────────

def fetch_ifs(freq: str, area: str, indicator: str,
              start_period: str | None = None,
              end_period: str | None = None,
              label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a single IFS series.

    Args:
        freq: "M" monthly, "Q" quarterly, "A" annual
        area: ISO 2-letter country code (e.g. "BR", "IN", "CN")
        indicator: IFS indicator code (e.g. "PCPI_IX")
        start_period: "2000" or "2000-01"
        end_period: same
        label: filename override

    Returns DataFrame with date, value, area, indicator columns.
    """
    dimensions = f"{freq}.{area}.{indicator}"
    url = f"{BASE_URL}/CompactData/IFS/{dimensions}"
    params = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    _throttle()
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA, "Accept": "application/json"},
                         timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] IMF IFS {area}/{indicator}: {e}", file=sys.stderr)
        return None

    # Navigate the JSON structure
    try:
        dataset = data["CompactData"]["DataSet"]
        series = dataset.get("Series")
        if series is None:
            print(f"  [WARN] IMF IFS {area}/{indicator}: no Series in response",
                  file=sys.stderr)
            return None

        # Series can be a dict (single) or list (multiple)
        if isinstance(series, dict):
            series = [series]

        rows = []
        for s in series:
            obs = s.get("Obs", [])
            if isinstance(obs, dict):
                obs = [obs]
            area_code = s.get("@REF_AREA", area)
            ind_code = s.get("@INDICATOR", indicator)
            for o in obs:
                rows.append({
                    "date": o.get("@TIME_PERIOD", ""),
                    "value": o.get("@OBS_VALUE"),
                    "area": area_code,
                    "indicator": ind_code,
                })
    except (KeyError, TypeError) as e:
        print(f"  [ERROR] IMF IFS {area}/{indicator}: JSON parse: {e}",
              file=sys.stderr)
        return None

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    fname = label or f"IFS_{freq}_{area}_{indicator}"
    out_path = RAW_IMF / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_multi_country(freq: str, areas: list[str], indicator: str,
                        start_period: str | None = None,
                        label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a single indicator for multiple countries in one call.
    Areas joined with "+" (e.g. "BR+IN+ZA+CN+MX+ID+TR+KR").
    """
    area_str = "+".join(areas)
    dimensions = f"{freq}.{area_str}.{indicator}"
    url = f"{BASE_URL}/CompactData/IFS/{dimensions}"
    params = {}
    if start_period:
        params["startPeriod"] = start_period

    _throttle()
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA, "Accept": "application/json"},
                         timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] IMF IFS multi {indicator}: {e}", file=sys.stderr)
        return None

    try:
        dataset = data["CompactData"]["DataSet"]
        series = dataset.get("Series", [])
        if isinstance(series, dict):
            series = [series]

        rows = []
        for s in series:
            obs = s.get("Obs", [])
            if isinstance(obs, dict):
                obs = [obs]
            area_code = s.get("@REF_AREA", "")
            for o in obs:
                rows.append({
                    "date": o.get("@TIME_PERIOD", ""),
                    "value": o.get("@OBS_VALUE"),
                    "area": area_code,
                })
    except (KeyError, TypeError) as e:
        print(f"  [ERROR] IMF parse: {e}", file=sys.stderr)
        return None

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["indicator"] = indicator
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    fname = label or f"IFS_{freq}_multi_{indicator}"
    out_path = RAW_IMF / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def list_datasets() -> list[str] | None:
    """List available IMF SDMX databases."""
    url = f"{BASE_URL}/Dataflow"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        data = r.json()
        flows = data.get("Structure", {}).get("Dataflows", {}).get("Dataflow", [])
        return [f.get("KeyFamilyRef", {}).get("KeyFamilyID", "") for f in flows]
    except Exception as e:
        print(f"  [ERROR] list_datasets: {e}", file=sys.stderr)
        return None


# ── curated catalog ───────────────────────────────────────────────────────────
#
# RELEASE TIMING GUIDE:
#   For the 10 countries with direct NSO ingestors (US, AU, UK, EA, DE, FR,
#   CA, JP, NZ, CH), DON'T use IMF — use the direct source which is 1-8 weeks
#   earlier.
#
#   Use IMF IFS for these EMERGING MARKET countries:
#     CN (China), IN (India), BR (Brazil), KR (South Korea), MX (Mexico),
#     ID (Indonesia), TR (Turkey), ZA (South Africa), PL (Poland),
#     TH (Thailand), MY (Malaysia), PH (Philippines), CL (Chile),
#     CO (Colombia), PE (Peru), CZ (Czech Republic), HU (Hungary),
#     RO (Romania), IL (Israel), AE (UAE), SA (Saudi Arabia)

EM_COUNTRIES = [
    "CN", "IN", "BR", "KR", "MX", "ID", "TR", "ZA",
    "PL", "TH", "MY", "PH", "CL", "CO", "PE",
    "CZ", "HU", "RO", "IL", "AE", "SA",
]

# Also pull developed markets from IMF as a BACKUP/VALIDATION layer
DM_COUNTRIES = ["US", "GB", "AU", "JP", "DE", "FR", "CA", "CH", "NZ"]

ALL_COUNTRIES = EM_COUNTRIES + DM_COUNTRIES

# FRED-MD equivalent indicators in IFS terms
IFS_INDICATORS = [
    # (local_suffix, freq, indicator_code, description)
    ("CPI",          "M", "PCPI_IX",           "Consumer prices, all items, index"),
    ("CPI_PCT",      "M", "PCPI_PC_CP_A_PT",   "CPI % change YoY"),
    ("POLICY_RATE",  "M", "FPOLM_PA",          "Policy rate / money market rate"),
    ("LENDING_RATE", "M", "FILR_PA",           "Lending rate"),
    ("DEPOSIT_RATE", "M", "FIDR_PA",           "Deposit rate"),
    ("TBILL_RATE",   "M", "FITB_PA",           "Treasury bill rate"),
    ("FX_USD",       "M", "ENDA_XDC_USD_RATE", "Exchange rate per USD, end of period"),
    ("REER",         "M", "EREER_IX",          "Real effective exchange rate, index"),
    ("BROAD_MONEY",  "M", "FM3_XDC",           "Broad money (M3), national currency"),
    ("GDP_NOM",      "Q", "NGDP_XDC",          "Nominal GDP, national currency"),
    ("GDP_REAL",     "Q", "NGDP_R_XDC",        "Real GDP, national currency"),
    ("UNEMP",        "Q", "LUR_PT",            "Unemployment rate, %"),
]

# Full catalog: cross-product of countries × indicators
IMF_CATALOG = []
for suffix, freq, ind, desc in IFS_INDICATORS:
    IMF_CATALOG.append({
        "suffix": suffix,
        "freq": freq,
        "indicator": ind,
        "description": desc,
        "em_countries": EM_COUNTRIES,
        "dm_countries": DM_COUNTRIES,
    })


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_IMF: {RAW_IMF}\n")

    # Test with a few EM countries
    test_countries = ["BR", "IN", "ZA", "CN", "KR", "MX"]
    test_indicators = [
        ("PCPI_IX", "M", "CPI"),
        ("FPOLM_PA", "M", "Policy rate"),
        ("ENDA_XDC_USD_RATE", "M", "FX per USD"),
    ]

    ok = fail = 0
    for ind_code, freq, desc in test_indicators:
        print(f"\n{desc} ({ind_code}, {freq}) — {len(test_countries)} countries")
        df = fetch_multi_country(freq, test_countries, ind_code,
                                 start_period="2020",
                                 label=f"test_{ind_code}")
        if df is not None and not df.empty:
            countries_found = df["area"].nunique()
            print(f"  OK: {len(df):,} rows, {countries_found} countries, "
                  f"{df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
            ok += 1
        else:
            print(f"  FAILED")
            fail += 1

    print(f"\nTest: {ok} OK, {fail} FAILED")

    # Show available datasets
    print("\nAvailable IMF datasets:")
    ds = list_datasets()
    if ds:
        for d in sorted(ds)[:20]:
            print(f"  {d}")
