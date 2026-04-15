"""
destatis_ingest.py — Fetch data from the Federal Statistical Office of Germany.

DESTATIS publishes a free Genesis-Online REST API at:
    https://www-genesis.destatis.de/genesisWS/rest/2020/data/tablefile

A free API username is required (register at:
    https://www-genesis.destatis.de/genesis/online?Menu=Anmeldung).
The username goes into .env as DESTATIS_USER and the password as
DESTATIS_PASSWORD.

Common DESTATIS table codes used here:
    61111      — Verbraucherpreisindex (national CPI)
    42153      — Index der industriellen Nettoproduktion (industrial production)
    13231      — Erwerbstaetige (employed persons)
    13211      — Arbeitslose (unemployed)
    45211      — Einzelhandelsumsatz (retail sales)
    31231      — Baugenehmigungen (building permits)
    81000      — Volkswirtschaftliche Gesamtrechnungen (national accounts)

Many tables are quarterly or monthly. The API returns a flat CSV.

Usage:
    from destatis_ingest import fetch_table
    df = fetch_table("61111-0001")  # CPI all items, monthly
"""

from __future__ import annotations

import os
import re
import sys
from io import StringIO
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

RAW_DESTATIS = Path(__file__).resolve().parents[2] / "store" / "raw" / "destatis"
RAW_DESTATIS.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www-genesis.destatis.de/genesisWS/rest/2020/data/tablefile"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


def fetch_table(table_code: str, area: str = "all",
                start_year: str = "1990",
                label: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a DESTATIS Genesis-Online table as CSV.

    Args:
        table_code: e.g. "61111-0001" (CPI all items index)
        area:       region filter; "all" returns the national series
        start_year: starting year for the data
        label:      filename override

    Requires DESTATIS_USER and DESTATIS_PASSWORD in .env.
    """
    user = os.environ.get("DESTATIS_USER")
    password = os.environ.get("DESTATIS_PASSWORD")
    if not user or not password:
        print(f"  [ERROR] DESTATIS {table_code}: DESTATIS_USER/PASSWORD not set",
              file=sys.stderr)
        return None

    params = {
        "username": user,
        "password": password,
        "name": table_code,
        "area": area,
        "compress": "false",
        "format": "ffcsv",
        "language": "en",
        "startyear": start_year,
    }

    try:
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=120)
        r.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] DESTATIS {table_code}: {e}", file=sys.stderr)
        return None

    text = r.text
    if not text.strip() or "error" in text.lower()[:200]:
        print(f"  [WARN] DESTATIS {table_code}: empty / error response", file=sys.stderr)
        return None

    try:
        df = pd.read_csv(StringIO(text), sep=";", low_memory=False)
    except Exception as e:
        print(f"  [ERROR] parse {table_code}: {e}", file=sys.stderr)
        return None

    if df.empty:
        return None

    fname = label or table_code.replace("-", "_")
    out_path = RAW_DESTATIS / f"{fname}.csv"
    df.to_csv(out_path, index=False)
    return df


# Curated DESTATIS table catalog mirroring FRED-MD/QD concepts.
DESTATIS_TABLES = [
    # ── Group 1: Output ──────────────────────────────────────────────────────
    ("DE_INDPRO",        "42153-0001", "Industrial production index, monthly"),
    ("DE_INDPRO_MFG",    "42153-0003", "Manufacturing production index, monthly"),

    # ── Group 2: Labour market ───────────────────────────────────────────────
    ("DE_EMPLOYED",      "13211-0001", "Employed persons, monthly"),
    ("DE_UNEMPLOYED",    "13211-0002", "Unemployed persons, monthly"),
    ("DE_UNRATE",        "13231-0001", "Unemployment rate (LFS), monthly"),

    # ── Group 3: Housing ─────────────────────────────────────────────────────
    ("DE_PERMITS",       "31121-0001", "Dwelling permits, total, monthly"),

    # ── Group 4: Retail ──────────────────────────────────────────────────────
    ("DE_RETAIL",        "45211-0001", "Retail trade index, monthly"),

    # ── Group 7: Prices ──────────────────────────────────────────────────────
    ("DE_CPI",           "61111-0001", "CPI all items, monthly"),
    ("DE_CPI_CORE",      "61111-0006", "CPI ex food + energy"),
    ("DE_PPI",           "61241-0001", "Producer prices industry, monthly"),

    # ── NIPA ─────────────────────────────────────────────────────────────────
    ("DE_GDP_REAL",      "81000-0011", "Real GDP, chained volumes, quarterly"),
    ("DE_GDP_NOM",       "81000-0001", "Nominal GDP, quarterly"),
]


if __name__ == "__main__":
    print(f"RAW_DESTATIS: {RAW_DESTATIS}\n")
    if not (os.environ.get("DESTATIS_USER") and os.environ.get("DESTATIS_PASSWORD")):
        print("DESTATIS_USER / DESTATIS_PASSWORD not set in .env")
        print("Register a free API user at: https://www-genesis.destatis.de/genesis/online?Menu=Anmeldung")
        sys.exit(1)

    for local_id, table, desc in DESTATIS_TABLES:
        print(f"  {local_id:15} {table:14} {desc}")
        df = fetch_table(table, label=local_id)
        if df is not None and not df.empty:
            print(f"    OK: {df.shape[0]:,} rows, {df.shape[1]} cols")
        else:
            print(f"    FAILED")
