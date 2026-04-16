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
- Added a DFM-to-site adapter scaffold so future DFM outputs can flow through the existing `ModelRun` publisher boundary.

## Validation Status

Latest validation should include:

- `python -m py_compile nowcast\g10\assemble.py nowcast\g10\panel.py nowcast\g10\coverage.py nowcast\g10\dfm.py nowcast\g10\smoke.py nowcast\cli.py`
- `python scripts\validate_outputs.py --countries us,au,de,br --publish-dir site\data`
- `python -m pytest -q --basetemp tmp\pytest`
- `make test-vintage`
- `make test-replay-smoke`
- `python -m nowcast.cli g10-dfm-smoke --iso US --vintage-date 2026-04-01 --processed-root <processed-root> --artifact-root <artifact-root> --maxiter 2`

## Current Risks

- `statsmodels` and `PyYAML` are declared dependencies, but the local venv may need dependency installation before running the full G10 config/model path.
- The G10 daily/replay/refit commands are scaffolded but intentionally not implemented.
- The existing US component bridge is still the website-backed US GDP model until the DFM replay path is proven.
- The fixture coverage check intentionally reports missing configured US target/panel series until the fixture panel is expanded toward the full country pack.
- Non-US G10 vintage construction remains the largest engineering risk.

## Next Steps

1. Run a live `g10-assemble-us --download` for the latest FRED-MD/FRED-QD current vintage and inspect row counts.
2. Expand the US country YAML and fixture panel toward the full FRED-MD/FRED-QD coverage.
3. Promote the DFM smoke output into a replay comparison artifact with vintage-to-vintage news deltas.
4. Decide when the DFM adapter should begin publishing experimental website payloads alongside the component bridge.
