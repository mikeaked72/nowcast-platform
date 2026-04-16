# Site dashboard

The static site reads only generated files under `site/data/`. It does not run model logic in the browser.

## Selectors

The dashboard supports:

- country
- indicator
- run date

Selections are mirrored into the URL query string:

```text
/?country=us&indicator=gdp&run=2026-02-15
```

This makes a specific nowcast view bookmarkable and shareable.

## Views

### Headline

Shows the selected run's estimate, change versus prior run, prior estimate, update cadence, and an overview of all enabled indicators for the selected country.

### History

Shows the estimate path for the selected reference period and a table of run-date estimates.

### Comparison

Shows how the selected run changed versus the prior run in the same reference
period, including new releases and component contribution deltas.

### Contributions

Shows:

- stacked component contribution levels by run date
- changes in component contributions versus the prior run
- the selected run's contribution table

### Release impacts

Shows:

- net new-release impact by run date
- summary counts for `new_release`, `carried_forward`, and `pending`
- source identifiers for each release-impact row
- the selected run's release-impact table
- a selected-run CSV download link

### Release dates

Shows a timeline of source release dates for the selected reference period.

### Downloads

Links directly to the static files used for the selected country/indicator pair,
shows artifact row counts, and surfaces provenance metadata such as schema
version, model version, source count, and last update time.

The dashboard also reads `site/data/manifest.json` when present so users can see
site build freshness without opening every individual payload.

The dashboard reads `site/data/source_coverage.json` when present to show
data-store freshness, processed parquet coverage, and top source series for the
selected country.

## Release status labels

Model-backed indicators can use the `notes` column in `release_impacts.csv` for release status:

- `new_release`: the row was newly incorporated on the selected run date
- `carried_forward`: the row was incorporated on an earlier run and remains active
- `pending`: the series is not yet released and is held at its expected value

## Experimental tracking outputs

Some early indicator pages use data-backed experimental trackers rather than
full econometric models. These outputs are marked with `model_status: warning`
and `model_version: tracking-0.1.0`. The methodology section names the source
series and states that the result is a transparent tracking proxy.
