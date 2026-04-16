# docs/spec.md — G10 Nowcasting System

## 0. Purpose

Build a production-grade, daily-refreshed, mixed-frequency dynamic factor nowcasting
system for the G10 economies. Replicate Chad Fulton's `DynamicFactorMQ` notebook
pattern country by country, back-tested using monthly "as-issued" vintage archives.

## 1. The logic in one picture

```
                       ┌────────────────────────────────────────┐
                       │            One country, one day        │
                       │                                        │
  sources              │   vintage assembly          model      │    outputs
  ───────              │   ─────────────────         ─────      │    ───────
  FRED-MD   ─┐         │                                        │
  FRED-QD   ─┤         │                                        │
  EA-MD-QD  ─┼──▶  raw/<source>/<date>/  ──▶  vintages/<ISO>/   │
  FRED API  ─┤                                     │            │
  ALFRED    ─┤                                     ▼            │
  OECD MEI  ─┘                              transform (tcode)   │
                       │                           │            │
                       │                           ▼            │
                       │                      processed panel   │
                       │                           │            │
                       │                           ▼            │
                       │               DynamicFactorMQ.fit  ──▶ │  nowcast.parquet
                       │                  (or .append)          │
                       │                           │            │
                       │                           ▼            │
                       │          results_new.news(results_old) │  news.parquet
                       │                                        │
                       └────────────────────────────────────────┘
                                         │
                                         ▼
                         nowcast_history.parquet (one row / day / target)
```

Three independent layers. Each is testable on its own. Each has a single
responsibility:

| Layer | Responsibility | Key property |
|-------|----------------|--------------|
| Data  | Get the right bytes into the right vintage folder | Vintage integrity |
| Panel | Produce the model-ready matrix for a given (ISO, vintage) | Deterministic from raw |
| Model | Fit `DynamicFactorMQ`, produce nowcast + news | Matches Fulton's notebook |

## 2. The model in detail

Direct reference: Fulton, "Large dynamic factor models, forecasting, and
nowcasting" — `statespace_large_dynamic_factor_models.ipynb`. The class is
`statsmodels.tsa.statespace.DynamicFactorMQ`. The underlying theory:

- **Factor block:** y_t = Λ f_t + ε_t, with f_t following a VAR(p).
- **Quarterly aggregation:** a quarterly observable is identified with the last
  month of the quarter and related to the latent monthly counterpart via the
  Mariano–Murasawa (2010) triangular aggregation weights (1, 2, 3, 2, 1). The
  notebook relies on `DynamicFactorMQ` implementing this internally — we do not
  re-implement it.
- **Estimation:** EM algorithm (Bańbura & Modugno 2014) which tolerates any
  pattern of missingness. No need to forward-fill or drop ragged-edge rows.
- **News decomposition:** given two results objects (from consecutive vintages),
  `results_new.news(results_old, impact_date=..., impacted_variable=...,
  comparison_type='previous')` returns a `NewsResults` object whose tables
  attribute each component of the nowcast revision to (i) updated series, (ii)
  newly added series, and (iii) revisions to previously-released series. We
  persist all of these tables, not just scalars.

### 2.1 Block structure

v1 uses country-tailored blocks, defined in `config/blocks.yaml`. A reasonable
default set, inspired by the NY Fed Staff Nowcast and Bok et al. (2018):

| Block     | Typical contents |
|-----------|------------------|
| global    | Loads on every series. Captures the business-cycle factor. |
| real      | IP, sales, industrial orders, PMI manufacturing, GDP |
| labour    | Employment, unemployment rate, hours, earnings, claims |
| prices    | CPI/HICP, core CPI, PPI, import prices |
| external  | Exports, imports, trade balance, FX |
| financial | Term spread, credit spread, equity index, policy rate |
| soft      | Consumer & business confidence, PMIs |

Each series in `config/countries/<ISO>.yaml` names the blocks it loads on.
`DynamicFactorMQ` accepts this via its `factors` argument (a dict mapping series
name → list of block names, plus `factor_multiplicities` and `factor_orders`).

### 2.2 Hyperparameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `factor_orders` | 2 | Order of the VAR on the factors |
| `factor_multiplicities` | 1 per block | Raise only with evidence |
| `idiosyncratic_ar1` | True | statsmodels default; matches Fulton |
| `standardize` | True | statsmodels default; matches Fulton |
| EM max iterations | 500 | With tight tolerance, 500 is usually sufficient |
| EM tolerance | 1e-6 | Default |

All of these are in `config/model.yaml`, not code.

## 3. Data layer

### 3.1 Sources and vintage semantics

| Country | Primary source | Vintage cadence | Vintage back to |
|---------|----------------|-----------------|------------------|
| US      | FRED-MD, FRED-QD | monthly | 1999-08 (MD), 2018-05 (QD) |
| DE, FR, IT, NL, BE | EA-MD-QD (Zenodo) | monthly | 2024-01 (real-time); earlier via pseudo-vintages |
| UK, CA, JP, CH, SE | FRED + ALFRED + OECD MEI | daily pull, we stamp vintage | series-dependent |

**Pseudo vs. real vintages.** For the non-US G10 countries where a vintage
archive does not go back as far as we would like, we distinguish:
- **Real vintages** (`real`): data captured as it was actually published on that day.
- **Pseudo vintages** (`pseudo`): the current value with publication-lag masked,
  i.e. we hold back each series by its known release calendar but do not replay
  revisions.

Every vintage parquet has a `vintage_kind` column with exactly one of those two
values. Mixed vintages are forbidden — the replay engine must raise if it sees
one vintage file mixing both.

### 3.2 FRED-MD / FRED-QD acquisition

The historical vintage archives are published as two zip files:
- `Historical Vintages of FRED-MD 1999-08 to 2014-12.zip`
- `Historical Vintages of FRED-MD 2015-01 to <latest-year>-12.zip`

And equivalent for FRED-QD from 2018-05. For any month on or after the latest
archive cut, we pull the monthly CSV directly from the McCracken page:

```
https://files.stlouisfed.org/files/htdocs/fred-md/monthly/<YYYY-MM>.csv
https://files.stlouisfed.org/files/htdocs/fred-qd/quarterly/<YYYY-MM>.csv
```

The header rows of these CSVs contain the transformation codes. These are parsed
once into `config/fred_md_tcodes.yaml` and `config/fred_qd_tcodes.yaml`.

### 3.3 ALFRED usage

For non-US countries, per-series vintage histories are fetched from ALFRED
(`https://api.stlouisfed.org/fred/series/observations` with `realtime_start` and
`realtime_end`). A FRED API key lives in the environment (`FRED_API_KEY`), never
in code. See `src/g10nowcast/data/alfred.py`.

### 3.4 Target-variable mapping

Every country's YAML has a top-level `targets:` block mapping the canonical
target name (gdp, cpi, employment, wages, profits, imports, exports,
investment) to the source series ID, native frequency, tcode, and publication lag
(in days from end of reference period). Example (US):

```yaml
targets:
  gdp:        {series: GDPC1,   freq: Q, tcode: 5, lag_days: 28}
  cpi:        {series: CPIAUCSL, freq: M, tcode: 6, lag_days: 14}
  employment: {series: PAYEMS,  freq: M, tcode: 5, lag_days: 5}
  wages:      {series: CES0500000003, freq: M, tcode: 5, lag_days: 5}
  profits:    {series: CPATAX,  freq: Q, tcode: 5, lag_days: 56}
  imports:    {series: IMPGS,   freq: Q, tcode: 5, lag_days: 28}
  exports:    {series: EXPGS,   freq: Q, tcode: 5, lag_days: 28}
  investment: {series: GPDIC1,  freq: Q, tcode: 5, lag_days: 28}
```

The `lag_days` field drives the pseudo-vintage masker.

## 4. Daily update loop (detail)

```python
# pseudocode; real implementation lives in src/g10nowcast/cli/daily.py
for iso in G10:
    cfg = load(f"config/countries/{iso}.yaml")

    raw_new = data.pull_today(iso, cfg)               # (1) sources -> data/raw
    vintage = data.assemble_vintage(iso, date=today)  # (2) raw -> vintages/<iso>/<today>.parquet
    panel = panel.build(iso, vintage)                 # (3) vintages -> processed panel

    prev = model.load_latest(iso)                     # yesterday's DynamicFactorMQ results
    results = model.append(prev, panel, refit=False)  # (4) fast incremental update

    for target in cfg.targets:
        impact_date = schedule.next_reference_period(target, today)
        news = results.news(prev, impact_date=impact_date,
                            impacted_variable=target,
                            comparison_type='previous')
        persist.nowcast(iso, today, target, results, news)    # (5)(6)

    doc.update_status(iso, today)                     # (7)
```

Sunday job: full EM refit with the entire panel, drop `refit=False`. Monday's
fast path then proceeds from the refitted model.

## 5. Historical real-time replay

The replay is run once per country over each month in the vintage archive. It is
the backbone of all evaluation. Its output — `replay_history.parquet` — answers
every question of the form *"what did the model think about X on day Y?"*.

Replay schema (one row per vintage × target × impact_date):

| column | type | meaning |
|--------|------|---------|
| iso | str | country |
| vintage_date | date | vintage file the nowcast was made from |
| target | str | gdp, cpi, employment, … |
| impact_date | date | period being nowcast (end of month convention) |
| nowcast | float | point estimate in original units |
| stderr | float | from the Kalman smoother |
| realized | float \| null | the eventual realisation (final revision) |
| news_json | str | serialized `news.summary_impacts` table |
| top_driver_1 | str | highest-weight updated series |
| top_driver_1_contribution | float | its contribution (in target units) |
| … | … | up to top_driver_5 |

Evaluation utilities (`src/g10nowcast/eval/`) compute:
- RMSE vs. realisation at each horizon (−3m, −2m, −1m, 0, +1m relative to release).
- Directional accuracy.
- RMSE vs. the "first release" and vs. "final revision" (two different truths).
- Comparison with the random-walk benchmark and the AR(1) benchmark.

## 6. Project layout

```
g10-nowcast/
├── AGENTS.md                     # Codex reads this first, every time
├── README.md                     # one-pager for humans
├── pyproject.toml                # deps, ruff, mypy, pytest config
├── Makefile                      # daily, replay, test, lint, refit
├── docs/
│   ├── spec.md                   # this file
│   ├── plan.md                   # the build plan with milestones
│   ├── status.md                 # current state (Codex updates)
│   └── decisions.md              # ADRs
├── prompts/
│   ├── architect.md              # the "plan-before-code" prompt
│   ├── implement.md              # the "implement + validate" prompt
│   ├── status.md                 # the "regenerate status" prompt
│   └── replay.md                 # the "run historical replay" prompt
├── config/
│   ├── model.yaml                # hyperparameters
│   ├── blocks.yaml               # block definitions
│   ├── countries/
│   │   ├── US.yaml
│   │   ├── CA.yaml
│   │   ├── UK.yaml
│   │   ├── DE.yaml
│   │   ├── FR.yaml
│   │   ├── IT.yaml
│   │   ├── JP.yaml
│   │   ├── CH.yaml
│   │   ├── SE.yaml
│   │   ├── NL.yaml
│   │   └── BE.yaml
│   ├── fred_md_tcodes.yaml
│   └── fred_qd_tcodes.yaml
├── src/g10nowcast/
│   ├── __init__.py
│   ├── cli/
│   │   ├── daily.py              # `python -m g10nowcast.cli.daily`
│   │   ├── replay.py
│   │   └── refit.py
│   ├── data/
│   │   ├── fred_md.py            # FRED-MD/QD vintage loader
│   │   ├── alfred.py             # per-series vintage fetcher
│   │   ├── ea_md_qd.py           # EA-MD-QD loader
│   │   ├── oecd_mei.py
│   │   └── assemble.py           # one-vintage assembler
│   ├── panel/
│   │   ├── transform.py          # tcode transforms
│   │   └── build.py              # processed panel builder
│   ├── model/
│   │   ├── dfm.py                # DynamicFactorMQ wrapper
│   │   ├── append.py             # incremental update
│   │   └── news.py               # news extraction & serialization
│   ├── eval/
│   │   ├── benchmarks.py
│   │   └── metrics.py
│   └── util/
│       ├── io.py
│       ├── schedule.py           # publication-lag & release-calendar logic
│       └── vintage.py            # vintage_date arithmetic
├── tests/
│   ├── test_fred_md_loader.py
│   ├── test_tcode_transforms.py
│   ├── test_panel_build.py
│   ├── test_model_fit_smoke.py
│   ├── test_append_matches_refit.py
│   ├── test_news_api.py
│   ├── test_replay_determinism.py
│   └── fixtures/
│       └── us_mini/              # tiny 3-vintage replay fixture
├── data/
│   ├── raw/                      # never mutated
│   ├── vintages/                 # tidy parquet per (iso, vintage_date)
│   └── processed/                # model-ready panels
└── artifacts/
    ├── <ISO>/
    │   ├── model_<YYYY-MM-DD>.pkl
    │   ├── nowcast_<YYYY-MM-DD>.parquet
    │   ├── news_<YYYY-MM-DD>.parquet
    │   ├── nowcast_history.parquet
    │   └── replay/<vintage>/…
```

## 7. Build order (milestones)

Each milestone ends with tests green and `docs/status.md` updated.

- **M0 — Scaffold**: repo skeleton, pyproject, AGENTS.md, spec, plan, makefile,
  CI stub.
- **M1 — US data vertical**: FRED-MD/QD vintage loader, tcode transforms,
  panel builder for US only. `make test-vintage` green.
- **M2 — US model vertical**: `DynamicFactorMQ` wrapper, single-vintage fit,
  nowcast extraction, smoke test against a pinned expected value from Fulton's
  2020-06 vintage.
- **M3 — News decomposition**: wrap `.news()`, persist the impacts table,
  unit-test against a trivial two-vintage toy.
- **M4 — US replay**: full historical replay from earliest joint FRED-MD+QD
  vintage to current. Evaluation metrics against realised values.
- **M5 — Daily loop for US**: `make daily` working end-to-end, `append` fast
  path, Sunday full refit.
- **M6 — Euro-area (DE, FR, IT, NL, BE)** via EA-MD-QD.
- **M7 — UK, CA, JP, CH, SE** via ALFRED + OECD assembly.
- **M8 — Dashboard / reporting** layer (out of scope for this doc — see
  `docs/plan.md`).

## 8. Known risks (from day 0)

1. **Real vintages for non-US G10 don't exist at scale.** Mitigated by the
   `vintage_kind` split and by leaning on ALFRED where possible. Be explicit
   about which results are from pseudo vintages.
2. **Revisions vs. missingness confusion.** A revision is *not* a news item in
   the Bańbura-Modugno sense; it is a change to an existing observation. The
   `news` method handles both, but our persistence layer must tag them
   separately. See `src/g10nowcast/model/news.py`.
3. **Block mis-specification.** Wrong block assignments quietly degrade the
   nowcast. Covered by per-country config + a block-sensitivity test.
4. **EM convergence on small panels.** Some of the smaller G10s may have panels
   of 20–40 series. `DynamicFactorMQ` still works, but convergence tolerance
   and initialisation matter more. See `docs/decisions.md`.
5. **Holiday / weekend daily runs.** `make daily` on a weekend should be a
   no-op for the ingestion step but still re-persist yesterday's nowcast tagged
   with today's date.

## 9. References

- Fulton, C. "Large dynamic factor models, forecasting, and nowcasting."
  tsa-notebooks, 2020.
- Bańbura, M., Modugno, M. "Maximum likelihood estimation of factor models on
  datasets with arbitrary pattern of missing data." JAE, 2014.
- Bok, B., Caratelli, D., Giannone, D., Sbordone, A., Tambalotti, A.
  "Macroeconomic Nowcasting and Forecasting with Big Data." ARE, 2018.
- Mariano, R.S., Murasawa, Y. "A coincident index, common factors, and monthly
  real GDP." OBES, 2010.
- McCracken, M., Ng, S. "FRED-MD: A monthly database." JBES, 2016.
- McCracken, M., Ng, S. "FRED-QD: A quarterly database." FRB St Louis Review, 2021.
- Barigozzi, M., Lissona, C. "EA-MD-QD: Large Euro Area datasets." Zenodo, 2024.
