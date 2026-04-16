# Project Status

Codex updates this file after each coherent unit of work.

## Current State

The repository now blends two layers:

- Existing nowcast platform: `nowcast/`, `country_packs/`, `site/`, generated static files under `site/data/`, and tests for the output contract.
- New G10 DynamicFactorMQ direction: `docs/spec.md`, `docs/plan.md`, `config/`, `prompts/`, and initial `nowcast/g10/` data/model scaffolding.

The website-facing US GDP output remains the component bridge model for now. The new G10 work is scaffolded alongside it and does not yet replace the published site model.

## What Changed Last

- Added the G10 spec, plan, decisions, status, prompt, and config files from the new operating package.
- Added `config/model.yaml`, `config/blocks.yaml`, and `config/countries/US.yaml`.
- Added `nowcast/g10/` with:
  - FRED transformation-code utilities
  - vintage integrity checks
  - FRED-MD/FRED-QD vintage CSV parsing into the tidy long schema
  - a lazy `statsmodels.DynamicFactorMQ` wrapper
  - config-loading helpers
- Added `Makefile` targets that preserve existing site validation while reserving daily/replay/refit entrypoints for the G10 path.
- Updated project dependencies in `pyproject.toml`, `requirements.txt`, and `requirements-dev.txt`.
- Updated `AGENTS.md` to reflect the blended architecture and the current static site contract.

## Validation Status

Latest validation should include:

- `python -m py_compile nowcast\g10\transforms.py nowcast\g10\vintage.py nowcast\g10\fred_md.py nowcast\g10\dfm.py nowcast\g10\config.py nowcast\cli.py`
- `python scripts\validate_outputs.py --countries us,au,de,br --publish-dir site\data`
- `python -m pytest -q --basetemp tmp\pytest`

## Current Risks

- `statsmodels` and `PyYAML` are declared dependencies, but the local venv may need dependency installation before running the full G10 config/model path.
- The G10 daily/replay/refit commands are scaffolded but intentionally not implemented.
- The existing US component bridge is still the website-backed US GDP model until the DFM replay path is proven.
- Non-US G10 vintage construction remains the largest engineering risk.

## Next Steps

1. Finish M1 US data vertical: download/cache FRED-MD and FRED-QD vintages, parse transformation headers, and assemble `data/vintages/US/<vintage>.parquet`.
2. Add a processed-panel builder that applies tcode transforms and splits monthly versus quarterly panels for `DynamicFactorMQ`.
3. Add a tiny US fixture with two or three vintages so `make test-vintage` can run without network access.
4. Only then start M2: fit a small `DynamicFactorMQ` smoke model and map its outputs back into the existing site contract.

