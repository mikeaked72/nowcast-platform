"""
insee_ingest.py — Fetch data from INSEE (Institut national de la statistique).

INSEE publishes a free REST API at:
    https://api.insee.fr/series/BDM/V1/data/{flow}/{key}

A free OAuth2 API key is required (sign up at:
    https://api.insee.fr/catalogue/site/themes/wso2/subthemes/insee/pages/help.jag).
The bearer token goes into .env as INSEE_TOKEN.

Common INSEE BDM dataflows:
    SERIES_BDM   — Banque de Données Macroéconomiques (general macro)
    IPC-1015     — Indice des prix à la consommation (CPI)
    IPI-1015     — Indice de production industrielle (industrial production)
    EMPLOI       — Employment series
    RTC          — Retail trade

Series codes are dot-separated: e.g. "001763852" is monthly CPI all items.

Usage:
    from insee_ingest import fetch_series
    df = fetch_series("001763852")  # France CPI all items index
"""

from __future__ import annotations

import os
import re
import sys
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree as ET

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

RAW_INSEE = Path(__file__).resolve().parents[2] / "store" / "raw" / "insee"
RAW_INSEE.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.insee.fr/series/BDM/V1"


def _headers() -> dict:
    token = os.environ.get("INSEE_TOKEN", "")
    h = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_series(series_id: str, label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a single INSEE BDM series. Returns DataFrame with date, value cols.
    """
    if not os.environ.get("INSEE_TOKEN"):
        print(f"  [ERROR] INSEE {series_id}: INSEE_TOKEN not set in .env",
              file=sys.stderr)
        return None

    url = f"{BASE_URL}/data/SERIES_BDM/{series_id}"
    try:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] INSEE {series_id}: {e}", file=sys.stderr)
        return None

    if not r.text.strip():
        print(f"  [WARN] INSEE {series_id}: empty response", file=sys.stderr)
        return None

    # The CSV has TIME_PERIOD and OBS_VALUE columns
    try:
        df = pd.read_csv(StringIO(r.text))
        date_col = next((c for c in df.columns if c.upper() in ("TIME_PERIOD", "DATE")),
                        None)
        val_col = next((c for c in df.columns if c.upper() in ("OBS_VALUE", "VALUE")),
                       None)
        if date_col is None or val_col is None:
            print(f"  [ERROR] {series_id}: cannot find date/value columns", file=sys.stderr)
            return None

        clean = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d"),
            "value": pd.to_numeric(df[val_col], errors="coerce"),
        }).dropna().reset_index(drop=True)
    except Exception as e:
        print(f"  [ERROR] parse {series_id}: {e}", file=sys.stderr)
        return None

    if clean.empty:
        return None

    fname = label or series_id
    out_path = RAW_INSEE / f"{fname}.csv"
    clean.to_csv(out_path, index=False)
    return clean


# Curated INSEE series catalog mirroring FRED-MD/QD concepts.
# Series IDs verified against the INSEE BDM browser.
INSEE_SERIES = [
    # ── Group 1: Output ──────────────────────────────────────────────────────
    ("FR_INDPRO",     "010767687", "France industrial production index, monthly"),
    ("FR_INDPRO_MFG", "010767701", "France manufacturing production, monthly"),

    # ── Group 2: Labour market ───────────────────────────────────────────────
    ("FR_UNRATE",     "001688526", "France unemployment rate, ILO definition, quarterly"),
    ("FR_EMPLOYMENT", "001577236", "France total employment, quarterly"),

    # ── Group 4: Consumption ─────────────────────────────────────────────────
    ("FR_RETAIL",     "001565530", "France retail trade index, monthly"),
    ("FR_HH_CONSUM",  "001616353", "France household consumption, monthly"),

    # ── Group 7: Prices ──────────────────────────────────────────────────────
    ("FR_CPI",        "001763852", "France CPI all items, monthly"),
    ("FR_CPI_CORE",   "001769683", "France core CPI ex energy and food"),
    ("FR_PPI",        "001565531", "France producer prices, monthly"),

    # ── NIPA ─────────────────────────────────────────────────────────────────
    ("FR_GDP_REAL",   "001616254", "France real GDP chained volume, quarterly"),
    ("FR_GDP_NOM",    "001616253", "France nominal GDP, quarterly"),

    # ── Sentiment ────────────────────────────────────────────────────────────
    ("FR_BUS_CLIM",   "001565198", "France business climate index"),
    ("FR_CONS_CONF",  "000857179", "France consumer confidence index"),
]


if __name__ == "__main__":
    print(f"RAW_INSEE: {RAW_INSEE}\n")
    if not os.environ.get("INSEE_TOKEN"):
        print("INSEE_TOKEN not set in .env")
        print("Register at https://api.insee.fr/catalogue/ and add to .env:")
        print('  INSEE_TOKEN="your-bearer-token"')
        sys.exit(1)

    for local_id, sid, desc in INSEE_SERIES:
        print(f"  {local_id:15} {sid:12} {desc}")
        df = fetch_series(sid, label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {len(df):,} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
        else:
            print(f"    FAILED")
