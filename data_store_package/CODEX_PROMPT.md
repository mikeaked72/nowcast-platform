# Codex Task: Complete the Macro Data Store

## Context

This repo contains a multi-country macroeconomic data pipeline. The goal is a harmonised cross-country panel modelled on the McCracken-Ng FRED-MD/QD framework (~248 US series) with equivalents for 13 additional jurisdictions.

**What's done:** US (FRED, 27 series) and Australia (RBA, 38 files) are downloaded and working. A processed parquet layer exists combining these two.

**What's not done:** 13 international ingestors are written but have NEVER been run. They may have bugs, wrong API endpoints, format parsing errors, or missing error handling. Your job is to get every one of them working and downloading data.

## Step-by-Step Instructions

### Phase 1: Verify repo structure and dependencies

1. Read `README.md` to understand the project layout.
2. Run `pip install -r requirements.txt` to install dependencies.
3. Source the `.env` file: `source .env` (contains the FRED API key).
4. Verify the FRED ingestor still works: `cd pipeline/ingest && python fred_ingest.py`. It should download 27 series to `../../store/raw/fred/`. If it works, Phase 1 US data is confirmed.
5. Verify the RBA ingestor: `python rba_ingest.py`. Should download CSV files to `../../store/raw/rba/`.

### Phase 2: Run and fix Australian ingestors

6. Run `python abs_ingest.py`. This uses the ABS SDMX API at `https://data.api.abs.gov.au/`. It should download Australian macro series (GDP, CPI, labour force, trade, housing) to `../../store/raw/abs/`.
7. If it fails, debug the issue. Common problems:
   - Accept header format: use `application/vnd.sdmx.data+csv;file=true;version=1.0.0` with fallback to XML
   - Series IDs may have changed — check against `specs/fred_qd_to_abs_mapping.md`
   - Rate limiting — add 1-second delays between requests
8. Log what was downloaded: series count, row counts, date range coverage.

### Phase 3: Run and fix all international ingestors

Run each ingestor in this priority order. For EACH one:
- Run the script
- If it fails, read the error, fix the script, re-run
- Log: source name, series downloaded, rows, date range, any issues fixed
- Create the output directory under `store/raw/{source}/` if it doesn't exist

**Priority order:**

| # | Script | Source | API Base URL | Expected output |
|---|--------|--------|-------------|-----------------|
| 1 | `ecb_ingest.py` | ECB Data Portal | `https://data-api.ecb.europa.eu/service/data/` | Euro area rates, money supply, credit, inflation |
| 2 | `eurostat_ingest.py` | Eurostat | `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/` | EU GDP, HICP, unemployment, industrial production |
| 3 | `ons_ingest.py` | UK ONS + BoE | `https://api.ons.gov.uk/` + BoE IADB | UK GDP, CPI, labour, rates |
| 4 | `imf_ingest.py` | IMF IFS/DOT | `http://dataservices.imf.org/REST/SDMX_JSON.svc/` | Global macro indicators, fallback source |
| 5 | `worldbank_ingest.py` | World Bank | `https://api.worldbank.org/v2/` | Development indicators, GDP, population |
| 6 | `statcan_ingest.py` | Statistics Canada | `https://www150.statcan.gc.ca/t1/tbl1/en/` | Canadian GDP, CPI, labour, rates |
| 7 | `bundesbank_ingest.py` | Deutsche Bundesbank | `https://api.statistiken.bundesbank.de/rest/data/` | German rates, money, credit |
| 8 | `boj_ingest.py` | Bank of Japan | `https://www.stat-search.boj.or.jp/ssi/` | Japanese rates, money supply |
| 9 | `estat_ingest.py` | Japan e-Stat | `https://api.e-stat.go.jp/rest/3.0/app/json/` | Japanese GDP, CPI, labour (needs API key) |
| 10 | `insee_ingest.py` | INSEE France | `https://api.insee.fr/series/BDM/V1/` | French GDP, CPI, labour |
| 11 | `bdf_ingest.py` | Banque de France | `https://api.webstat.banque-france.fr/webstat-fr/v1/` | French financial series |
| 12 | `destatis_ingest.py` | DESTATIS Germany | `https://www-genesis.destatis.de/genesisWS/rest/2020/` | German real economy (needs API key) |

**Common issues across ingestors:**
- Wrong Accept headers for SDMX APIs — try both CSV and XML formats
- API endpoint changes — check the current documentation
- Rate limiting — add `time.sleep(1)` between requests
- SSL certificate issues — try `verify=False` as last resort
- Response format changes — some APIs return JSON, some XML, some CSV
- Empty responses — check if the series ID/flow ref is correct
- The `.env` file must be sourced for FRED_API_KEY to be available

### Phase 4: Build the processed layer

9. Once all raw data is downloaded, run `python pipeline/build_processed.py`.
10. This should merge all raw CSVs into harmonised parquet files:
    - `store/processed/daily.parquet` — daily frequency series (rates, FX, yields)
    - `store/processed/monthly.parquet` — monthly frequency series (CPI, production, employment)
    - `store/processed/quarterly.parquet` — quarterly series (GDP, balance of payments)
11. If `build_processed.py` doesn't handle the new international series yet, extend it to include them. The output should have columns named by ISO country code + concept (e.g., `AUS_CPI`, `GBR_GDP`, `DEU_INDPRO`).

### Phase 5: Validate and document

12. Run a validation pass:
    - For each country, check that at least the core series exist: GDP (or proxy), CPI, unemployment rate, policy rate, exchange rate
    - Print a coverage matrix: countries × concept groups, showing which cells have data
    - Flag any series with suspiciously short date ranges or all-NaN values
13. Update `store/manifest.json` with download timestamps and series counts per source.
14. Update `README.md` status table with actual results.
15. Commit all changes with a descriptive message.

### Phase 6: Quality and robustness

16. Add retry logic (3 attempts with exponential backoff) to any ingestor that doesn't have it.
17. Add a `--dry-run` flag to each ingestor that validates the API connection without downloading.
18. Ensure each ingestor can be run independently: `python pipeline/ingest/ecb_ingest.py` should work without importing from other modules.
19. Add logging (Python `logging` module) to each ingestor — INFO for successful downloads, WARNING for retries, ERROR for failures.

## End State

When complete, the repo should:
- Download ~1,280 series across 13+ countries with a single command (`python pipeline/update_international.py`)
- Produce harmonised parquet files aligned to the FRED-MD/QD framework
- Be runnable on a weekly schedule (every Monday) to refresh data
- Have clear logging of what succeeded and what failed
- Be documented well enough that a new user can set up and run it

## Key Files to Reference

- `specs/macro_data_mapping.md` — the master mapping of what series to download per country
- `specs/series_definitions.json` — machine-readable series catalog
- `specs/release_timing.md` — which source to prefer when multiple sources cover the same concept
- `specs/fred_qd_to_abs_mapping.md` — detailed US-to-Australia mapping
- `specs/module_spec.md` — technical spec for how ingestor modules should be structured
