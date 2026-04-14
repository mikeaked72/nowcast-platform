# AGENTS.md

## Purpose
This repository builds multi-country nowcast outputs from API and source data, validates them, and publishes static artefacts for the `site/` frontend.

## Architecture
- `nowcast/` = Python package for ingestion, transformation, fitting, news decomposition, and publishing.
- `country_packs/` = country-specific configuration only.
- `site/` = static frontend only. No modelling logic belongs here.
- `tests/` = unit, smoke, and contract tests.
- `runs/` = local artefacts only. Never rely on these as committed source data.
- `docs/` = architecture, contract, and deployment notes.

## Working assumptions
- The frontend consumes prebuilt files under `site/data/<country>/`.
- The heavy nowcast job runs outside the browser.
- Cloudflare Pages serves static assets only.
- The publish boundary is owned by `nowcast/publish.py`.

## Hard rules
1. Preserve the published output contract unless explicitly asked to change it.
2. If you change the output contract, update all of the following together:
   - `nowcast/publish.py`
   - `docs/output_contract.md`
   - `site/` code that consumes the outputs
   - fixtures and tests
3. Do not move modelling logic into `site/`.
4. Do not put country-specific logic into generic package files unless it is parameterised through `country_packs/`.
5. Do not put secrets in code, config, sample packs, or commits.
6. Treat notebooks as reference and reproduction aids only. Production logic belongs in the package.
7. Prefer small, surgical edits over broad rewrites.
8. Validate every layer boundary when a change spans multiple layers.
9. Do not silently broaden schemas or coerce malformed data in the frontend.
10. Use existing patterns before creating new abstractions.

## Task routing
### If the task is model or data related
Work in:
- `nowcast/`
- `country_packs/`
- `tests/`
- `docs/output_contract.md`

Do not modify frontend files unless the task changes the published contract or exposes a real display bug.

### If the task is frontend related
Work in:
- `site/`
- relevant frontend smoke tests

Do not modify model code unless the root cause is a broken or missing payload field.

### If the task is country onboarding
Start in:
- `country_packs/`
- pack validation tests

Only touch package code if the new country cannot be expressed via the current schema.

### If the task is deployment related
Work in:
- `.github/workflows/`
- `docs/deployment.md`
- deployment-specific config files

Do not change modelling logic during deployment-only tasks unless the deploy is failing because the generated outputs are invalid.

## Output contract
For each country, the published site payload must contain:
- `site/data/<country>/nowcast_latest.json`
- `site/data/<country>/nowcast_history.csv`
- `site/data/<country>/news_latest_vs_prior.csv`

See `docs/output_contract.md` for the field-level contract.

## Definition of done
A task is not done unless:
- relevant tests pass
- output contract validation passes
- a local smoke run succeeds for at least one country
- the site still renders with the produced payloads
- docs are updated if behaviour changed
- the final note explains what changed, how it was validated, and what risks remain

## Safe task patterns
- Add a country by editing `country_packs/` first, then package code only if the schema cannot express the new case.
- When fixing display bugs, do not modify model code unless the bug is data-contract related.
- When fixing model issues, add or update tests before changing site behaviour.
- When changing the contract, update fixtures first so failures become explicit.

## Commands
Replace these placeholders with real project commands once the environment is finalised.

- install: `make install`
- test: `pytest -q`
- smoke model run: `python -m nowcast.cli run --country us --as-of 2026-03`
- validate publish contract: `python scripts/validate_outputs.py --country us`
- local site preview: `python -m http.server 3000 -d site`

If these commands are wrong for the repo state, update this file in the same commit that introduces the new canonical commands.

## PR checklist
Every PR summary should state:
- which layer changed
- whether the output contract changed
- what validations were run
- whether a smoke country was generated
- what risks or TODOs remain
