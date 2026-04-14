Read `AGENTS.md` first and treat it as the canonical operating guide for this repository.

If instructions here and `AGENTS.md` differ, follow `AGENTS.md`.

Project defaults:
- Keep notebooks out of the production path.
- Preserve the `site/data/<country>/` output contract unless explicitly asked to change it.
- Prefer small edits over rewrites.
- Keep modelling logic in `nowcast/`, country-specific rules in `country_packs/`, and display logic in `site/`.
- Report what you validated and what still needs checking.
