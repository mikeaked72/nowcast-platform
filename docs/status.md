# Project Status

Codex updates this file after each coherent unit of work.

## Current State

The repository now blends two layers:

- Existing nowcast platform: `nowcast/`, `country_packs/`, `site/`, generated static files under `site/data/`, and tests for the output contract.
- New G10 DynamicFactorMQ direction: `docs/spec.md`, `docs/plan.md`, `config/`, `prompts/`, and initial `nowcast/g10/` data/model scaffolding. The imported spec uses the standalone-package name `g10nowcast` in examples; in this blended repository, production code lives under `nowcast/g10/`.

The website-facing US GDP output remains the component bridge model for now. The new G10 work is scaffolded alongside it and does not yet replace the published site model.

## What Changed Last

- Implemented the first US G10 data vertical and smoke model path:
  - immutable raw storage helpers under `nowcast/g10/raw_store.py`
  - FRED-MD/FRED-QD public vintage URL and download helpers
  - US vintage assembly from raw FRED-MD/QD CSVs into `data/vintages/US/<date>.parquet`
  - sidecar vintage manifests with source paths, row counts, and monthly/quarterly series counts
  - processed panel builder that applies FRED tcode transformations and writes monthly/quarterly matrices
  - CLI command `python -m nowcast.cli g10-assemble-us --vintage-date YYYY-MM-DD`
- Added offline FRED-MD/QD fixtures for two US vintages.
- Added config-to-vintage coverage checks for configured US targets and panel series.
- Added a DFM processed-panel fit entrypoint and smoke artifact writer that run when `statsmodels` is installed and cleanly report missing dependency otherwise.
- Added a G10 experimental GDP publish path:
  - indicator code `gdp_experimental` in the US country pack
  - CLI command `python -m nowcast.cli g10-publish-experimental --iso US --vintage-date YYYY-MM-DD`
  - deterministic GDP proxy from the processed panel, currently preferring transformed `GDPC1`
  - source-level release-impact rows from the largest monthly/quarterly panel movers
  - optional provenance artifacts listed in `metadata.json`
- Improved the dashboard to label G10 outputs as experimental, group comparison impacts, and show optional G10 provenance without failing when optional diagnostics are absent or malformed.
- Expanded the US G10 fixture panel to 25 series:
  - 20 monthly FRED-MD-style series covering production, income, labour, prices, wages, financial, external, housing, and sentiment inputs
  - 5 quarterly FRED-QD-style targets covering GDP, investment, profits, imports, and exports
  - current fixture coverage ratio is 100% against the seed US config
- Repaired the live FRED-MD/FRED-QD URL path:
  - current downloads now discover the St. Louis Fed index-page CSV targets when possible
  - explicit vintage downloads use the current `YYYY-MM-md.csv` / `YYYY-MM-qd.csv` media paths
  - raw downloads retry with a clearer `RawFetchError` instead of surfacing a low-level timeout trace
  - `g10-assemble-us` and `g10-run-experimental-us` accept `--download-timeout` and `--download-retries`

## Validation Status

Latest validation should include:

- `python -m py_compile nowcast\g10\assemble.py nowcast\g10\panel.py nowcast\g10\coverage.py nowcast\g10\dfm.py nowcast\g10\smoke.py nowcast\cli.py`
- `python -m py_compile nowcast\publish.py nowcast\g10\experimental_publish.py nowcast\cli.py`
- `python scripts\validate_outputs.py --countries us,au,de,br --publish-dir site\data`
- `python -m pytest -q --basetemp tmp\pytest`
- `make test-vintage`
- `make test-replay-smoke`
- `python -m nowcast.cli g10-dfm-smoke --iso US --vintage-date 2026-04-01 --processed-root <processed-root> --artifact-root <artifact-root> --maxiter 2`
- `python -m nowcast.cli g10-publish-experimental --iso US --vintage-date 2026-04-01 --processed-root <processed-root> --vintage-root <vintage-root> --artifact-root <artifact-root> --publish-dir <site-data-root>`
- `python -m nowcast.cli g10-check-coverage --iso US --vintage-date 2026-04-01 --vintage-root <vintage-root> --matrix-output <coverage.csv>`

## Current Risks

- `statsmodels` and `PyYAML` are declared dependencies, but the local venv may need dependency installation before running the full G10 config/model path.
- The G10 daily/replay/refit commands are scaffolded but intentionally not implemented.
- The existing US component bridge is still the website-backed US GDP model until the DFM replay path is proven.
- The `gdp_experimental` estimate is a development proxy, not a production GDPNow-equivalent DFM extraction.
- The fixture coverage check now covers all configured US targets and seed panel series; the values are synthetic fixture data for plumbing, not live FRED observations.
- Live FRED-MD/FRED-QD access from this Windows environment timed out against the official St. Louis Fed host on 2026-04-17, including escalated direct dated-vintage attempts. The downloader now fails clearly, but a successful live pull still needs to be verified from a network path that can reach the host.
- Non-US G10 vintage construction remains the largest engineering risk.

## Next Steps

1. Add an end-to-end convenience command that assembles, smokes, publishes, and validates `gdp_experimental`.
2. Re-test live `g10-assemble-us --download --vintage-month 2026-03 --download-timeout 180` from a network path that can reach St. Louis Fed CSV media URLs, then inspect row counts.
3. Promote the single-vintage experimental output into a replay artifact with vintage-to-vintage news deltas.
4. Add a live-source bypass or alternate mirror strategy if St. Louis Fed CSV access remains unavailable from the runtime network.
