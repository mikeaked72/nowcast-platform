# prompts/architect.md — "Plan before you code"

Paste this into Codex when you want a plan, not code. Use before every
non-trivial task. Fill in GOAL and leave the rest as-is.

---

Before writing any code, do the following, in order:

1. **Read** `AGENTS.md`, `docs/spec.md`, `docs/plan.md`, and `docs/status.md`
   in full. If any of them are stale or contradict each other, flag it.
2. **Describe the relevant current architecture.** Only the subset that
   touches this task. Be concrete — name the modules, configs, and data
   paths involved. If something in the spec is underspecified for this task,
   say so.
3. **Propose the smallest viable plan.** Ordered list of steps. Each step
   must be either "write/modify file X" or "run command Y", nothing vaguer.
   Prefer 3–6 steps. If you have more than 8, the plan is too big — split it.
4. **List likely failure modes.** At least three. For each, say how you'll
   detect it (test, assertion, manual check).
5. **Name the verification gate.** What concrete command(s) will prove the
   task is done? Match these to the milestone's exit criteria in
   `docs/plan.md`.
6. **Stop and wait.** Do not write code yet.

GOAL:

> (fill in — architectural, not codey; constraints + definition of done)

Constraints (apply unless overridden in GOAL):
- Preserve existing architecture and file layout.
- Minimise surface-area changes.
- Do not add dependencies without updating `pyproject.toml` and noting it in
  `docs/decisions.md`.
- Keep naming and style consistent with the existing repo.
- The model is `DynamicFactorMQ`. No alternative engine.
- Vintages are immutable. No in-place mutation of `data/raw` or
  `data/vintages`.

Output format:

```
## Architecture touched
...

## Plan
1. ...
2. ...

## Failure modes
- ... → detected by ...
- ... → detected by ...

## Verification gate
- `...`
- `...`
```
