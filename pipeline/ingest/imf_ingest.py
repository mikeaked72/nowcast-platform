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

try:
    from common import add_common_args, configure_logging, retry_call
except ImportError:
    from pipeline.ingest.common import add_common_args, configure_logging, retry_call


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_IMF = Path(__file__).resolve().parents[2] / "store" / "raw" / "imf"
RAW_IMF.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.imf.org/external/sdmx/2.1"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Rate limiting — IMF API limits to ~10 requests per second
_LAST_REQUEST = 0.0
_MIN_INTERVAL = 0.5  # seconds between requests

ISO2_TO_IMF_AREA = {
    "AE": "ARE", "AU": "AUS", "BR": "BRA", "CA": "CAN", "CH": "CHE",
    "CL": "CHL", "CN": "CHN", "CO": "COL", "CZ": "CZE", "DE": "DEU",
    "FR": "FRA", "GB": "GBR", "HU": "HUN", "ID": "IDN", "IL": "ISR",
    "IN": "IND", "JP": "JPN", "KR": "KOR", "MX": "MEX", "MY": "MYS",
    "NZ": "NZL", "PE": "PER", "PH": "PHL", "PL": "POL", "RO": "ROU",
    "SA": "SAU", "TH": "THA", "TR": "TUR", "US": "USA", "ZA": "ZAF",
}


def _throttle():
    global _LAST_REQUEST
    now = time.time()
    wait = _MIN_INTERVAL - (now - _LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST = time.time()


# ── core fetch ────────────────────────────────────────────────────────────────

def _dataflow_for_indicator(indicator: str) -> str:
    if indicator.startswith("PCPI"):
        return "CPI"
    if indicator in {"FPOLM_PA", "FILR_PA", "FIDR_PA", "FITB_PA"}:
        return "MFS_IR"
    if indicator in {"FM3_XDC"}:
        return "MFS_MA"
    if indicator in {"ENDA_XDC_USD_RATE", "EREER_IX"}:
        return "MFS_FMP"
    return "IFS"


def _dimensions_for_indicator(freq: str, area: str, indicator: str) -> str:
    imf_area = ISO2_TO_IMF_AREA.get(area, area)
    if indicator == "PCPI_IX":
        return f"{imf_area}.CPI._T.IX.{freq}"
    if indicator == "PCPI_PC_CP_A_PT":
        return f"{imf_area}.CPI._T.YOY_PCH_PA_PT.{freq}"
    return f"{imf_area}.{indicator}.{freq}"


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
    flow = _dataflow_for_indicator(indicator)
    dimensions = _dimensions_for_indicator(freq, area, indicator)
    url = f"{BASE_URL}/data/{flow}/{dimensions}"
    params = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    _throttle()
    try:
        r = retry_call(
            lambda: requests.get(url, params=params,
                                 headers={"User-Agent": UA, "Accept": "text/csv, application/json"},
                                 timeout=60),
            label=f"IMF {flow} {area}/{indicator}",
        )
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
    except Exception as e:
        print(f"  [ERROR] IMF IFS {area}/{indicator}: {e}", file=sys.stderr)
        return None

    if df.empty or "OBS_VALUE" not in df.columns:
        return None
    df = _normalise_sdmx_csv(df, indicator)
    if df.empty:
        return None

    fname = label or f"IMF_{freq}_{area}_{indicator}"
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
    frames = []
    for area in areas:
        df = fetch_ifs(freq, area, indicator, start_period=start_period,
                       label=None)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)

    fname = label or f"IFS_{freq}_multi_{indicator}"
    out_path = RAW_IMF / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_sdmx_series(flow: str, key: str,
                      start_period: str | None = None,
                      end_period: str | None = None,
                      label: str | None = None,
                      indicator: str | None = None) -> pd.DataFrame | None:
    """
    Fetch one IMF SDMX 2.1 series by exact dataflow and dimension key.

    Use this for live-tested mappings whose current SDMX 2.1 keys do not fit
    the older IFS-style {freq, area, indicator} helper.
    """
    url = f"{BASE_URL}/data/{flow}/{key}"
    params = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    _throttle()
    try:
        r = retry_call(
            lambda: requests.get(
                url,
                params=params,
                headers={"User-Agent": UA, "Accept": "text/csv, application/json"},
                timeout=60,
            ),
            label=f"IMF {flow} {key}",
        )
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
    except Exception as e:
        print(f"  [ERROR] IMF {flow} {key}: {e}", file=sys.stderr)
        return None

    if df.empty or "OBS_VALUE" not in df.columns:
        return None
    rows = _normalise_sdmx_csv(df, indicator or key)
    if rows.empty:
        return None

    # Single promoted series should load into the processed layer as local_id,
    # not as AREA_suffix fan-out used by multi-country IMF_EM files.
    rows = rows[["date", "value"]].copy()
    fname = label or re_safe_label(f"{flow}_{key}")
    out_path = RAW_IMF / f"{fname}.csv"
    rows.to_csv(out_path, index=False)
    return rows


def _normalise_sdmx_csv(df: pd.DataFrame, indicator: str) -> pd.DataFrame:
    country_col = "COUNTRY" if "COUNTRY" in df.columns else "REF_AREA"
    rows = pd.DataFrame({
        "date": df.get("TIME_PERIOD"),
        "value": pd.to_numeric(df.get("OBS_VALUE"), errors="coerce"),
        "area": df.get(country_col),
        "indicator": indicator,
    })
    return rows.dropna(subset=["date", "value"]).reset_index(drop=True)


def re_safe_label(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in value)[:150]


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

# FRED-MD equivalent indicators in IMF SDMX terms.
# Keep the default production catalog limited to validated SDMX 2.1 keys.
ACTIVE_IFS_INDICATORS = [
    # (local_suffix, freq, indicator_code, description)
    ("CPI",          "M", "PCPI_IX",           "Consumer prices, all items, index"),
    ("CPI_PCT",      "M", "PCPI_PC_CP_A_PT",   "CPI % change YoY"),
]

DISCOVERY_IFS_INDICATORS = [
    # These legacy IFS-style concepts need current SDMX 2.1 codelist mapping
    # before they should run in the default production update.
    ("LENDING_RATE", "M", "FILR_PA",           "Lending rate"),
    ("DEPOSIT_RATE", "M", "FIDR_PA",           "Deposit rate"),
    ("TBILL_RATE",   "M", "FITB_PA",           "Treasury bill rate"),
    ("REER",         "M", "EREER_IX",          "Real effective exchange rate, index"),
    ("GDP_NOM",      "Q", "NGDP_XDC",          "Nominal GDP, national currency"),
    ("GDP_REAL",     "Q", "NGDP_R_XDC",        "Real GDP, national currency"),
    ("UNEMP",        "Q", "LUR_PT",            "Unemployment rate, %"),
]

IMF_SINGLE_SERIES = [
    (
        "BRA_POLICY_RATE",
        "MFS_IR",
        "BRA.MFS135_RT_PT_A_PT.M",
        "2020",
        "Brazil policy or money-market rate",
    ),
    (
        "BRA_EXCHANGE_RATE",
        "ER",
        "BRA.XDC_USD.PA_RT.M",
        "2020",
        "Brazil local currency per USD, period average",
    ),
    (
        "BRA_BROAD_MONEY",
        "MFS_MA",
        "BRA.BM_MAI.XDC.M",
        "2020",
        "Brazil broad money monetary aggregate",
    ),
]

# Full catalog: cross-product of countries × indicators
IMF_CATALOG = []
for suffix, freq, ind, desc in ACTIVE_IFS_INDICATORS:
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
    parser = add_common_args(__import__("argparse").ArgumentParser())
    args = parser.parse_args()
    configure_logging(args.verbose)
    print(f"RAW_IMF: {RAW_IMF}\n")
    if args.dry_run:
        df = fetch_ifs("M", "BR", "PCPI_IX", start_period="2025")
        print("OK" if df is not None else "FAILED")
        raise SystemExit(0 if df is not None else 1)

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
