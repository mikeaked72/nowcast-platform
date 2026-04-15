"""
fred_ingest.py — Fetch a single FRED series and save to raw store.

Usage:
    from fred_ingest import fetch
    df = fetch("DGS10")
    df = fetch("DGS10", start_date="2000-01-01")
"""

import os
import re
import sys
from pathlib import Path

import pandas as pd
from fredapi import Fred


# ── env loader ────────────────────────────────────────────────────────────────
# Walk up from __file__ looking for .env (robust to importlib loading)

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
    # Match: [export ]KEY=VALUE, with optional quotes, ignore comments
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
        # Strip inline comment (but only if not inside quotes)
        if val and val[0] not in ("'", '"'):
            hash_idx = val.find("#")
            if hash_idx != -1:
                val = val[:hash_idx].strip()
        # Strip matching quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        os.environ[key] = val


_load_env()

# ── paths ─────────────────────────────────────────────────────────────────────

RAW_FRED = Path(__file__).resolve().parents[2] / "store" / "raw" / "fred"
RAW_FRED.mkdir(parents=True, exist_ok=True)


# ── public API ────────────────────────────────────────────────────────────────

def fetch(series_id: str, start_date: str | None = None) -> pd.DataFrame | None:
    """
    Fetch a FRED series and save to store/raw/fred/{series_id}.csv.

    Columns: date (YYYY-MM-DD string), value (float)

    Returns the DataFrame, or None on failure.
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print(f"  [ERROR] {series_id}: FRED_API_KEY not set", file=sys.stderr)
        return None

    try:
        fred = Fred(api_key=api_key)
        raw = fred.get_series(series_id, observation_start=start_date)

        if raw is None or raw.empty:
            print(f"  [WARN]  {series_id}: empty response from FRED", file=sys.stderr)
            return None

        df = raw.dropna().reset_index()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).reset_index(drop=True)

        out_path = RAW_FRED / f"{series_id}.csv"
        df.to_csv(out_path, index=False)
        return df

    except Exception as e:
        print(f"  [ERROR] {series_id}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # Quick self-test
    print(f"env file: {_find_env()}")
    print(f"FRED_API_KEY set: {bool(os.environ.get('FRED_API_KEY'))}")
    print(f"RAW_FRED: {RAW_FRED}")
    df = fetch("DGS10")
    if df is not None:
        print(f"DGS10 OK: {len(df)} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
