# prompts/status.md — "Regenerate the status report"

Paste this into Codex when you want a fresh, accurate view of project state.
Useful after a long session, after a context switch, or when `docs/status.md`
looks stale.

---

Give me a current codebase status report. Do not guess — inspect the
filesystem, run the commands, and read the files.

Produce this report and **write it into `docs/status.md`** (replacing the
current contents), using the exact section headings already in that file:

1. **Current milestone** — which one from `docs/plan.md` we're in, and
   whether its entry criteria are met.
2. **Branch / working tree** — run `git status` and `git log -1 --oneline`.
3. **What was done last** — inferred from the last 10 commits and the diff
   against `main`.
4. **What is in flight** — uncommitted files, half-written tests, TODO
   comments newer than the last commit.
5. **What's next (top 3)** — concrete, ordered, each one referencing a
   specific file or a specific line in `docs/plan.md`.
6. **Test / lint / typecheck status** — run `pytest -q`, `ruff check .`,
   `mypy src`, `make test-vintage`, `make test-replay-smoke`. Report the
   real exit status of each.
7. **Architecture map (as-is)** — a brief tree of what's actually
   implemented vs. what's still spec-only. Don't copy the spec; diff it
   against reality.
8. **Open risks** — carry forward from `docs/spec.md §8` and add any new
   ones discovered during work.
9. **Recommended next actions for Codex** — one paragraph, ending with
   the exact `prompts/implement.md` goal string to paste next.

After writing the file, summarise the report in chat — but the file is the
source of truth, not your chat reply.
