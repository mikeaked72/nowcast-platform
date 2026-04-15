"""
eurostat_ingest.py — Fetch data from Eurostat via the SDMX 2.1 REST API.

Verified base URL (as of 2026):
    https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{flow}/{key}

Eurostat uses the "ESTAT" agency ID for all non-partner datasets. For a data
query on a named dataflow, the agency prefix is optional — the short form
below works:

    .../data/prc_hicp_midx?format=SDMX-CSV
    .../data/prc_hicp_midx/M.INX_RT.CP00.EA?format=SDMX-CSV&startPeriod=2000

flow: the dataflow ID (e.g. "namq_10_gdp", "prc_hicp_midx", "une_rt_m")
key:  dot-separated dimension filter. Empty components mean "all values".
      Use "all" for every dimension — only do this if the dataset is small.

NOTE: from January 2026, HICP data is only published under ECOICOP v2
(classification change per EU regulation 2025/1182). Legacy keys may return
empty results for post-2025 periods.

Usage:
    from eurostat_ingest import fetch, list_dataflows
    df = fetch("prc_hicp_midx", "M.INX_RT.CP00.EA", start_period="2000")
    df = fetch("namq_10_gdp", "Q.CLV15_MEUR.SCA.B1GQ.EA19", start_period="2000")
"""

from __future__ import annotations

import re
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_EUROSTAT = Path(__file__).resolve().parents[2] / "store" / "raw" / "eurostat"
RAW_EUROSTAT.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Eurostat prefers the `format` query parameter over Accept header negotiation.
# We still send Accept as a backup.
DEFAULT_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"


def fetch(flow: str, key: str = "", start_period: str | None = None,
          end_period: str | None = None,
          label: str | None = None,
          agency: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a Eurostat dataflow via the SDMX 2.1 REST API.

    Args:
        flow:  dataflow ID (e.g. "namq_10_gdp")
        key:   dimension filter (default "" = all dimensions)
        start_period: "2000" or "2000-Q1" or "2000-01"
        end_period:   similar
        label: filename override
        agency: optional agency prefix (default "ESTAT" is implicit)

    Returns: DataFrame with SDMX-CSV columns, or None on failure.
    """
    # If caller supplies the agency, use the full path form
    if agency:
        url = f"{BASE_URL}/data/{agency}/{flow}/{key}"
    else:
        url = f"{BASE_URL}/data/{flow}/{key}" if key else f"{BASE_URL}/data/{flow}"

    # Strip a trailing slash if key was empty
    url = url.rstrip("/")

    params: dict[str, str] = {"format": "SDMX-CSV", "detail": "full"}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    headers = {"Accept": DEFAULT_ACCEPT, "User-Agent": UA}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=180)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Eurostat {flow}: {e}", file=sys.stderr)
        return None

    text = r.text
    if not text.strip():
        print(f"  [WARN] Eurostat {flow}: empty response", file=sys.stderr)
        return None

    # Eurostat sometimes returns an XML error body with a 200 status. Detect.
    if text.lstrip().startswith("<") and ("Error" in text[:500] or "xml" in text[:100]):
        print(f"  [WARN] Eurostat {flow}: XML error body", file=sys.stderr)
        print(f"  First 300: {text[:300]}", file=sys.stderr)
        return None

    try:
        df = pd.read_csv(StringIO(text))
    except Exception as e:
        print(f"  [ERROR] parse {flow}: {e}", file=sys.stderr)
        print(f"  First 300 chars: {text[:300]}", file=sys.stderr)
        return None

    if df.empty:
        return None

    safe_key = re.sub(r'[^A-Za-z0-9_]', '_', key)[:100]
    fname = label or (f"{flow}_{safe_key}" if safe_key else flow)
    fname = fname[:200]
    out_path = RAW_EUROSTAT / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def list_dataflows(agency: str = "ESTAT") -> list[dict] | None:
    """
    Fetch the catalog of available Eurostat dataflows.
    Returns a list of dicts: {id, agency, version, name}.
    """
    url = f"{BASE_URL}/dataflow/{agency}/all/latest"
    try:
        r = requests.get(url, headers={"Accept": "application/xml",
                                       "User-Agent": UA}, timeout=120)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] list_dataflows: {e}", file=sys.stderr)
        return None

    pat = re.compile(
        r'<str:Dataflow[^>]*id="(?P<id>[^"]+)"'
        r'[^>]*agencyID="(?P<agency>[^"]+)"'
        r'[^>]*version="(?P<version>[^"]+)"[^>]*>'
    )
    ids = [m.groupdict() for m in pat.finditer(r.text)]
    return sorted(ids, key=lambda d: d["id"])


# ── curated series catalog ────────────────────────────────────────────────────
#
# Each entry: (local_id, flow, key, start_period, description)
#
# Keys use explicit dimension filters where known to reduce payload size.
# Empty keys ("") return every dimension combination — fine for small flows
# but can return megabytes+ for large ones.

EUROSTAT_SERIES = [
    # ── Group 1: NIPA ────────────────────────────────────────────────────────
    # namq_10_gdp: freq, unit, s_adj, na_item, geo
    ("EA_GDP_REAL",      "namq_10_gdp",
        "Q.CLV15_MEUR.SCA.B1GQ.EA20",  "2000", "EA real GDP, chained volumes"),
    ("EA_GDP_NOM",       "namq_10_gdp",
        "Q.CP_MEUR.SCA.B1GQ.EA20",     "2000", "EA nominal GDP"),
    ("EA_HH_CONSUMPTION","namq_10_gdp",
        "Q.CLV15_MEUR.SCA.P31_S14_S15.EA20", "2000", "EA household consumption, real"),
    ("EA_INVESTMENT",    "namq_10_gdp",
        "Q.CLV15_MEUR.SCA.P51G.EA20",  "2000", "EA gross fixed capital formation, real"),
    ("EA_EXPORTS",       "namq_10_gdp",
        "Q.CLV15_MEUR.SCA.P6.EA20",    "2000", "EA exports, real"),
    ("EA_IMPORTS",       "namq_10_gdp",
        "Q.CLV15_MEUR.SCA.P7.EA20",    "2000", "EA imports, real"),

    # ── Group 2: Labour market ───────────────────────────────────────────────
    # une_rt_m: freq, s_adj, age, unit, sex, geo
    ("EA_UNEMPLOYMENT",  "une_rt_m",
        "M.SA.TOTAL.PC_ACT.T.EA20",    "2000", "EA monthly unemployment rate"),
    ("EA_EMPLOYMENT",    "lfsi_emp_m",
        "M.PC_ACT.TOTAL.T.EA20",       "2000", "EA monthly employment rate"),

    # ── Group 3: Housing ─────────────────────────────────────────────────────
    # sts_cobp_m: freq, indic_bt, nace_r2, s_adj, unit, geo
    ("EA_BUILD_PERMITS", "sts_cobp_m",
        "M.PSQM.F_CC11_X_CC114.SCA.I21.EA20",  "2000", "EA building permits (dwellings)"),

    # ── Group 4: Retail & industry ───────────────────────────────────────────
    # sts_inpr_m: freq, indic_bt, nace_r2, s_adj, unit, geo
    ("EA_INDPRO",        "sts_inpr_m",
        "M.PROD.B-D.SCA.I21.EA20",     "1990", "EA industrial production index, monthly"),
    ("EA_INDPRO_MFG",    "sts_inpr_m",
        "M.PROD.C.SCA.I21.EA20",       "1990", "EA manufacturing IP index"),
    ("EA_RETAIL",        "sts_trtu_m",
        "M.TOVV.G47.SCA.I21.EA20",     "2000", "EA retail trade turnover volume"),
    ("EA_NEW_ORDERS",    "sts_inno_m",
        "M.ORD_DMY.C.SCA.I21.EA20",    "2000", "EA new orders in manufacturing"),

    # ── Group 7: Prices ──────────────────────────────────────────────────────
    # prc_hicp_midx: freq, unit, coicop, geo
    ("EA_HICP_ALL",      "prc_hicp_midx",
        "M.I15.CP00.EA20",             "2000", "EA HICP all items, 2015=100"),
    ("EA_HICP_CORE",     "prc_hicp_midx",
        "M.I15.TOT_X_NRG_FOOD.EA20",   "2000", "EA HICP ex energy, food, alcohol, tobacco"),
    ("EA_HICP_ENERGY",   "prc_hicp_midx",
        "M.I15.NRG.EA20",              "2000", "EA HICP energy"),
    ("EA_HICP_SERVICES", "prc_hicp_midx",
        "M.I15.SERV.EA20",             "2000", "EA HICP services"),
    # prc_hicp_manr: annual rate of change
    ("EA_HICP_YOY",      "prc_hicp_manr",
        "M.RCH_A.CP00.EA20",           "2000", "EA HICP annual rate of change"),
    # sts_inpp_m: producer prices
    ("EA_PPI",           "sts_inpp_m",
        "M.PRC_PRR.B-E36.NSA.I21.EA20","2000", "EA industrial producer prices"),

    # ── FRED-QD Group 13: Sentiment (DG ECFIN BCS) ───────────────────────────
    # ei_bsco_m: freq, indic, s_adj, geo
    ("EA_CONS_CONF",     "ei_bsco_m",
        "M.BS-CSMCI.SA.EA20",          "1985", "EA consumer confidence indicator"),
    ("EA_ESI",           "ei_bssi_m_r2",
        "M.BS-ESI-I.SA.EA20",          "1985", "EA economic sentiment indicator"),
]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_EUROSTAT: {RAW_EUROSTAT}\n")

    ok = fail = 0
    for local_id, flow, key, start, desc in EUROSTAT_SERIES:
        print(f"  {local_id:18} {flow:16} {desc}")
        df = fetch(flow, key, start_period=start, label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {len(df):,} rows, {df.shape[1]} cols")
            ok += 1
        else:
            print(f"    FAILED")
            fail += 1

    print(f"\nTotal: {ok} OK, {fail} failed out of {len(EUROSTAT_SERIES)}")
