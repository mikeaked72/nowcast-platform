"""
estat_ingest.py — Fetch Japanese Government Statistics from e-Stat API.

Portal: https://www.e-stat.go.jp/en
API docs: https://www.e-stat.go.jp/api/en/api-dev/how_to_use
Registration: https://www.e-stat.go.jp/mypage/ (free, instant)

Base URL:
    https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData
    ?appId={ESTAT_APP_ID}&statsDataId={TABLE_ID}&...

The API is free. An application ID (appId) is required — register at the
e-Stat mypage (free, instant). Store the key in .env as ESTAT_APP_ID.

Data is returned as JSON with a nested structure:
    GET_STATS_DATA > STATISTICAL_DATA > DATA_INF > VALUE[]

Each VALUE object has dimension attributes (tab, cat01, cat02, area, time)
and a "$" field containing the actual observation value.

Key statistical table IDs for macro data (statsDataId):
    0003427113  — Consumer Price Index (CPI), 2020-base, all items
    0003143513  — Labour Force Survey (unemployment, employment)
    0003109741  — Industrial Production Index (IIP)
    0003109680  — Indices of Tertiary Industry Activity
    0003109674  — Monthly GDP estimates (SNA)

Usage:
    from estat_ingest import fetch_table, fetch_series
    df = fetch_table("0003427113")  # CPI all items
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd
import requests


# ── env loader ────────────────────────────────────────────────────────────────

def _find_env() -> Path | None:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        cand = parent / ".env"
        if cand.exists():
            return cand
    return None


def _load_env():
    env_file = _find_env()
    if env_file is None:
        return
    pat = re.compile(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = pat.match(line)
        if not m:
            continue
        key = m.group(1)
        val = m.group(2).strip()
        if val and val[0] not in ("'", '"'):
            hash_idx = val.find("#")
            if hash_idx != -1:
                val = val[:hash_idx].strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        os.environ[key] = val


_load_env()


# ── paths ─────────────────────────────────────────────────────────────────────

RAW_ESTAT = Path(__file__).resolve().parents[2] / "store" / "raw" / "estat"
RAW_ESTAT.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


# ── fetch ─────────────────────────────────────────────────────────────────────

def fetch_table(stats_data_id: str, label: str | None = None,
                **extra_params) -> pd.DataFrame | None:
    """
    Fetch a statistical table from e-Stat by its statsDataId.

    Returns a flat DataFrame with columns for each dimension + value.
    """
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        print(f"  [ERROR] e-Stat: ESTAT_APP_ID not set in .env", file=sys.stderr)
        print(f"  Register at https://www.e-stat.go.jp/mypage/", file=sys.stderr)
        return None

    params = {
        "appId": app_id,
        "statsDataId": stats_data_id,
        "lang": "E",
        "metaGetFlg": "N",
        "cntGetFlg": "N",
        **extra_params,
    }

    try:
        r = requests.get(BASE_URL, params=params,
                         headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] e-Stat {stats_data_id}: {e}", file=sys.stderr)
        return None

    # Navigate the JSON tree
    try:
        result = data.get("GET_STATS_DATA", {})
        status = result.get("RESULT", {}).get("STATUS", -1)
        if status != 0:
            error_msg = result.get("RESULT", {}).get("ERROR_MSG", "unknown")
            print(f"  [ERROR] e-Stat {stats_data_id}: status={status} {error_msg}",
                  file=sys.stderr)
            return None

        values = result["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    except (KeyError, TypeError) as e:
        print(f"  [ERROR] e-Stat {stats_data_id}: unexpected JSON structure: {e}",
              file=sys.stderr)
        return None

    if not values:
        print(f"  [WARN] e-Stat {stats_data_id}: empty VALUE array", file=sys.stderr)
        return None

    # Flatten: each VALUE dict has dimension keys (@tab, @cat01, ..., @time)
    # and the value in "$"
    rows = []
    for v in values:
        row = {}
        for k, val in v.items():
            if k == "$":
                row["value"] = val
            elif k.startswith("@"):
                row[k[1:]] = val  # strip the @ prefix
            else:
                row[k] = val
        rows.append(row)

    df = pd.DataFrame(rows)

    # Save raw
    fname = label or stats_data_id
    out_path = RAW_ESTAT / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


def fetch_series(stats_data_id: str, label: str | None = None,
                 time_col: str = "time", value_col: str = "value",
                 **extra_params) -> pd.DataFrame | None:
    """
    Fetch and clean to a simple date/value DataFrame.
    """
    df = fetch_table(stats_data_id, label=label, **extra_params)
    if df is None or df.empty:
        return None

    if time_col not in df.columns or value_col not in df.columns:
        print(f"  [WARN] e-Stat {stats_data_id}: missing {time_col}/{value_col} columns. "
              f"Available: {list(df.columns)[:10]}", file=sys.stderr)
        return df  # return the raw table so caller can inspect

    clean = pd.DataFrame({
        "date": df[time_col].astype(str),
        "value": pd.to_numeric(df[value_col], errors="coerce"),
    }).dropna().reset_index(drop=True)

    if not clean.empty:
        fname = (label or stats_data_id) + "_clean"
        out_path = RAW_ESTAT / f"{fname}.csv"
        clean.to_csv(out_path, index=False)

    return clean


# ── curated catalog ───────────────────────────────────────────────────────────

ESTAT_SERIES = [
    # (local_id, statsDataId, description, extra_params)
    ("JP_CPI",        "0003427113", "Japan CPI 2020-base, all items, national", {}),
    ("JP_LABOUR",     "0003143513", "Japan Labour Force Survey — unemployment, employment", {}),
    ("JP_IIP",        "0003109741", "Japan Industrial Production Index", {}),
    ("JP_TERTIARY",   "0003109680", "Japan Tertiary Industry Activity Index", {}),
]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"RAW_ESTAT: {RAW_ESTAT}\n")

    if not os.environ.get("ESTAT_APP_ID"):
        print("ESTAT_APP_ID not set in .env")
        print("Register free at: https://www.e-stat.go.jp/mypage/")
        print("Then add to .env:  ESTAT_APP_ID=\"your-app-id\"")
        sys.exit(1)

    for local_id, sid, desc, params in ESTAT_SERIES:
        print(f"  {local_id:15} {sid:15} {desc}")
        df = fetch_table(sid, label=local_id, **params)
        if df is not None and not df.empty:
            print(f"    OK: {df.shape[0]:,} rows, {df.shape[1]} cols")
            print(f"    Columns: {list(df.columns)[:8]}")
        else:
            print(f"    FAILED")
