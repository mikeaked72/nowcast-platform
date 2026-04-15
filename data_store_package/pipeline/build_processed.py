"""
build_processed.py — Build aligned parquet files from raw CSVs.

Reads everything under store/raw/ and produces:
    store/processed/daily.parquet     — all daily series, business day calendar
    store/processed/monthly.parquet   — all monthly series, month-end
    store/processed/quarterly.parquet — all quarterly series

Usage: python data-store/pipeline/build_processed.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict

import pandas as pd


# ── paths ─────────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent
STORE = HERE.parent / "store"
RAW = STORE / "raw"
PROCESSED = STORE / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = STORE / "manifest.json"
DEFINITIONS_PATH = HERE.parent / "specs" / "series_definitions.json"


# ── loaders ───────────────────────────────────────────────────────────────────

def load_fred_series(series_id: str) -> pd.Series | None:
    """Load a FRED series from raw/fred/{id}.csv as a date-indexed Series."""
    path = RAW / "fred" / f"{series_id}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns or "value" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].rename(series_id)


def load_rba_series(table: str, sid: str, local_id: str) -> pd.Series | None:
    """Load an RBA series from raw/rba/{table}_{sid}.csv."""
    path = RAW / "rba" / f"{table.lower()}_{sid}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns or "value" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].rename(local_id)


def load_abs_series(filename_stem: str, local_id: str) -> pd.Series | None:
    """Load a simple ABS series from raw/abs/. Assumes SDMX-CSV format with
    TIME_PERIOD and OBS_VALUE columns."""
    path = RAW / "abs" / f"{filename_stem}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    # SDMX-CSV typically has TIME_PERIOD and OBS_VALUE
    date_col = next((c for c in df.columns if c.upper() in ("TIME_PERIOD", "DATE")), None)
    val_col = next((c for c in df.columns if c.upper() in ("OBS_VALUE", "VALUE")), None)
    if date_col is None or val_col is None:
        return None
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).reset_index(drop=True)
    # If the dataflow has multiple series stacked, aggregate or pick the first
    # For now, keep the mean of values at each date as a simple flattening
    grp = df.groupby(date_col)[val_col].mean()
    return grp.rename(local_id)


# ── assembly ──────────────────────────────────────────────────────────────────

# Frequency mapping for known series
FRED_FREQS = {
    # Daily
    "DFF": "daily", "DGS1": "daily", "DGS2": "daily", "DGS5": "daily",
    "DGS10": "daily", "DGS30": "daily", "T10Y2Y": "daily",
    "BAMLC0A0CM": "daily", "BAMLH0A0HYM2": "daily", "DBAA": "daily",
    "DTWEXBGS": "daily", "DEXUSEU": "daily", "DEXJPUS": "daily",
    # Weekly
    "ICSA": "weekly",
    # Monthly
    "FEDFUNDS": "monthly", "INDPRO": "monthly", "UNRATE": "monthly",
    "PAYEMS": "monthly", "CPIAUCSL": "monthly", "PCEPILFE": "monthly",
    "PPIACO": "monthly", "RSAFS": "monthly", "UMCSENT": "monthly",
    "HOUST": "monthly", "PERMIT": "monthly", "M2SL": "monthly",
    "JLNUM12M": "monthly",
}

RBA_CATALOG = [
    # (table, series_id, local_id, freq)
    ("f1",   "FIRMMCRTD",   "AUS_CASHRATE",    "daily"),
    ("f1.1", "FIRMMBAB30",  "AUS_BBSW30",      "monthly"),
    ("f1.1", "FIRMMBAB90",  "AUS_BBSW90",      "monthly"),
    ("f2",   "FCMYGBAG2D",  "AGB2Y",           "monthly"),
    ("f2",   "FCMYGBAG3D",  "AGB3Y",           "monthly"),
    ("f2",   "FCMYGBAG5D",  "AGB5Y",           "monthly"),
    ("f2",   "FCMYGBAG10D", "AGB10Y",          "monthly"),
    ("f5",   "FILRHLBVS",   "AUS_MORTGAGE",    "monthly"),
    ("f11",  "FXRUSD",      "AUDUSD",          "daily"),
    ("f11",  "FXRTWI",      "AUD_TWI",         "daily"),
    ("d2",   "DLCACOHN",    "AUS_OO_HOUS_CR",  "monthly"),
    ("d2",   "DLCACIHN",    "AUS_INV_HOUS_CR", "monthly"),
    ("d2",   "DLCACOPN",    "AUS_PERS_CR",     "monthly"),
    ("d2",   "DLCACBN",     "AUS_BUS_CR",      "monthly"),
    ("d2",   "DLCACN",      "AUS_TOTAL_CR",    "monthly"),
    ("d3",   "DMAM3N",      "AUS_M3",          "monthly"),
    ("d3",   "DMABMN",      "AUS_BROADMNY",    "monthly"),
    ("d3",   "DMAMMB",      "AUS_MONYBASE",    "monthly"),
    ("i2",   "GRCPBMUSD",   "IRON_ORE",        "monthly"),
    ("i2",   "GRCPBCUSD",   "AUS_COMM_USD",    "monthly"),
    ("i2",   "GRCPBCSDR",   "AUS_COMM_SDR",    "monthly"),
]

ABS_CATALOG = [
    # (filename_stem, local_id, freq)
    ("CPI_all_groups_quarterly", "AUS_CPI", "quarterly"),
    ("labour_force_monthly",     "AUS_UNEMP", "monthly"),
]

ISO2_TO_ISO3 = {
    "AE": "ARE", "AU": "AUS", "BR": "BRA", "CA": "CAN", "CH": "CHE",
    "CL": "CHL", "CN": "CHN", "CO": "COL", "CZ": "CZE", "DE": "DEU",
    "FR": "FRA", "GB": "GBR", "HU": "HUN", "ID": "IDN", "IL": "ISR",
    "IN": "IND", "JP": "JPN", "KR": "KOR", "MX": "MEX", "MY": "MYS",
    "NZ": "NZL", "PE": "PER", "PH": "PHL", "PL": "POL", "RO": "ROU",
    "SA": "SAU", "TH": "THA", "TR": "TUR", "US": "USA", "ZA": "ZAF",
}

RAW_SOURCE_DIRS = {
    "ecb": "ecb",
    "eurostat": "eurostat",
    "statcan": "statcan",
    "boc": "boc",
    "boe": "boe",
    "wb": "worldbank",
    "worldbank": "worldbank",
}


def build():
    daily_series: Dict[str, pd.Series] = {}
    weekly_series: Dict[str, pd.Series] = {}
    monthly_series: Dict[str, pd.Series] = {}
    quarterly_series: Dict[str, pd.Series] = {}
    annual_series: Dict[str, pd.Series] = {}

    def route(s: pd.Series, freq: str, bucket_name: str):
        if s is None or s.empty:
            print(f"  [skip] {bucket_name} (empty)")
            return
        if freq == "daily":
            daily_series[s.name] = s
        elif freq == "weekly":
            weekly_series[s.name] = s
        elif freq == "monthly":
            monthly_series[s.name] = s
        elif freq == "quarterly":
            quarterly_series[s.name] = s
        elif freq == "annual":
            annual_series[s.name] = s
        print(f"  [ok]   {bucket_name} ({freq}, {len(s):,} rows)")

    def parse_time_period(values: pd.Series) -> pd.Series:
        as_text = values.astype(str).str.strip()
        qmask = as_text.str.match(r"^\d{4}-Q[1-4]$")
        out = pd.to_datetime(as_text, errors="coerce")
        if qmask.any():
            quarters = pd.PeriodIndex(as_text[qmask].str.replace("-Q", "Q"), freq="Q")
            out.loc[qmask] = quarters.to_timestamp(how="end").normalize()
        ymask = as_text.str.match(r"^\d{4}$")
        if ymask.any():
            out.loc[ymask] = pd.to_datetime(as_text[ymask] + "-12-31", errors="coerce")
        return out

    def infer_frequency(df: pd.DataFrame, date_col: str) -> str:
        for col in ("FREQ", "freq"):
            if col in df.columns:
                value = str(df[col].dropna().iloc[0]).upper() if not df[col].dropna().empty else ""
                if value.startswith("D"):
                    return "daily"
                if value.startswith("W"):
                    return "weekly"
                if value.startswith("M"):
                    return "monthly"
                if value.startswith("Q"):
                    return "quarterly"
                if value.startswith("A"):
                    return "annual"
        sample = df[date_col].dropna().astype(str).head(20)
        if sample.str.match(r"^\d{4}-Q[1-4]$").any():
            return "quarterly"
        if sample.str.match(r"^\d{4}$").all():
            return "annual"
        parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().sum() >= 2:
            step = parsed.sort_values().diff().dropna().dt.days.median()
            if step <= 3:
                return "daily"
            if step <= 10:
                return "weekly"
            if step <= 45:
                return "monthly"
            if step <= 120:
                return "quarterly"
        return "monthly"

    def value_column(df: pd.DataFrame) -> str | None:
        for col in ("value", "OBS_VALUE"):
            if col in df.columns:
                return col
        for col in df.columns:
            if col.lower() == "date" or col == "TIME_PERIOD":
                continue
            values = pd.to_numeric(df[col], errors="coerce")
            if values.notna().any():
                return col
        return None

    def load_international_series(local_id: str, source: str) -> list[tuple[pd.Series, str]]:
        dirname = RAW_SOURCE_DIRS.get(source)
        if dirname is None:
            return []
        path = RAW / dirname / f"{local_id}.csv"
        if not path.exists():
            return []
        df = pd.read_csv(path, low_memory=False)
        if df.empty:
            return []

        if dirname == "worldbank" and {"date", "value", "country"}.issubset(df.columns):
            suffix = local_id.removeprefix("WB_")
            out: list[tuple[pd.Series, str]] = []
            for country, part in df.groupby("country"):
                iso3 = ISO2_TO_ISO3.get(str(country).upper(), str(country).upper())
                dates = parse_time_period(part["date"])
                values = pd.to_numeric(part["value"], errors="coerce")
                s = pd.Series(values.to_numpy(), index=dates, name=f"{iso3}_{suffix}")
                s = s.dropna().sort_index()
                if not s.empty:
                    out.append((s, "annual"))
            return out

        date_col = "date" if "date" in df.columns else "TIME_PERIOD" if "TIME_PERIOD" in df.columns else None
        val_col = value_column(df)
        if date_col is None or val_col is None:
            return []
        dates = parse_time_period(df[date_col])
        values = pd.to_numeric(df[val_col], errors="coerce")
        s = pd.Series(values.to_numpy(), index=dates, name=local_id).dropna().sort_index()
        if s.empty:
            return []
        return [(s, infer_frequency(df, date_col))]

    print("Loading FRED series...")
    for sid, freq in FRED_FREQS.items():
        s = load_fred_series(sid)
        route(s, freq, sid)

    print("\nLoading RBA series...")
    for table, sid, local_id, freq in RBA_CATALOG:
        s = load_rba_series(table, sid, local_id)
        route(s, freq, local_id)

    print("\nLoading ABS series...")
    for stem, local_id, freq in ABS_CATALOG:
        s = load_abs_series(stem, local_id)
        route(s, freq, local_id)

    print("\nLoading international raw series...")
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        for local_id, info in sorted(manifest.get("series", {}).items()):
            if info.get("status") != "OK":
                continue
            source = str(info.get("source", "")).split(":", 1)[0]
            for s, freq in load_international_series(local_id, source):
                route(s, freq, s.name)

    # Build DataFrames
    def build_df(series_dict, freq_code):
        if not series_dict:
            return pd.DataFrame()
        df = pd.concat(series_dict.values(), axis=1).sort_index()
        return df

    daily_df = build_df(daily_series, "B")
    weekly_df = build_df(weekly_series, "W-FRI")
    monthly_df = build_df(monthly_series, "M")
    quarterly_df = build_df(quarterly_series, "Q")
    annual_df = build_df(annual_series, "A")

    # Forward-fill daily by business day calendar (max 3 days per spec)
    if not daily_df.empty:
        bday_idx = pd.bdate_range(daily_df.index.min(), daily_df.index.max())
        daily_df = daily_df.reindex(bday_idx).ffill(limit=3)

    # Save
    outputs = {
        "daily": daily_df,
        "weekly": weekly_df,
        "monthly": monthly_df,
        "quarterly": quarterly_df,
        "annual": annual_df,
    }
    for name, df in outputs.items():
        if df.empty:
            print(f"  [skip] {name}.parquet (no series)")
            continue
        out_path = PROCESSED / f"{name}.parquet"
        df.to_parquet(out_path)
        print(f"  [save] {out_path} ({df.shape[0]:,} rows x {df.shape[1]:,} cols)")

    manifest = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
    manifest.setdefault("processed", {})
    for name, df in outputs.items():
        manifest["processed"][name] = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "path": f"store/processed/{name}.parquet",
            "start": None if df.empty else df.index.min().strftime("%Y-%m-%d"),
            "end": None if df.empty else df.index.max().strftime("%Y-%m-%d"),
        }
    STORE.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return outputs


if __name__ == "__main__":
    build()
