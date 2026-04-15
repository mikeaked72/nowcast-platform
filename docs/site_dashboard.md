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

### Contributions

Shows:

- stacked component contribution levels by run date
- changes in component contributions versus the prior run
- the selected run's contribution table

### Release impacts

Shows:

- net new-release impact by run date
- summary counts for `new_release`, `carried_forward`, and `pending`
- the selected run's release-impact table
- a selected-run CSV download link

### Release dates

Shows a timeline of source release dates for the selected reference period.

### Downloads

Links directly to the static files used for the selected country/indicator pair.

## Release status labels

Model-backed indicators can use the `notes` column in `release_impacts.csv` for release status:

- `new_release`: the row was newly incorporated on the selected run date
- `carried_forward`: the row was incorporated on an earlier run and remains active
- `pending`: the series is not yet released and is held at its expected value
