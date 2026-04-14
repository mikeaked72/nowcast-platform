# Output contract

This document defines the published payload contract between the model pipeline and the static site.

## Principle
Internal modelling objects may change. Published site payloads should change rarely and only deliberately.

The browser should consume complete, explicit payloads. The browser should not infer missing values, fix malformed records, or reconstruct model outputs from partial data.

## Published file set
For every supported country code `<country>`, the publish step must generate:

- `site/data/<country>/nowcast_latest.json`
- `site/data/<country>/nowcast_history.csv`
- `site/data/<country>/news_latest_vs_prior.csv`

In addition, the site root should include:

- `site/data/countries.json`

## countries.json
This file drives the country selector.

### Minimum fields
- `code`: short country identifier used in folder naming, for example `us` or `au`
- `name`: display name shown in the UI
- `default_target`: display label for the nowcast target, for example `GDP QoQ saar`
- `enabled`: boolean flag for whether the country is shown

### Example
```json
[
  {
    "code": "us",
    "name": "United States",
    "default_target": "GDP QoQ saar",
    "enabled": true
  }
]
```

## nowcast_latest.json
This file contains the current nowcast snapshot for a country and powers the summary card.

### Required top-level fields
- `country_code`: string
- `country_name`: string
- `target_code`: string
- `target_name`: string
- `as_of_date`: ISO date string for the information date
- `reference_period`: string label for the target period being nowcast
- `nowcast_value`: numeric point estimate
- `units`: string
- `prior_nowcast_value`: numeric or `null`
- `delta_vs_prior`: numeric or `null`
- `model_status`: string such as `ok`, `warning`, or `error`
- `model_version`: string
- `last_updated_utc`: ISO timestamp string

### Optional fields
- `data_cutoff_utc`
- `release_window`
- `notes`
- `confidence_band`

### Example
```json
{
  "country_code": "us",
  "country_name": "United States",
  "target_code": "gdp_qoq_saar",
  "target_name": "GDP QoQ saar",
  "as_of_date": "2026-03-14",
  "reference_period": "2026Q1",
  "nowcast_value": 2.1,
  "units": "percent",
  "prior_nowcast_value": 1.8,
  "delta_vs_prior": 0.3,
  "model_status": "ok",
  "model_version": "0.1.0",
  "last_updated_utc": "2026-03-14T09:00:00Z"
}
```

## nowcast_history.csv
This file powers the time series chart for a country.

### Required columns
- `as_of_date`
- `reference_period`
- `nowcast_value`
- `target_name`
- `units`

### Optional columns
- `prior_nowcast_value`
- `delta_vs_prior`
- `lower_band`
- `upper_band`
- `model_status`

### Notes
- Use ISO dates where possible.
- Keep one row per nowcast observation.
- Order rows ascending by `as_of_date`.

### Example
```csv
as_of_date,reference_period,nowcast_value,target_name,units
2026-01-15,2026Q1,1.4,GDP QoQ saar,percent
2026-02-15,2026Q1,1.8,GDP QoQ saar,percent
2026-03-14,2026Q1,2.1,GDP QoQ saar,percent
```

## news_latest_vs_prior.csv
This file powers the decomposition view comparing the latest nowcast against the prior nowcast.

### Required columns
- `series_code`
- `series_name`
- `release_date`
- `reference_period`
- `actual_value`
- `expected_value`
- `surprise`
- `impact_on_nowcast`
- `direction`

### Optional columns
- `category`
- `units`
- `notes`

### Notes
- `direction` should be explicit, for example `positive`, `negative`, or `neutral`.
- `impact_on_nowcast` should be numeric so the frontend can sort or aggregate it cleanly.

### Example
```csv
series_code,series_name,release_date,reference_period,actual_value,expected_value,surprise,impact_on_nowcast,direction
retail_sales,Retail sales,2026-03-12,2026-02,0.7,0.3,0.4,0.12,positive
industrial_prod,Industrial production,2026-03-13,2026-02,-0.2,0.1,-0.3,-0.08,negative
```

## Validation rules
- All required files must exist for enabled countries.
- All required fields and columns must be present.
- Dates must parse cleanly.
- Numeric fields must be numeric or explicitly `null` where allowed.
- Country codes must match folder names.
- `countries.json` must not reference countries that do not have a complete payload.
- Frontend code should assume validation has already happened.

## Change policy
If you change this contract, the same PR must also update:
- the publish code
- validation code
- test fixtures
- site consumers
- this document
