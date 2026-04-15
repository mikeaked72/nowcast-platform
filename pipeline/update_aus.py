"""
update_aus.py — Download Australian macro series (RBA + ABS) and update manifest.

Run: python data-store/pipeline/update_aus.py
"""

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _import_mod(name: str, filename: str):
    path = Path(__file__).parent / "ingest" / filename
    ingest_dir = str(path.parent)
    if ingest_dir not in sys.path:
        sys.path.insert(0, ingest_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rba = _import_mod("rba_ingest", "rba_ingest.py")
abs_mod = _import_mod("abs_ingest", "abs_ingest.py")

STORE = Path(__file__).parents[1] / "store"
MANIFEST_PATH = STORE / "manifest.json"


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"last_full_update": None, "series": {}}


def save_manifest(manifest: dict):
    STORE.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


# Series to download — full FRED-MD/FRED-QD equivalent catalog for AUS
# (local_id, source_tag, table_or_dataflow, series_id_or_key, label)
#
# Catalog organised by FRED-MD group; see data-store/specs/macro_data_mapping.md
# for the cross-country mapping. Add new series here, then re-run.

RBA_SERIES = [
    # ── Group 6: Interest rates (RBA F1, F2, F3, F4, F5, F6) ────────────────
    ("AUS_CASHRATE",   "f1",  "FIRMMCRTD",   "RBA Cash Rate Target (daily)"),
    ("AUS_BBSW30",     "f1.1","FIRMMBAB30",  "30-day Bank Accepted Bill rate"),
    ("AUS_BBSW90",     "f1.1","FIRMMBAB90",  "90-day Bank Accepted Bill rate"),
    ("AUS_BBSW180",    "f1.1","FIRMMBAB180", "180-day Bank Accepted Bill rate"),
    ("AGB2Y",          "f2",  "FCMYGBAG2D",  "AUS 2-Year Treasury Bond Yield"),
    ("AGB3Y",          "f2",  "FCMYGBAG3D",  "AUS 3-Year Treasury Bond Yield"),
    ("AGB5Y",          "f2",  "FCMYGBAG5D",  "AUS 5-Year Treasury Bond Yield"),
    ("AGB10Y",         "f2",  "FCMYGBAG10D", "AUS 10-Year Treasury Bond Yield"),
    ("AUS_MORTGAGE",   "f5",  "FILRHLBVS",   "Standard variable housing rate"),

    # ── Group 5: Money & Credit (RBA D2, D3) ────────────────────────────────
    ("AUS_OO_HOUS_CR", "d2",  "DLCACOHN",    "Credit; Owner-occupier housing"),
    ("AUS_INV_HOUS_CR","d2",  "DLCACIHN",    "Credit; Investor housing"),
    ("AUS_PERS_CR",    "d2",  "DLCACOPN",    "Credit; Other personal"),
    ("AUS_BUS_CR",     "d2",  "DLCACBN",     "Credit; Business"),
    ("AUS_TOTAL_CR",   "d2",  "DLCACN",      "Credit; Total"),
    ("AUS_M3",         "d3",  "DMAM3N",      "M3 money supply"),
    ("AUS_BROADMNY",   "d3",  "DMABMN",      "Broad money"),
    ("AUS_MNYBASE",    "d3",  "DMAMMB",      "Money base"),

    # ── Group 6 (cont'd): Exchange rates (RBA F11) ──────────────────────────
    ("AUDUSD",         "f11", "FXRUSD",      "AUD/USD spot"),
    ("AUDJPY",         "f11", "FXRJY",       "AUD/JPY spot"),
    ("AUDEUR",         "f11", "FXREUR",      "AUD/EUR spot"),
    ("AUDGBP",         "f11", "FXRUKPS",     "AUD/GBP spot"),
    ("AUDCNY",         "f11", "FXRCR",       "AUD/CNY spot"),
    ("AUDNZD",         "f11", "FXRNZD",      "AUD/NZD spot"),
    ("AUD_TWI",        "f11", "FXRTWI",      "AUD Trade Weighted Index"),

    # ── Group 7 (cont'd): Commodity prices (RBA I2) ─────────────────────────
    ("AUS_COMM_SDR",   "i2",  "GRCPBCSDR",   "Commodity price index, SDR terms"),
    ("AUS_COMM_USD",   "i2",  "GRCPBCUSD",   "Commodity price index, USD terms"),
    ("AUS_COMM_BULK",  "i2",  "GRCPBMUSD",   "Bulk commodity price index, USD"),
    ("IRON_ORE",       "i2",  "GRCPBMUSD",   "Iron ore (proxy via bulk index)"),
    # NOTE: GRCPBCAUD, GRCPNRMUSD, GRCPRMUSD removed — not present in current RBA i2 table
]

ABS_SERIES = [
    # (local_id, flow_ref, key, start_period, label)
    #
    # Phase 2A core: one query per dataflow with key="all" pulls everything,
    # then build_processed.py routes individual series. As we firm up the
    # SDMX dimension keys we can replace key="all" with specific filters
    # to reduce data volume.

    # ── Group 1: Output & Income (Quarterly National Accounts) ──────────────
    ("AUS_NATIONAL_ACCOUNTS",  "ABS,ANA_AGG",  "all", "1990",
        "national_accounts_quarterly_aggregates"),

    # ── Group 2: Labour market ──────────────────────────────────────────────
    ("AUS_LABOUR_FORCE",       "ABS,LF",       "all", "1990",
        "labour_force_monthly"),
    # NOTE: ABS,LF_Q removed — 404 not found on ABS API

    # ── Group 7: Prices ─────────────────────────────────────────────────────
    ("AUS_CPI",                "ABS,CPI",      "all", "1980",
        "CPI_all_groups_quarterly"),
    ("AUS_MONTHLY_CPI",        "ABS,CPI_M", "all", "2018",
        "CPI_monthly_indicator"),
    ("AUS_PPI",                "ABS,PPI",      "all", "1990",
        "producer_price_indexes_quarterly"),
    ("AUS_IT_PRICE",           "ABS,ITPI_EXP", "all", "1990",
        "international_trade_price_indexes"),

    # ── Earnings & productivity (FRED-QD Group 10) ──────────────────────────
    ("AUS_WPI",                "ABS,WPI",      "all", "1997",
        "wage_price_index_quarterly"),
    ("AUS_AWE",                "ABS,AWE",      "all", "1990",
        "average_weekly_earnings"),

    # ── Group 4: Consumption, orders, inventories ───────────────────────────
    ("AUS_RETAIL",             "ABS,RT",       "all", "1990",
        "retail_trade_monthly"),
    ("AUS_RETAIL_VOL",         "ABS,RT",       "all", "1990",
        "retail_trade_volume_quarterly"),
    ("AUS_BUS_INDICATORS",     "ABS,QBIS",     "all", "1990",
        "business_indicators_quarterly"),
    ("AUS_CAPEX",              "ABS,CAPEX",    "all", "1990",
        "private_new_capital_expenditure"),

    # ── Group 3: Housing ────────────────────────────────────────────────────
    ("AUS_BUILDING_APPROVALS", "ABS,BA_GCCSA", "all", "2021",
        "building_approvals_monthly"),
    ("AUS_BUILDING_ACTIVITY",  "ABS,BUILDING_ACTIVITY","all", "1990",
        "building_activity_quarterly"),
    ("AUS_LENDING_INDICATORS", "ABS,LEND_HOUSING", "all", "2002",
        "lending_indicators_monthly"),
    ("AUS_RES_PROPERTY_PRICE", "ABS,RPPI",     "all", "2003",
        "residential_property_price_indexes"),

    # ── Group 11/12: Household & Non-household balance sheets ───────────────
    ("AUS_FINANCIAL_ACCOUNTS", "ABS,ANA_AGG",  "all", "1988",
        "financial_accounts_quarterly"),

    # ── International trade & balance of payments ───────────────────────────
    ("AUS_BOP",                "ABS,BOP",      "all", "1959",
        "balance_of_payments_quarterly"),
    ("AUS_MERCH_TRADE",        "ABS,ITGS", "all", "1990",
        "international_merchandise_trade"),
]


def main():
    manifest = load_manifest()
    ok_rba, fail_rba = [], []
    ok_abs, fail_abs = [], []

    print(f"\nAUS ingest — {len(RBA_SERIES)} RBA + {len(ABS_SERIES)} ABS series")
    print("-" * 60)
    print("\n[RBA]")

    for local_id, table, sid, label in RBA_SERIES:
        print(f"  {local_id:15} {table:5} {sid:14} ...", end=" ", flush=True)
        df = rba.fetch_series(table, sid)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if df is None or df.empty:
            fail_rba.append(local_id)
            manifest["series"][local_id] = {
                "last_updated": now, "rows": 0, "start": None, "end": None,
                "source": f"rba:{table}:{sid}", "status": "ERROR",
            }
            print("FAILED")
        else:
            ok_rba.append(local_id)
            manifest["series"][local_id] = {
                "last_updated": now, "rows": len(df),
                "start": df["date"].iloc[0], "end": df["date"].iloc[-1],
                "source": f"rba:{table}:{sid}", "status": "OK",
            }
            print(f"OK  ({len(df):,} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]})")

    print("\n[ABS]")
    for local_id, flow_ref, key, start, label in ABS_SERIES:
        print(f"  {local_id:20} {flow_ref:20} ...", end=" ", flush=True)
        df = abs_mod.fetch(flow_ref, key, start_period=start, label=label)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if df is None or df.empty:
            fail_abs.append(local_id)
            manifest["series"][local_id] = {
                "last_updated": now, "rows": 0, "start": None, "end": None,
                "source": f"abs:{flow_ref}", "status": "ERROR",
            }
            print("FAILED")
        else:
            ok_abs.append(local_id)
            manifest["series"][local_id] = {
                "last_updated": now, "rows": len(df),
                "start": None, "end": None,
                "source": f"abs:{flow_ref}",
                "columns": list(df.columns)[:20],
                "status": "OK",
            }
            print(f"OK  ({len(df):,} rows, {df.shape[1]} cols)")

    manifest["last_full_update"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_manifest(manifest)

    # Summary
    print(f"\n{'-' * 60}")
    print(f"  RBA downloaded : {len(ok_rba)}/{len(RBA_SERIES)}")
    if fail_rba:
        print(f"  RBA failed     : {', '.join(fail_rba)}")
    print(f"  ABS downloaded : {len(ok_abs)}/{len(ABS_SERIES)}")
    if fail_abs:
        print(f"  ABS failed     : {', '.join(fail_abs)}")
    print(f"  Manifest       : {MANIFEST_PATH}")
    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main()
