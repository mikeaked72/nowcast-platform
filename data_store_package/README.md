# Macro Data Store

Multi-country macroeconomic data pipeline for signal research. Builds a harmonised cross-country panel modelled on the McCracken-Ng FRED-MD/QD framework (134 monthly + 114 quarterly US series) with equivalents for 13 additional jurisdictions.

## Project Status

| Source | Country | Ingestor | Data | Status |
|--------|---------|----------|------|--------|
| FRED | US | `fred_ingest.py` | 27 series, 177K rows | DONE |
| RBA | Australia | `rba_ingest.py` | 28 configured series | DONE |
| ABS | Australia | `abs_ingest.py` | 19 configured dataflows | DONE after live catalogue remap |
| ECB | Euro Area | `ecb_ingest.py` | policy rates, FX, HICP, GDP, credit | DONE |
| Eurostat | Europe | `eurostat_ingest.py` | GDP, trade, HICP, PPI, unemployment | DONE for core European panel |
| Bundesbank | Germany | `bundesbank_ingest.py` | 2y/5y/10y/30y yields | DONE for yield curve; credit keys pending |
| INSEE | France | `insee_ingest.py` | 0 series | Script written, never run |
| BdF | France | `bdf_ingest.py` | 0 public series | Requires `BDF_CLIENT_ID`/`BDF_CLIENT_SECRET` |
| DESTATIS | Germany | `destatis_ingest.py` | 0 series | Script written, never run |
| ONS + BoE | UK | `ons_ingest.py` | ONS public routes + BoE rates, 5y/10y/20y yield curve | PARTIAL: 2y/30y curve keys pending |
| StatCan | Canada | `statcan_ingest.py` | CPI, unemployment, rates, yields | DONE |
| BoJ | Japan | `boj_ingest.py` | CGPI and current account flat-file series | PARTIAL: legacy API keys pending |
| e-Stat | Japan | `estat_ingest.py` | 0 series | Script written, never run |
| IMF | Global | `imf_ingest.py` | CPI and CPI percent-change panels | DONE for CPI; other concepts in discovery |
| World Bank | Global | `worldbank_ingest.py` | structural annual indicators | DONE |

**Processed layer:** daily, weekly, monthly, quarterly, and annual parquet panels build from the available raw data. Latest dimensions are daily 18,730 x 30; weekly 3,092 x 1; monthly 2,424 x 154; quarterly 206 x 63; annual 36 x 437.

## Directory Structure

```
data-store/
  .env                          # API keys (FRED, etc.) - DO NOT COMMIT
  .gitignore
  requirements.txt
  pipeline/
    ingest/                     # 15 country-specific ingestor scripts
      fred_ingest.py            # US Federal Reserve Economic Data
      rba_ingest.py             # Reserve Bank of Australia
      abs_ingest.py             # Australian Bureau of Statistics (SDMX)
      ecb_ingest.py             # European Central Bank
      eurostat_ingest.py        # Eurostat (SDMX)
      bundesbank_ingest.py      # Deutsche Bundesbank
      insee_ingest.py           # INSEE France
      bdf_ingest.py             # Banque de France
      destatis_ingest.py        # German Federal Statistical Office
      ons_ingest.py             # UK ONS + Bank of England IADB
      statcan_ingest.py         # Statistics Canada
      boj_ingest.py             # Bank of Japan
      estat_ingest.py           # Japan e-Stat
      imf_ingest.py             # International Monetary Fund
      worldbank_ingest.py       # World Bank
    update_fred.py              # Orchestrator: run FRED update
    update_aus.py               # Orchestrator: run RBA + ABS
    update_international.py     # Orchestrator: run all international
    build_processed.py          # Merge raw CSVs into processed parquet
    scan_rba_ids.py             # Utility: scan RBA table IDs
  specs/
    macro_data_mapping.md       # Master mapping: FRED-MD/QD -> each country
    series_definitions.json     # Machine-readable series catalog
    release_timing.md           # Source priority by timeliness
    fred_qd_to_abs_mapping.md   # Detailed US-AUS mapping
    module_spec.md              # Technical spec for ingestor modules
    data_expansion_plan.md      # Roadmap for additional series
  store/
    raw/                        # Raw downloads by source
      fred/                     # 27 CSV files (DONE)
      rba/                      # 38 CSV files (DONE)
      abs/                      # ABS SDMX downloads
      ecb/                      # ECB Data Portal downloads
    processed/
      daily.parquet             # Harmonised daily panel
      weekly.parquet            # Harmonised weekly panel
      monthly.parquet           # Harmonised monthly panel
      quarterly.parquet         # Harmonised quarterly panel
      annual.parquet            # Harmonised annual panel
    manifest.json               # What's been downloaded and when
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your FRED API key (free from fred.stlouisfed.org)
source .env
```

## Running

```bash
# US data (already done)
python pipeline/update_fred.py

# Australia
python pipeline/update_aus.py

# All international sources
python pipeline/update_international.py

# Rebuild processed parquet from raw
python pipeline/build_processed.py

# Individual ingestors (for debugging)
cd pipeline/ingest
python abs_ingest.py
python ecb_ingest.py
# etc.
```

## API Requirements

| Source | Auth | Notes |
|--------|------|-------|
| FRED | API key required | Free from fred.stlouisfed.org/docs/api/api_key.html |
| RBA | None | Public CSV tables |
| ABS | None | SDMX API, no auth since Nov 2024 |
| ECB | None | ECB Data Portal, public |
| Eurostat | None | SDMX REST, public |
| Bundesbank | None | Public API |
| ONS | None | Public API |
| BoE | None | IADB public |
| IMF | None | IFS/DOT public |
| World Bank | None | Public indicators API |
| StatCan | None | CODR public |
| BoJ | None | Public time series |
| e-Stat | API key (free) | estat.go.jp |
| INSEE | None | BDM public |
| DESTATIS | API key (free) | destatis.de |

## Target End State

A harmonised panel covering ~1,280 series across 13+ countries, automatically refreshable on a weekly schedule. The panel mirrors the FRED-MD/QD structure so that any signal research built on US data can be immediately tested cross-country.
