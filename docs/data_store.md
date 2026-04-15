# Macro Data Store

The macro data store is the source-download and processed-panel layer for the
nowcasting platform. The active code lives in `pipeline/`, source definitions
live in `specs/`, and generated data lives under `store/`.

## Run Order

1. Install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Provide API keys in a local `.env` file. Do not commit this file. FRED needs
   `FRED_API_KEY`; e-Stat, INSEE, and DESTATIS are skipped unless their keys are
   present.

3. Download data:

   ```powershell
   .\.venv\Scripts\python.exe pipeline\update_fred.py
   .\.venv\Scripts\python.exe pipeline\update_aus.py
   .\.venv\Scripts\python.exe pipeline\update_international.py
   ```

4. Build processed panels:

   ```powershell
   .\.venv\Scripts\python.exe pipeline\build_processed.py
   ```

5. Validate coverage:

   ```powershell
   .\.venv\Scripts\python.exe pipeline\validate_data_store.py
   ```

The same sequence can be run with:

```powershell
.\.venv\Scripts\python.exe pipeline\update_all_data.py
```

## Outputs

Raw downloads are written to `store/raw/<source>/` and are ignored by git.
Processed parquet outputs are written to `store/processed/` and are also ignored.
`store/manifest.json` is the lightweight committed status record.

Current processed files:

- `daily.parquet`
- `weekly.parquet`
- `monthly.parquet`
- `quarterly.parquet`
- `annual.parquet`

Column naming follows the source where a series is inherently national, such as
`CAN_CPI`, `UK_BANK_RATE`, or `EA_GDP_REAL`. World Bank structural panels are
expanded to ISO3 concept columns such as `USA_GDP_REAL`, `AUS_EXPORTS_GDP`, and
`DEU_CPI_INFLATION`.

## Current Status

As of the first integrated run on 2026-04-15:

- FRED: 27/27 series downloaded.
- RBA: 28/28 series downloaded.
- ABS: 10/19 dataflows downloaded; the remaining failures are 404 dataflow IDs
  that need catalogue remapping.
- International public sources: 51 series downloaded and 49 failures recorded
  without aborting the run.
- Processed layer: daily, weekly, monthly, quarterly, and annual parquet files
  build successfully from available raw data.

## Known Follow-Ups

- Remap ABS dataflows that now return 404.
- Update ONS, Bundesbank, Banque de France, BoJ, and selected Eurostat series
  keys against their current catalogues.
- Move IMF calls from the refused HTTP endpoint to the current IMF Data API.
- Add per-ingestor `--dry-run` flags and shared retry/logging helpers across all
  source modules.
