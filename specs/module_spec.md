# Module Specification: data-store
# Version: 1.0
# Created: 2026-04-03
# Status: ACTIVE — Shared module, not a project

## Purpose
Single source of truth for all financial time series used across
the macro-signal-system and any future projects.

Owns the data. All other modules read from it. None write to it.
Keeps raw originals, processed series, and all definitions.
Updates automatically on a weekly schedule.

## Design Principles
- One module owns the data. No other module fetches live data.
- Raw data preserved permanently — never overwritten, only appended.
- Processed files regenerated from raw on each update.
- Definitions drive everything — series, sources, transforms, frequencies.
- Failures are logged and flagged but never silent.
- Every series is versioned: you can reconstruct any past state.

---

## Storage Architecture

### Why Parquet
- Native pandas read/write — no translation overhead
- Compressed: 50 years of daily data across 20 assets ≈ 3–5 MB
- Supports metadata columns and dtypes natively
- Fast columnar reads — load one series without reading all
- Standard format: any Python tool reads it

### Why JSON for manifest
- Human readable — you can open it and understand it
- Machine readable — Claude can update it programmatically
- Lightweight — just metadata, not data

### Why flat files over SQLite/database
- No server, no setup, no connection management
- Works natively with GitHub (text diffs on JSON)
- Parquet is faster than SQLite for time series reads
- Simple enough that Claude can maintain it without a DBA

---

## Folder Structure

```
~/ClaudeWorkspace/data-store/
  CLAUDE.md               ← module instructions
  CHANGELOG.md            ← update history
  status.md               ← current state
  specs/
    module_spec.md        ← this file
    series_definitions.json ← THE master definitions file
  pipeline/
    update_all.py         ← master update script
    ingest/
      fred_ingest.py      ← US macro data
      rba_ingest.py       ← Australian central bank data
      yfinance_ingest.py  ← equities, FX, commodities
      abs_ingest.py       ← Australian Bureau of Statistics
    validate.py           ← data quality checks
    transform.py          ← return calculations, alignment
  store/
    raw/                  ← downloaded originals, never modified
      fred/               ← one CSV per series, timestamped
      rba/                ← RBA table downloads
      yfinance/           ← price downloads
      abs/                ← ABS release downloads
    processed/            ← aligned, cleaned, return-transformed
      daily.parquet       ← all daily series, business day calendar
      monthly.parquet     ← all monthly series, month-end
      quarterly.parquet   ← all quarterly series
    manifest.json         ← current state of all series
    update_log.md         ← human-readable run history
  tests/
    test_integrity.py     ← run after every update
```

---

## series_definitions.json — The Master File

This is the single file that defines everything.
Claude never changes series without updating this file first.

Structure per series:
```json
{
  "series_id": "UST10Y",
  "label": "US 10-Year Treasury Yield",
  "asset_class": "fixed_income",
  "source": "fred",
  "source_id": "DGS10",
  "frequency": "daily",
  "units": "percent",
  "start_date": "1962-01-02",
  "transform": "level",
  "return_transform": "diff",
  "update_frequency": "daily",
  "last_updated": "2026-04-03",
  "notes": "Constant maturity. Missing weekends/holidays filled forward max 3 days.",
  "used_by": ["paper_001", "paper_002"]
}
```

Transform values:
- `level`     → store as-is (yields, rates, VIX)
- `log`       → natural log of price
- `log_diff`  → log return (use for equities, FX, commodities)
- `diff`      → first difference (use for yields, spreads)
- `pct_change`→ percentage change

Return transform values (used when signals need returns):
- `log_diff`  → ln(P_t / P_{t-1})
- `diff`      → P_t - P_{t-1}
- `excess`    → log_diff minus risk-free rate

---

## Manifest.json — Current State

Updated after every run. Tracks what exists and when it was last touched.

```json
{
  "last_full_update": "2026-04-03T05:00:00",
  "series": {
    "UST10Y": {
      "last_updated": "2026-04-03",
      "rows": 16234,
      "start": "1962-01-02",
      "end": "2026-04-02",
      "gaps": 0,
      "status": "OK"
    },
    "AGB10Y": {
      "last_updated": "2026-04-03",
      "rows": 8901,
      "start": "1992-01-03",
      "end": "2026-04-02",
      "gaps": 2,
      "status": "WARNING — 2 gaps > 5 days, see update_log"
    }
  }
}
```

---

## Update Protocol

### Weekly Sunday 5am AEST (off-peak)
The scheduled task runs update_all.py which:
1. Reads series_definitions.json — what needs updating?
2. For each series: fetch latest from source, append to raw/
3. Validate: check for gaps, outliers, revision flags
4. Regenerate processed/ parquet files from raw/
5. Update manifest.json with new timestamps and row counts
6. Write update_log.md entry
7. Git commit: "DATA: weekly update YYYY-MM-DD"

### On-demand updates
Any time new data is needed for a paper:
- Claude checks manifest.json first
- If series exists and is fresh (< 8 days old): use it
- If missing or stale: run targeted update for that series only
- Update manifest.json and log

### Failure handling
- One series fails: log it, continue with others, flag in manifest
- Source API down: log it, use last known good data, flag in status.md
- New series added: run targeted fetch, add to manifest
- Never abort the whole update for one failure

---

## Data Quality Rules

Applied in validate.py after every fetch:

1. GAP CHECK: Flag any gaps > 5 consecutive business days
2. OUTLIER CHECK: Flag returns > 5 standard deviations from rolling mean
3. REVISION CHECK: Compare last 30 rows of new fetch to stored — flag if > 0.1% change
4. RANGE CHECK: Prices must be positive. Yields must be between -2% and 25%.
5. ALIGNMENT: All processed/ files use same business day calendar (NYSE)

Validation failures go to update_log.md and manifest.json status field.
They do not stop the update. They flag for owner review.

---

## How Other Modules Use This

```python
# In any signal module — this is the ONLY way to get data
import pandas as pd
import json

STORE_PATH = Path.home() / "ClaudeWorkspace/data-store/store"

def load_series(series_ids: list, frequency: str = "monthly") -> pd.DataFrame:
    """Load requested series from processed store."""
    freq_map = {"daily": "daily", "monthly": "monthly", "quarterly": "quarterly"}
    path = STORE_PATH / "processed" / f"{freq_map[frequency]}.parquet"
    df = pd.read_parquet(path, columns=series_ids)
    return df

def get_manifest() -> dict:
    """Check what data is available and when it was last updated."""
    with open(STORE_PATH / "manifest.json") as f:
        return json.load(f)
```

No signal module ever touches raw/, calls an API, or modifies manifest.json.

---

## Session Start Protocol

Every time Claude works on data-store:
1. Read specs/series_definitions.json — what is defined?
2. Read store/manifest.json — what exists and when was it updated?
3. Read store/update_log.md — what happened last time?
4. Read CHANGELOG.md
5. Confirm plan before starting

---

## Adding a New Series

When a new paper requires data not in the store:
1. Add entry to series_definitions.json
2. Run targeted fetch for new series only
3. Add to appropriate processed/ parquet files
4. Update manifest.json
5. Add to used_by field of existing series if needed
6. Git commit: "DATA: add series [ID] for paper_NNN"

---

## Scheduled Tasks

1. Weekly update — Sunday 5am AEST
   Prompt: "Read data-store/specs/series_definitions.json.
   Run pipeline/update_all.py. Update all series that are
   > 7 days old. Validate, regenerate processed files,
   update manifest.json, write update_log entry. Commit to git."

2. Pre-paper check — runs at start of each paper session
   Prompt: "Check data-store/store/manifest.json for series
   required by [paper_NNN]. Flag any missing or stale series.
   Run targeted update if needed before signal work begins."

---

## Success Criteria
- All 20 core series updating without errors weekly
- No signal session requires live data fetching
- Manifest accurately reflects current state
- update_log provides clear audit trail
- Any series can be reconstructed from raw/ at any point in time
