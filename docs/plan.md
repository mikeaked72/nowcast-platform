# docs/plan.md — Build Plan

This is the build plan. It is milestone-oriented, not date-oriented, because
Codex-driven work is bursty. Each milestone has **explicit entry and exit
criteria** and a **"this milestone is not done until"** list that `make
check-milestone` validates.

## Milestone M0 — Scaffold

**Entry:** empty repo.
**Exit:** every path in `docs/spec.md §6` exists, `pytest -q` returns 0 tests
collected without error, `ruff check .` and `mypy src` both pass.

Not done until:
- [ ] `AGENTS.md`, `docs/spec.md`, `docs/plan.md`, `docs/status.md`,
      `docs/decisions.md` all exist.
- [ ] `pyproject.toml` declares: `statsmodels>=0.14`, `pandas`, `numpy`,
      `pyarrow`, `requests`, `pyyaml`, `click`, `ruff`, `mypy`, `pytest`,
      `pytest-cov`, `python-dateutil`.
- [ ] `Makefile` defines: `daily`, `replay`, `refit`, `test`, `lint`,
      `test-vintage`, `test-replay-smoke`, `check-milestone`.
- [ ] `config/model.yaml`, `config/blocks.yaml`, `config/countries/US.yaml`
      populated with placeholder-but-valid values.
- [ ] `.github/workflows/ci.yml` runs ruff + mypy + pytest on push.
- [ ] `docs/status.md` updated.

## Milestone M1 — US data vertical

**Entry:** M0 exit criteria met.
**Exit:** for any `vintage ∈ [2015-01, current]`, the command
`python -m g10nowcast.cli.replay --iso US --vintage <v> --data-only` writes
a valid `data/vintages/US/<v>.parquet` with the expected schema and row count
within tolerance.

Not done until:
- [ ] `src/g10nowcast/data/fred_md.py` implements `load_vintage(vintage_date)`
      returning a DataFrame with `[date, series_id, value, tcode]`.
- [ ] Same for FRED-QD.
- [ ] `src/g10nowcast/data/assemble.py::assemble_vintage(iso, vintage_date)`
      merges monthly + quarterly into one tidy parquet with
      `[date, series_id, value, freq, tcode, vintage_date, vintage_kind]`.
- [ ] Tests: `test_fred_md_loader.py` (parses the tcode header, handles the
      1999-08 through current schema drift, rejects malformed files),
      `test_assemble_vintage.py` (schema, no-nulls-in-key-columns,
      vintage_date correctness).
- [ ] `make test-vintage` passes.
- [ ] `docs/status.md` updated.

## Milestone M2 — US model vertical

**Entry:** M1 exit criteria met.
**Exit:** `python -m g10nowcast.cli.replay --iso US --vintage 2020-06
--targets gdp` produces a single-vintage nowcast whose 2020Q2 point estimate
matches Fulton's notebook to within 0.05 percentage points.

Not done until:
- [ ] `src/g10nowcast/model/dfm.py` implements `fit(panel, config)` returning
      a `DynamicFactorMQResults`.
- [ ] The wrapper passes `factors`, `factor_orders`, `factor_multiplicities`
      to `DynamicFactorMQ` from `config/blocks.yaml`.
- [ ] A smoke test pins the 2020Q2 nowcast for US GDP at the 2020-06 vintage
      (the notebook's own example) with a numerical tolerance.
- [ ] `docs/status.md` updated.

## Milestone M3 — News decomposition

**Entry:** M2 exit criteria met.
**Exit:** for any two consecutive vintages v_prev, v_new,
`python -m g10nowcast.cli.replay --iso US --vintages v_prev,v_new --news`
produces a `news_<v_new>.parquet` whose total impact equals the difference in
point nowcasts to machine precision.

Not done until:
- [ ] `src/g10nowcast/model/news.py::compute_news(results_new, results_old,
      impact_date, impacted_variable)` returns a dataclass with: `total_impact`,
      `updates_table`, `revisions_table`, `top_drivers`.
- [ ] A closure test: sum of `updates_table.impact` +
      `revisions_table.impact` equals `nowcast_new - nowcast_old` within 1e-8.
- [ ] `docs/status.md` updated.

## Milestone M4 — US historical replay

**Entry:** M3 exit criteria met.
**Exit:** `make replay COUNTRY=US START=2015-01 END=current` runs to completion
and `artifacts/US/replay_history.parquet` has one row per
(vintage, target, impact_date) triple with no nulls in required columns.

Not done until:
- [ ] `src/g10nowcast/cli/replay.py` iterates vintages, fits, computes news
      vs. prior vintage, writes replay parquets.
- [ ] Deterministic: running twice produces identical parquets (checked via
      hash in `test_replay_determinism.py`).
- [ ] Evaluation script reports RMSE vs. realised values at the standard
      horizons.
- [ ] `docs/status.md` updated.

## Milestone M5 — Daily loop (US)

**Entry:** M4 exit criteria met.
**Exit:** `make daily` on any weekday updates `data/`, `artifacts/US/`, and
`docs/status.md` in one shot, using `results.append(refit=False)` for the
model step unless it's Sunday.

Not done until:
- [ ] `src/g10nowcast/cli/daily.py` exists.
- [ ] `src/g10nowcast/model/append.py::append_today(prev_results, panel)`
      returns a new results object without re-running EM.
- [ ] A test verifies that `append`-then-`fit` gives the same point nowcast
      as a full refit to within tolerance after one full EM pass.
- [ ] Sunday branch triggers a full refit and replaces the base results.
- [ ] `docs/status.md` updated.

## Milestone M6 — Euro-area via EA-MD-QD

**Entry:** M5 exit criteria met.
**Exit:** `make replay COUNTRY=DE START=2024-01 END=current` completes,
analogous for FR, IT, NL, BE.

Not done until:
- [ ] `src/g10nowcast/data/ea_md_qd.py` handles the Zenodo zip structure.
- [ ] `config/countries/DE.yaml`, `FR.yaml`, `IT.yaml`, `NL.yaml`, `BE.yaml`
      populated with full target maps and block assignments.
- [ ] Replay evaluation against GDP releases is within expected error bands.
- [ ] `docs/status.md` updated.

## Milestone M7 — UK, CA, JP, CH, SE via ALFRED + OECD

**Entry:** M6 exit criteria met.
**Exit:** `make replay COUNTRY=<X>` works for X ∈ {UK, CA, JP, CH, SE}.

Not done until:
- [ ] `src/g10nowcast/data/alfred.py::fetch_vintages(series_id, realtime_range)`
      works and respects the FRED API rate limits.
- [ ] `src/g10nowcast/data/oecd_mei.py` loader.
- [ ] Vintage assembly logic handles mixed-source panels, tagging each cell
      with `vintage_kind`.
- [ ] Per-country YAMLs complete.
- [ ] `docs/status.md` updated.

## Milestone M8 — Reporting layer (stretch)

Not specified here. See a future `docs/plan.md §M8` once M7 ships.

## Parallelism hints for Codex

- M1, M2, M3 are strictly sequential; do not start M2 before M1 is green.
- M6 and M7 are independent of each other but both depend on M5.
- Within M7, each country's YAML + loader can be its own worktree/thread.
- `docs/status.md` updates serialize — only one thread writes at a time.
