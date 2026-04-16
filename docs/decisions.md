# docs/decisions.md — Architecture Decision Records

One entry per durable architectural choice. Append only. If a decision is
reversed, add a new entry that supersedes the old one — do not delete the old.

Format: `ADR-NNNN — Title` / Context / Decision / Consequences / Status.

---

## ADR-0001 — Use `statsmodels.DynamicFactorMQ` as the only model

**Status:** accepted.

**Context.** The user explicitly named Chad Fulton's nowcasting notebook as the
model reference. That notebook is built around `DynamicFactorMQ`, which
implements exactly the Bańbura & Modugno (2014) EM estimator on a mixed
monthly/quarterly panel and exposes the `news()` decomposition natively.
Alternatives considered: `dfms` (R), `nowcast_lstm`, custom Kalman-filter
rewrites. All rejected.

**Decision.** `DynamicFactorMQ` is the sole forecasting engine for v1. No
ensemble fallback, no alternative model. Any research into alternatives goes
into a separate `research/` subfolder and is explicitly out of the build path.

**Consequences.**
- Pin `statsmodels>=0.14` — earlier versions have `DynamicFactorMQ` but the
  `news()` API and serialization surface have moved.
- Block structure and hyperparameters must round-trip through the library's
  `factors`, `factor_orders`, `factor_multiplicities` kwargs.
- Incremental updates use `results.append(refit=False)` — that is the
  library-supported fast path.

---

## ADR-0002 — One model per country

**Status:** accepted.

**Context.** The user's spec talks about "G10 economic data" as a single
problem. Technically possible options: (a) one joint cross-country DFM, (b) a
country-specific DFM per economy, (c) a hierarchical / panel DFM.

**Decision.** v1 = (b), one `DynamicFactorMQ` per country. Blocks are
country-specific.

**Consequences.**
- Cross-country spillovers are not captured in v1. Accepted cost.
- Each country's YAML is self-contained and independently testable.
- Country-level parallelism is trivial: one worktree per country is fine.
- A future v2 can experiment with a global-factor block fed by a common set
  of series without reshaping the whole repo — it just adds a block.

---

## ADR-0003 — Vintage parquets are immutable and tidy-long-format

**Status:** accepted.

**Context.** Mixed-frequency panels are naturally wide (one column per
series). But wide parquets are painful for vintage logic because adding a
series mid-history breaks the schema. Tidy long format (one row per
date × series) is slightly larger on disk but schema-stable.

**Decision.** Vintage parquets are tidy long with columns
`[date, series_id, value, freq, tcode, vintage_date, vintage_kind]`.
Processed panels are materialised wide at load time.

**Consequences.**
- Disk usage is higher. Acceptable.
- Joins across vintages, diffs between vintages, and news computation become
  trivial dataframe operations.
- The "processed" panel stage becomes a pure function of the vintage parquet.

---

## ADR-0004 — Pseudo-vintage is an explicit, tagged concept

**Status:** accepted.

**Context.** The FRED-MD and FRED-QD vintage archives go back only to 1999-08
and 2018-05 respectively. Non-US G10 countries have even sparser archival
coverage. For backtests covering pre-archive periods, we must synthesise
vintages by masking current values according to publication-lag calendars.
This is not a real vintage — it does not replicate revisions — and conflating
the two quietly corrupts evaluation.

**Decision.** Every vintage parquet carries a `vintage_kind` column with
exactly one value: `real` or `pseudo`. Mixed-kind vintages are forbidden. The
evaluation layer must report metrics separately for the two kinds.

**Consequences.**
- Slightly more code in the assembly layer to enforce this.
- Backtest numbers will come with an explicit "kind" tag, which is honest.
- Adds one column to the vintage schema; dataframes don't care.

---

## ADR-0005 — Incremental updates on weekdays, full EM refit on Sundays

**Status:** accepted.

**Context.** A full EM fit of `DynamicFactorMQ` on a panel of ~100 monthly
series can take several minutes per country. Running this every day for every
country is wasteful and reduces responsiveness. `results.append(refit=False)`
is a supported fast path.

**Decision.** `make daily` uses `append(refit=False)` on weekdays. Sunday's
run does a full EM refit and overwrites the base results pickle that the week
builds on.

**Consequences.**
- Drift risk: if the EM-optimal parameters shift materially across the week,
  the weekday nowcast is slightly off. Mitigated by the Sunday refit and by
  the fact that EM parameters are historically very stable at weekly horizons.
- Need a test asserting that after one EM pass from the appended state, the
  result equals a full-refit result within tolerance.
- Simplifies cost, latency, and reproducibility of the daily loop.
