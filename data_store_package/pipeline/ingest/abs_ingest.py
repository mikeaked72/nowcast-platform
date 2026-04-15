"""
abs_ingest.py — Fetch Australian Bureau of Statistics data via SDMX API.

ABS SDMX REST API (no auth since Nov 2024):

    Data:      https://data.api.abs.gov.au/rest/data/{flowRef}/{dataKey}[?params]
    Dataflows: https://data.api.abs.gov.au/rest/dataflow/all?detail=allstubs
    Structure: https://data.api.abs.gov.au/rest/datastructure/ABS/{flowId}/{version}

Working verified example:
    https://data.api.abs.gov.au/rest/data/ABS,CPI,1.1.0/1+2+3.10001.10.50.Q
        ?startPeriod=2010-Q1&firstNObservations=10

flowRef format: {agencyId},{dataflowId},{version}   e.g. "ABS,CPI,1.1.0"
key format:     dot-separated dimension filter, "all" for all dimensions

SDMX-CSV is the friendliest return format:
    Accept: application/vnd.sdmx.data+csv;file=true

Usage:
    from abs_ingest import fetch, list_dataflows, fetch_with_fallback
    df = fetch("ABS,CPI,1.1.0", "all", start_period="2000")
    df = fetch_with_fallback("CPI", "all", start_period="2000")
"""

from __future__ import annotations

import re
import sys
import time
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

try:
    from common import add_common_args, configure_logging, retry_call
except ImportError:
    from pipeline.ingest.common import add_common_args, configure_logging, retry_call


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_ABS = Path(__file__).resolve().parents[2] / "store" / "raw" / "abs"
RAW_ABS.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://data.api.abs.gov.au/rest"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# ABS SDMX-CSV accept headers (in preference order — we fall through on 406)
ACCEPT_HEADERS = [
    "application/vnd.sdmx.data+csv;file=true;version=1.0.0",
    "application/vnd.sdmx.data+csv;version=1.0.0",
    "application/vnd.sdmx.data+csv;labels=both;file=true",
    "application/vnd.sdmx.data+csv",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _request_with_fallback(url: str, params: dict, timeout: int = 120) -> requests.Response | None:
    """Try each accept header in turn. Return first successful response."""
    last_err = None
    for accept in ACCEPT_HEADERS:
        headers = {"Accept": accept, "User-Agent": UA}
        try:
            r = retry_call(
                lambda: requests.get(url, headers=headers, params=params, timeout=timeout),
                label=f"ABS {url}",
            )
            if r.status_code == 200 and r.text.strip():
                return r
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
            continue
    print(f"  [ERROR] {url}: all accept headers failed — {last_err}", file=sys.stderr)
    return None


# ── discovery ─────────────────────────────────────────────────────────────────

def list_dataflows(detail: str = "allstubs") -> list[dict] | None:
    """
    List every ABS dataflow. Returns a list of dicts with id, agency, version,
    and name (from the SDMX dataflow structure message).
    """
    url = f"{BASE_URL}/dataflow/all"
    params = {"detail": detail}
    try:
        r = retry_call(
            lambda: requests.get(url, headers={"Accept": "application/xml",
                                               "User-Agent": UA},
                                 params=params, timeout=60),
            label="ABS dataflow",
        )
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] list_dataflows: {e}", file=sys.stderr)
        return None

    ns = {
        "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
        "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    }
    root = ET.fromstring(r.text)
    flows = []
    for dataflow in root.findall(".//str:Dataflow", ns):
        name = dataflow.find("com:Name", ns)
        flows.append({
            "id": dataflow.attrib.get("id", ""),
            "agency": dataflow.attrib.get("agencyID", "ABS"),
            "version": dataflow.attrib.get("version", ""),
            "name": "" if name is None else (name.text or ""),
        })
    return sorted(flows, key=lambda d: d["id"])


def fetch_latest_version(flow_id: str, agency: str = "ABS") -> str | None:
    """Return the most recent version string for a dataflow, or None."""
    flows = list_dataflows()
    if not flows:
        return None
    candidates = [
        d for d in flows
        if d["id"] == flow_id and d["agency"] == agency
    ]
    if not candidates:
        return None
    # Version strings are like "1.0.0" — take the lexicographically largest
    return sorted(candidates, key=lambda d: d["version"])[-1]["version"]


# ── data fetch ────────────────────────────────────────────────────────────────

def fetch(flow_ref: str, key: str = "all",
          start_period: str | None = None,
          end_period: str | None = None,
          label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch ABS data. flow_ref is 'agency,dataflowId,version' or 'dataflowId' alone.

    Args:
        flow_ref: "ABS,CPI,1.1.0" or "CPI"
        key:      "all" or dimension filter like "1.10001.10.50.Q"
        start_period: "2000" or "2000-Q1"
        end_period:   "2025-Q4"
        label:    filename override
    """
    # Normalise the flow_ref — ABS accepts "ABS,X,Y" with commas
    if "," not in flow_ref:
        flow_ref = f"ABS,{flow_ref}"  # version defaults to latest on the ABS side

    url = f"{BASE_URL}/data/{flow_ref}/{key}"
    params: dict[str, str] = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period

    r = _request_with_fallback(url, params)
    if r is None:
        return None

    try:
        df = pd.read_csv(StringIO(r.text))
    except Exception as e:
        print(f"  [ERROR] ABS parse {flow_ref}: {e}", file=sys.stderr)
        print(f"  First 300 chars: {r.text[:300]}", file=sys.stderr)
        return None

    if df.empty:
        print(f"  [WARN] ABS {flow_ref}: empty DataFrame", file=sys.stderr)
        return None

    # Save raw
    safe_ref = flow_ref.replace(",", "_").replace("/", "_").replace(":", "_")
    safe_key = re.sub(r'[^A-Za-z0-9_]', '_', key)[:80]
    fname = label or f"{safe_ref}_{safe_key}"
    fname = fname[:200]
    out_path = RAW_ABS / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_with_fallback(dataflow_id: str, key: str = "all",
                        start_period: str | None = None,
                        label: str | None = None) -> pd.DataFrame | None:
    """
    Try multiple flow_ref formats for a dataflow:
        1. Exact version from list_dataflows()
        2. "ABS,{id}" (version defaults)
        3. "{id}" bare

    Useful when you don't know the exact version.
    """
    tried = []

    version = fetch_latest_version(dataflow_id)
    if version:
        ref = f"ABS,{dataflow_id},{version}"
        df = fetch(ref, key, start_period=start_period, label=label)
        tried.append((ref, df is not None))
        if df is not None:
            return df

    for ref in [f"ABS,{dataflow_id}", dataflow_id]:
        df = fetch(ref, key, start_period=start_period, label=label)
        tried.append((ref, df is not None))
        if df is not None:
            return df

    print(f"  [ERROR] {dataflow_id}: no version succeeded. Tried: {tried}",
          file=sys.stderr)
    return None


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = add_common_args(__import__("argparse").ArgumentParser())
    args = parser.parse_args()
    configure_logging(args.verbose)
    print(f"RAW_ABS: {RAW_ABS}\n")

    # Discover what dataflows are available
    print("Listing available ABS dataflows...")
    flows = list_dataflows()
    if flows:
        print(f"  Found {len(flows)} dataflows")
        if args.dry_run:
            raise SystemExit(0)
        # Print macro-relevant ones
        kws = ("CPI", "LABOUR", "LF", "GDP", "ANA", "WPI", "RET", "HOUS",
               "BUILD", "LEND", "BUS", "CAPEX", "BOP", "FA", "PPI", "MERCH")
        interesting = [
            d for d in flows
            if any(kw in d["id"].upper() for kw in kws)
        ]
        print(f"  Macro-relevant ({len(interesting)}):")
        for d in interesting[:30]:
            print(f"    {d['agency']:<6} {d['id']:<25} {d['version']:<8} {d['name'][:60]}")
    else:
        print("  (could not list — check connectivity)")

    print("\n--- Test 1: CPI (fetch_with_fallback) ---")
    df = fetch_with_fallback("CPI", "all", start_period="2020")
    if df is not None:
        print(f"  OK: {df.shape[0]} rows, {df.shape[1]} cols")
        print(f"  Columns: {list(df.columns)[:8]}")

    print("\n--- Test 2: Labour Force (fetch_with_fallback) ---")
    df = fetch_with_fallback("LF", "all", start_period="2020")
    if df is not None:
        print(f"  OK: {df.shape[0]} rows, {df.shape[1]} cols")

    print("\n--- Test 3: National Accounts ---")
    df = fetch_with_fallback("ANA_AGG", "all", start_period="2020")
    if df is not None:
        print(f"  OK: {df.shape[0]} rows, {df.shape[1]} cols")
