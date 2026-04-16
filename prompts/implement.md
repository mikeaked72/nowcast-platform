# prompts/implement.md — "Implement, validate, report"

Paste this into Codex when you want execution. Assumes `prompts/architect.md`
has already been run and a plan has been agreed (or the goal is small enough
to skip architecture).

---

**GOAL:**

> (fill in — what capability, what constraint, what "done" means)

**Constraints.**
- Preserve existing architecture and file layout.
- Minimise surface-area changes. If you touch more than ~5 files, stop and
  explain why before continuing.
- No new dependencies unless justified and declared in `pyproject.toml`.
- Naming, style, and type annotations must match the existing codebase.
- The model is `DynamicFactorMQ`. No alternative engine.
- Vintages are immutable. No in-place writes to `data/raw` or `data/vintages`.
- No nowcast for date D may reference data with `vintage_date > D`. Enforce
  in code, not just by convention.

**Definition of done.**
- Feature works end to end on a realistic input.
- `pytest -q` passes.
- `ruff check .` passes.
- `mypy src` passes.
- If the data layer changed: `make test-vintage` passes.
- If the model layer changed: `make test-replay-smoke` passes.
- `docs/status.md` updated with: what changed, why, what broke, what's next.
- `docs/decisions.md` updated only if a durable architectural choice was made.

**Workflow Codex must follow.**

1. Re-read `AGENTS.md`, `docs/spec.md`, `docs/status.md`, and any file you're
   about to modify.
2. Explain the current state of the relevant subsystem in 3–5 sentences.
3. Implement in the smallest coherent chunk.
4. Write or update tests **in the same commit** as the code they cover.
5. Run: `pytest -q && ruff check . && mypy src`. Fix, re-run, until clean.
6. If data or model layer touched, also run the relevant `make test-*`
   target.
7. Update `docs/status.md` — replace the current file, don't append
   duplicates. Follow the exact section headings already in that file.
8. Report back.

**Report format (at the end).**

```
## Files changed
- path/to/file.py — one line description
- ...

## Tests run
- pytest -q     → PASS / FAIL / N tests
- ruff          → PASS / FAIL
- mypy          → PASS / FAIL
- make test-... → PASS / FAIL / skipped (reason)

## What now works
- ... (evidence: a command or test name)

## Risks remaining
- ... (how you'd detect)
- ...

## Suggested next action
- (one concrete thing, referencing `docs/plan.md` milestone)
```
