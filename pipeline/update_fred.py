"""
update_fred.py — Download all FRED series and update manifest.json.

Run: python data-store/pipeline/update_fred.py
"""

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _import_fred_ingest():
    """Import fred_ingest despite 'data-store' being an invalid package name."""
    spec_path = Path(__file__).parent / "ingest" / "fred_ingest.py"
    spec = importlib.util.spec_from_file_location("fred_ingest", spec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.fetch


fetch = _import_fred_ingest()

SERIES = [
    "DFF", "FEDFUNDS",
    "DGS1", "DGS2", "DGS5", "DGS10", "DGS30",
    "T10Y2Y",
    "BAMLC0A0CM", "BAMLH0A0HYM2",
    "DBAA",
    "INDPRO", "UNRATE", "PAYEMS", "ICSA",
    "CPIAUCSL", "PCEPILFE", "PPIACO",
    "RSAFS", "UMCSENT",
    "HOUST", "PERMIT",
    "M2SL",
    "DTWEXBGS", "DEXUSEU", "DEXJPUS",
    "JLNUM12M",
]

STORE = Path(__file__).parents[1] / "store"
MANIFEST_PATH = STORE / "manifest.json"


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            data = json.load(f)
        # Normalise: existing manifest may be flat {series_id: {...}} without wrapper
        if "series" not in data:
            data = {"last_full_update": None, "series": data}
        return data
    return {"last_full_update": None, "series": {}}


def save_manifest(manifest: dict):
    STORE.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    manifest = load_manifest()
    total = len(SERIES)
    ok, failed = [], []

    print(f"\nFRED ingest -- {total} series\n{'-' * 40}")

    for i, sid in enumerate(SERIES, 1):
        print(f"  [{i:02d}/{total}] {sid} ...", end=" ", flush=True)
        df = fetch(sid)

        if df is None:
            failed.append(sid)
            manifest["series"][sid] = {
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "rows": 0,
                "start": None,
                "end": None,
                "status": "ERROR",
            }
            print("FAILED")
        else:
            ok.append(sid)
            manifest["series"][sid] = {
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "rows": len(df),
                "start": df["date"].iloc[0],
                "end": df["date"].iloc[-1],
                "status": "OK",
            }
            print(f"OK  ({len(df):,} rows, {df['date'].iloc[0]} to {df['date'].iloc[-1]})")

    manifest["last_full_update"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_manifest(manifest)

    # ── summary ──────────────────────────────────────────────────────────────
    total_rows = sum(manifest["series"][s]["rows"] for s in ok)
    print(f"\n{'-' * 40}")
    print(f"  Downloaded : {len(ok)}/{total} series")
    print(f"  Total rows : {total_rows:,}")
    if failed:
        print(f"  Failed     : {', '.join(failed)}")
    print(f"  Manifest   : {MANIFEST_PATH}")
    print(f"{'-' * 40}\n")


if __name__ == "__main__":
    main()
