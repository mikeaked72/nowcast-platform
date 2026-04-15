"""
update_international.py — Phase 3: run all non-US/AUS ingestors and update
the data-store manifest.

Currently active sources:
    ecb_ingest.py        — ECB Data Portal SDMX (no auth)
    eurostat_ingest.py   — Eurostat SDMX (no auth)
    statcan_ingest.py    — Statistics Canada + Bank of Canada (no auth)
    ons_ingest.py        — UK Office for National Statistics (no auth)
    bundesbank_ingest.py — Deutsche Bundesbank SDMX (no auth)
    destatis_ingest.py   — DESTATIS Genesis-Online (free key required)
    insee_ingest.py      — INSEE BDM (free OAuth2 key required)
    bdf_ingest.py        — Banque de France WebStat (no auth)

Skipped if their respective API key is missing from .env.

Run: python data-store/pipeline/update_international.py
"""

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _import_mod(name: str, filename: str):
    path = Path(__file__).parent / "ingest" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _try_import(name: str, filename: str):
    """Import an ingestor or return None if it fails (missing dep, etc.)."""
    try:
        return _import_mod(name, filename)
    except Exception as e:
        print(f"  [skip] {name}: {e}")
        return None


# Always-available, no-auth sources
ecb = _try_import("ecb_ingest",        "ecb_ingest.py")
eurostat = _try_import("eurostat_ingest", "eurostat_ingest.py")
ca = _try_import("statcan_ingest",     "statcan_ingest.py")
ons = _try_import("ons_ingest",        "ons_ingest.py")
buba = _try_import("bundesbank_ingest","bundesbank_ingest.py")
bdf = _try_import("bdf_ingest",        "bdf_ingest.py")

# Sources requiring API keys — only load if env var is present
destatis = _try_import("destatis_ingest", "destatis_ingest.py") \
    if os.environ.get("DESTATIS_USER") else None
insee = _try_import("insee_ingest", "insee_ingest.py") \
    if os.environ.get("INSEE_TOKEN") else None
estat = _try_import("estat_ingest", "estat_ingest.py") \
    if os.environ.get("ESTAT_APP_ID") else None

# BoJ API — no auth required (launched Feb 2026)
boj = _try_import("boj_ingest", "boj_ingest.py")

# Global multi-country sources (no auth)
imf = _try_import("imf_ingest", "imf_ingest.py")
wb = _try_import("worldbank_ingest", "worldbank_ingest.py")

STORE = Path(__file__).parents[1] / "store"
MANIFEST_PATH = STORE / "manifest.json"


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"  [WARN] ignoring invalid manifest: {MANIFEST_PATH}")
    return {"last_full_update": None, "series": {}}


def save_manifest(manifest: dict):
    STORE.mkdir(parents=True, exist_ok=True)
    tmp_path = MANIFEST_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    tmp_path.replace(MANIFEST_PATH)


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(manifest, local_id, df, source_str):
    if df is None or df.empty:
        manifest["series"][local_id] = {
            "last_updated": now_utc(), "rows": 0,
            "start": None, "end": None,
            "source": source_str, "status": "ERROR",
        }
        return False
    first = _json_date(df["date"].iloc[0]) if "date" in df.columns else None
    last = _json_date(df["date"].iloc[-1]) if "date" in df.columns else None
    manifest["series"][local_id] = {
        "last_updated": now_utc(),
        "rows": len(df),
        "start": first, "end": last,
        "source": source_str, "status": "OK",
    }
    return True


def _json_date(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def main():
    manifest = load_manifest()
    ok, fail = [], []

    print("International data ingestion (Phase 3)")
    print("=" * 60)

    # ECB
    if ecb is not None:
        print("\n[ECB]")
        for local_id, (key, desc) in ecb.ECB_SERIES.items():
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = ecb.fetch(key, start_period="2000", label=local_id)
            if _record(manifest, local_id, df, f"ecb:{key}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # Eurostat
    if eurostat is not None:
        print("\n[Eurostat]")
        eurostat_catalog = list(eurostat.EUROSTAT_SERIES)
        eurostat_catalog.extend(getattr(eurostat, "EUROSTAT_COUNTRY_SERIES", []))
        for local_id, flow, key, start, desc in eurostat_catalog:
            print(f"  {local_id:18} ...", end=" ", flush=True)
            df = eurostat.fetch(flow, key, start_period=start, label=local_id)
            if _record(manifest, local_id, df, f"eurostat:{flow}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # Statistics Canada / BoC
    if ca is not None:
        print("\n[Canada]")
        for local_id, source, sid, desc in ca.CANADA_CATALOG:
            print(f"  {local_id:15} ...", end=" ", flush=True)
            if source == "boc":
                df = ca.fetch_boc_series(sid, label=local_id)
            else:
                df = ca.fetch_statcan_vector(sid, label=local_id)
            if _record(manifest, local_id, df, f"{source}:{sid}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # UK — ONS Time Series + Bank of England IADB
    if ons is not None:
        print("\n[UK — ONS]")
        for local_id, cdid, dataset, desc in ons.UK_ONS_SERIES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = ons.fetch_ons_timeseries(cdid, dataset, label=local_id)
            if _record(manifest, local_id, df, f"ons:{cdid}/{dataset}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

        print("\n[UK — Bank of England]")
        for local_id, codes, desc in ons.UK_BOE_SERIES:
            print(f"  {local_id:20} ...", end=" ", flush=True)
            df = ons.fetch_boe_series(codes, start="01/Jan/1990", label=local_id)
            if _record(manifest, local_id, df, f"boe:{','.join(codes)}"):
                ok.append(local_id)
                print(f"OK ({df.shape[0]:,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # Bundesbank (no auth)
    if buba is not None:
        print("\n[Bundesbank]")
        for local_id, flow, key, desc in buba.BUBA_SERIES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = buba.fetch(flow, key, start_period="2000", label=local_id)
            if _record(manifest, local_id, df, f"buba:{key}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # Banque de France (no auth)
    if bdf is not None:
        print("\n[Banque de France]")
        for local_id, flow, key, desc in bdf.BDF_SERIES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = bdf.fetch(flow, key, start_period="2000", label=local_id)
            if _record(manifest, local_id, df, f"bdf:{key}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # DESTATIS (requires DESTATIS_USER + DESTATIS_PASSWORD)
    if destatis is not None:
        print("\n[DESTATIS]")
        for local_id, table, desc in destatis.DESTATIS_TABLES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = destatis.fetch_table(table, label=local_id)
            if _record(manifest, local_id, df, f"destatis:{table}"):
                ok.append(local_id)
                print(f"OK ({df.shape[0]:,})")
            else:
                fail.append(local_id)
                print("FAILED")
    else:
        print("\n[DESTATIS] skipped — DESTATIS_USER not in .env")

    # INSEE (requires INSEE_TOKEN)
    if insee is not None:
        print("\n[INSEE]")
        for local_id, sid, desc in insee.INSEE_SERIES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = insee.fetch_series(sid, label=local_id)
            if _record(manifest, local_id, df, f"insee:{sid}"):
                ok.append(local_id)
                print(f"OK ({len(df):,})")
            else:
                fail.append(local_id)
                print("FAILED")
    else:
        print("\n[INSEE] skipped — INSEE_TOKEN not in .env")

    # e-Stat Japan (requires ESTAT_APP_ID)
    if estat is not None:
        print("\n[e-Stat Japan]")
        for local_id, sid, desc, params in estat.ESTAT_SERIES:
            print(f"  {local_id:14} ...", end=" ", flush=True)
            df = estat.fetch_table(sid, label=local_id, **params)
            if _record(manifest, local_id, df, f"estat:{sid}"):
                ok.append(local_id)
                print(f"OK ({df.shape[0]:,})")
            else:
                fail.append(local_id)
                print("FAILED")
    else:
        print("\n[e-Stat Japan] skipped — ESTAT_APP_ID not in .env")

    # Bank of Japan (no auth — API series)
    if boj is not None:
        print("\n[Bank of Japan — API]")
        for local_id, code, freq, desc in boj.BOJ_SERIES:
            print(f"  {local_id:20} ...", end=" ", flush=True)
            df = boj.fetch_series(code, start_period="200001", label=local_id)
            if _record(manifest, local_id, df, f"boj:{code}"):
                ok.append(local_id)
                print(f"OK ({df.shape[0]:,})")
            else:
                fail.append(local_id)
                print("FAILED")

        # Also try flat file downloads
        print("\n[Bank of Japan — Flat files]")
        for local_id, cat, desc in boj.BOJ_FLATFILES:
            print(f"  {local_id:20} ...", end=" ", flush=True)
            df = boj.fetch_flatfile(cat, label=local_id)
            if _record(manifest, local_id, df, f"boj:flatfile:{cat}"):
                ok.append(local_id)
                print(f"OK ({df.shape[0]:,})")
            else:
                fail.append(local_id)
                print("FAILED")

    # ── IMF IFS (no auth — EM monthly/quarterly macro) ──────────────────────
    if imf is not None:
        print("\n[IMF IFS — Emerging Markets]")
        for entry in imf.IMF_CATALOG:
            suffix = entry["suffix"]
            freq = entry["freq"]
            ind = entry["indicator"]
            desc = entry["description"]
            # Fetch EM countries in one multi-country call
            local_id = f"IMF_EM_{suffix}"
            countries = entry["em_countries"]
            print(f"  {local_id:22} {ind:22} ({len(countries)} EM) ...",
                  end=" ", flush=True)
            df = imf.fetch_multi_country(freq, countries, ind,
                                         start_period="1990",
                                         label=local_id)
            if _record(manifest, local_id, df, f"imf:IFS:{ind}"):
                ok.append(local_id)
                nc = df["area"].nunique() if "area" in df.columns else "?"
                print(f"OK ({len(df):,} rows, {nc} countries)")
            else:
                fail.append(local_id)
                print("FAILED")

    # ── World Bank (no auth — annual structural data) ─────────────────────
    if wb is not None:
        print("\n[World Bank — Annual structural]")
        for suffix, ind_code, desc in wb.WB_INDICATORS:
            local_id = f"WB_{suffix}"
            countries = wb.ALL_COUNTRIES
            print(f"  {local_id:22} {ind_code:26} ...", end=" ", flush=True)
            df = wb.fetch_multi_country(countries, ind_code,
                                        start_year=1990,
                                        label=local_id)
            if _record(manifest, local_id, df, f"wb:{ind_code}"):
                ok.append(local_id)
                nc = df["country"].nunique() if "country" in df.columns else "?"
                print(f"OK ({len(df):,} rows, {nc} countries)")
            else:
                fail.append(local_id)
                print("FAILED")

    manifest["last_full_update"] = now_utc()
    save_manifest(manifest)

    print("\n" + "=" * 60)
    print(f"  OK:     {len(ok)} series")
    print(f"  Failed: {len(fail)} series" + (f" ({', '.join(fail)})" if fail else ""))
    print(f"  Manifest: {MANIFEST_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
