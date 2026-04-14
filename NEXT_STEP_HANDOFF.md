# What to do next

You asked to be told when to move into Codex or Claude Code.

That point is now.

These files are the right moment to hand the repo to a coding agent because the remaining work is implementation inside the repository, not more architecture.

## Best handoff sequence
1. Add these files to the repo.
2. Open the repo in Codex or Claude Code.
3. Ask the agent to reconcile these files with the actual project tree.
4. Then ask it to create the missing executable pieces referenced by the workflows, especially:
   - `nowcast/publish.py`
   - `nowcast/schemas.py`
   - `scripts/run_country.py`
   - `scripts/run_all_countries.py`
   - `scripts/validate_outputs.py`
   - tests for the publish contract

## Use Codex if
- you want the repo operating rules enforced through `AGENTS.md`
- you want long-horizon repo work and GitHub-centred flow
- you are happy using WSL2 or a Unix-like environment

## Use Claude Code if
- you want fast local iteration on Windows first
- you expect the next pass to involve messy notebook patching or package drift
- you want a strong second-opinion coding agent inside the repo

## Prompt to use in either Codex or Claude Code
Read `AGENTS.md` first.

Reconcile the repository with the workflow and contract files that were just added.

Tasks:
1. create `nowcast/publish.py` to convert internal model outputs into the published site contract
2. create `nowcast/schemas.py` with validation helpers for the JSON and CSV outputs
3. create `scripts/run_country.py`, `scripts/run_all_countries.py`, and `scripts/validate_outputs.py`
4. add tests covering the output contract and one smoke publish run
5. keep edits minimal and preserve the existing site contract
6. do not move modelling logic into `site/`
7. tell me any assumptions you had to make because the current scaffolding is incomplete

Validation required before finishing:
- tests pass
- one smoke country publish run succeeds
- published output files match `docs/output_contract.md`
- explain any remaining gaps

## Human decisions still needed
- final Python dependency setup
- exact canonical CLI commands
- first real country beyond the United States
- Cloudflare Pages project name and secrets
- whether `site/data/` should be committed or treated as build output only
