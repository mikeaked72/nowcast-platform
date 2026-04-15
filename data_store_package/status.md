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

As of the expanded integrated run on 2026-04-15:

- FRED: 27/27 series downloaded.
- RBA: 28/28 series downloaded.
- ABS: 19/19 configured dataflows downloaded after remapping current ABS
  dataflow IDs through the live catalogue.
- UK ONS: 9/9 public time-series routes downloaded.
- Eurostat: euro-area aggregates plus national GDP, trade, unemployment, HICP,
  and PPI panels for DEU, FRA, ITA, ESP, NLD, BEL, AUT, PRT, IRL, FIN, SWE,
  DNK, NOR, and CHE.
- IMF: migrated from the retired/refused `dataservices.imf.org` route to the
  current SDMX 2.1 endpoint. Monthly CPI index and CPI percent-change panels now
  download for 21 emerging-market and G20-style country codes.
- Bundesbank: German government yield keys were repaired against the current
  BBSIS term-structure flow. Household and NFC credit keys still need a current
  catalogue match.
- Banque de France: the ingestor now uses structured logging and skips cleanly
  without credentials. Set `BDF_CLIENT_ID` and `BDF_CLIENT_SECRET` to enable the
  authenticated API.
- BoJ: the legacy API keys are still unresolved, but current public flat-file
  discovery works for the CGPI package.
- International public sources: 179 series downloaded and 27 failures recorded
  without aborting the run.
- Processed layer: daily, weekly, monthly, quarterly, and annual parquet files
  build successfully from available raw data.
- Latest processed dimensions: daily 18,730 x 28; weekly 3,092 x 1; monthly
  2,424 x 148; quarterly 206 x 63; annual 36 x 437.

## Known Follow-Ups

- Finish IMF SDMX 2.1 dimension maps for rates, FX, unemployment, GDP, and
  broad-money series beyond CPI.
- Find current Bundesbank credit-series keys for household and NFC lending.
- Replace legacy BoJ API codes with current API or flat-file packages for money,
  policy-rate, and balance-sheet concepts.
- Provide Banque de France API credentials if authenticated French financial
  series are required.
- Extend the shared `--dry-run`, retry/backoff, and structured logging helper
  to any lower-priority ingestors that still use their original direct request
  loops.
