# prompts/replay.md — "Run the historical replay"

Paste this into Codex when you want to run or re-run the historical replay
for a country (or all countries). Assumes M4 (US) or M6/M7 (others) is at
least partially complete.

---

**GOAL:** run the historical real-time replay and produce
`artifacts/<ISO>/replay_history.parquet` plus a human-readable evaluation
report.

**Inputs (fill these in).**
- `COUNTRY`: ISO code from the G10 set (US, CA, UK, DE, FR, IT, JP, CH, SE,
  NL, BE).
- `START`: first vintage month to replay (e.g. `2015-01`). Default: earliest
  vintage for which we have data for this country.
- `END`: last vintage month. Default: `current`.
- `TARGETS`: comma-separated list. Default: all eight targets from
  `config/countries/<ISO>.yaml`.

**Constraints.**
- Deterministic. Running this prompt twice with the same inputs must
  produce byte-identical parquets (modulo trailing metadata). If you cannot
  guarantee this, stop and explain.
- No nowcast may reference data with `vintage_date > its own vintage`.
  Enforce this with an assertion in the replay loop, not just a comment.
- Use `real` vintages where available; if any are `pseudo`, report the
  split in the final evaluation.
- Don't silently skip a vintage. If a vintage file is missing or malformed,
  log it, fail loudly, and surface the failure in the final report.

**Workflow Codex must follow.**

1. Read `AGENTS.md`, `docs/spec.md §5 and §7`, and `config/countries/<ISO>.yaml`.
2. Check that the data layer has all vintages in `[START, END]`. If not,
   run the ingestion first.
3. For each vintage V in order:
   a. Load `data/vintages/<ISO>/<V>.parquet`.
   b. Build the processed panel.
   c. Fit `DynamicFactorMQ` (full EM) or, if replaying from the fast path
      onwards, `append` from V-1.
   d. For each target, compute the nowcast and (if V > START) the news vs.
      V-1 via `results.news(...)`.
   e. Persist to `artifacts/<ISO>/replay/<V>/`.
4. Assemble `artifacts/<ISO>/replay_history.parquet`.
5. Run evaluation: RMSE vs. realised values at horizons {-3m, -2m, -1m, 0,
   +1m}, split by `vintage_kind`, with random-walk and AR(1) benchmarks.
6. Write the evaluation to `artifacts/<ISO>/replay_report_<today>.md`.

**Report back with.**
- How many vintages replayed.
- How many nowcasts produced.
- Real vs. pseudo vintage counts.
- A compact RMSE table per target × horizon.
- Whether the determinism hash matched any previous run.
- Whether any vintages were skipped or failed, with reasons.
- The path to `artifacts/<ISO>/replay_report_<today>.md`.
