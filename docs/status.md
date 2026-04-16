# Project Status

Codex updates this file after each coherent unit of work.

## Current State

The repository now blends two layers:

- Existing nowcast platform: `nowcast/`, `country_packs/`, `site/`, generated static files under `site/data/`, and tests for the output contract.
- New G10 DynamicFactorMQ direction: `docs/spec.md`, `docs/plan.md`, `config/`, `prompts/`, and initial `nowcast/g10/` data/model scaffolding. The imported spec uses the standalone-package name `g10nowcast` in examples; in this blended repository, production code lives under `nowcast/g10/`.

The website-facing US GDP output remains the component bridge model for now. The new G10 work is scaffolded alongside it and does not yet replace the published site model.

## What Changed Last

- Implemented the first US G10 data vertical:
  - immutable raw storage helpers under `nowcast/g10/raw_store.py`
  - FRED-MD/FRED-QD public vintage URL and download helpers
  - US vintage assembly from raw FRED-MD/QD CSVs into `data/vintages/US/<date>.parquet`
  - processed panel builder that applies FRED tcode transformations and writes monthly/quarterly matrices
  - CLI command `python -m nowcast.cli g10-assemble-us --vintage-date YYYY-MM-DD`
- Added offline FRED-MD/QD fixtures for two US vintages.
- Added a DFM processed-panel fit entrypoint that runs when `statsmodels` is installed and cleanly reports missing dependency otherwise.
- Added a DFM-to-site adapter scaffold so future DFM outputs can flow through the existing `ModelRun` publisher boundary.

## Validation Status

Latest validation should include:

- `python -m py_compile nowcast\g10\transforms.py nowcast\g10\vintage.py nowcast\g10\fred_md.py nowcast\g10\dfm.py nowcast\g10\config.py nowcast\cli.py`
- `python scripts\validate_outputs.py --countries us,au,de,br --publish-dir site\data`
- `python -m pytest -q --basetemp tmp\pytest`
- `make test-vintage`
- `make test-replay-smoke`

## Current Risks

- `statsmodels` and `PyYAML` are declared dependencies, but the local venv may need dependency installation before running the full G10 config/model path.
- The G10 daily/replay/refit commands are scaffolded but intentionally not implemented.
- The existing US component bridge is still the website-backed US GDP model until the DFM replay path is proven.
- Non-US G10 vintage construction remains the largest engineering risk.

## Next Steps

1. Install declared G10 dependencies in the local venv and run `python -m nowcast.cli g10-check-config --iso US`.
2. Run a live `g10-assemble-us --download` for the latest FRED-MD/QD current vintage and inspect row counts.
3. Expand the US country YAML toward the full FRED-MD/FRED-QD panel.
4. Implement M2 smoke fitting against a pinned vintage once the real panel is available.
