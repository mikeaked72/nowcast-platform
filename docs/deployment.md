# Deployment flow

## Target model
- GitHub is the source of truth for code.
- GitHub Actions builds the nowcast payloads.
- Cloudflare Pages serves the static site.
- The `site/` directory is the deploy artefact.

## Why this split
The model pipeline is Python-heavy and may need package control, scheduling, and validation before deployment. The site is static and should only consume published artefacts.

## Recommended Cloudflare mode
Use Cloudflare Pages Direct Upload from GitHub Actions.

This fits a custom build pipeline because the workflow can generate the payloads first, validate them, then deploy the prebuilt `site/` directory.

## Required secrets
Store these in GitHub repository secrets:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_PAGES_PROJECT`

If you also use private data APIs, store those credentials in GitHub secrets as well. Never place them in country packs or committed config.

## Build sequence
1. Check out the repo.
2. Set up Python.
3. Install dependencies.
4. Run tests and a smoke country if this is a CI validation job.
5. Run the publish pipeline for the intended countries.
6. Write site payloads into `site/data/`.
7. Validate the published contract.
8. Deploy `site/` to Cloudflare Pages.

## Branch model
- `main` is protected and deployable.
- feature branches run CI only.
- deploys happen from `main` or manual dispatch.
- scheduled refreshes run from GitHub Actions on the default branch.

## Failure policy
Do not deploy if:
- tests fail
- contract validation fails
- required output files are missing
- a publish job returns partial country outputs for enabled countries

## Manual recovery
If a scheduled nowcast run fails:
1. inspect the workflow logs
2. identify whether the failure is data ingress, modelling, publish validation, or Cloudflare deployment
3. rerun after the root cause is fixed
4. do not hand-patch `site/data/` in production outside the publish workflow unless the incident process explicitly allows it
