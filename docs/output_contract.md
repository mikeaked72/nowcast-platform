# Output contract

This document defines the published payload contract between the model pipeline and the static site.

## Principle

Internal modelling objects may change. Published site payloads should change rarely and deliberately.

The browser consumes complete, explicit payloads. It should not infer missing values, repair malformed records, or reconstruct model outputs from partial data.

## Published file set

The publish root is `site/data/`.

The root must include:

- `site/data/countries.json`

For every enabled country and indicator pair, the publish step must generate:

- `site/data/{country_code}/{indicator_code}/latest.json`
- `site/data/{country_code}/{indicator_code}/history.csv`
- `site/data/{country_code}/{indicator_code}/contributions.csv`
- `site/data/{country_code}/{indicator_code}/release_impacts.csv`
- `site/data/{country_code}/{indicator_code}/metadata.json`

Examples:

- `site/data/us/gdp/latest.json`
- `site/data/us/inflation/history.csv`
- `site/data/au/gdp/release_impacts.csv`

## countries.json

This file drives the country and indicator selectors.

Required country fields:

- `code`: short country identifier used in folder naming, for example `us` or `au`
- `name`: display name
- `default_target`: default target label
- `enabled`: boolean flag
- `indicators`: list of enabled indicator entries

Required indicator entry fields:

- `code`: folder-safe indicator code, for example `gdp`
- `display_name`: UI label, for example `GDP`

Example:

```json
[
  {
    "code": "us",
    "name": "United States",
    "default_target": "GDP QoQ saar",
    "enabled": true,
    "indicators": [
      { "code": "gdp", "display_name": "GDP" },
      { "code": "inflation", "display_name": "Inflation" }
    ]
  }
]
```

## metadata.json

This file defines how the site explains and formats an indicator.

Required fields:

- `country_code`
- `country_name`
- `indicator_code`
- `display_name`
- `unit`
- `decimals`
- `default_chart_type`
- `explanatory_text`
- `update_cadence_label`

Optional but recommended fields:

- `default_period`
- `methodology`
- `faq`
- `downloads`

## latest.json

This file contains the current snapshot for one country/indicator pair.

Required fields:

- `country_code`
- `country_name`
- `indicator_code`
- `indicator_name`
- `as_of_date`
- `next_update_date`
- `reference_period`
- `estimate_value`
- `unit`
- `prior_estimate_value`
- `delta_vs_prior`
- `model_status`
- `model_version`
- `last_updated_utc`

Numeric fields must be numbers or explicit `null` where allowed. Dates must be ISO date strings, and `last_updated_utc` must be an ISO timestamp.

## history.csv

This file powers the estimate evolution view.

Required columns:

- `as_of_date`
- `reference_period`
- `estimate_value`
- `prior_estimate_value`
- `delta_vs_prior`
- `model_status`

Rows must be ordered ascending by `as_of_date`.

## contributions.csv

This file powers the contribution/drivers view.

Required columns:

- `as_of_date`
- `component_code`
- `component_name`
- `reference_period`
- `contribution`
- `direction`
- `category`
- `unit`

`direction` must be one of `positive`, `negative`, or `neutral`.

## release_impacts.csv

This file powers the release-impact table and the release-date timeline.

Required columns:

- `as_of_date`
- `release_date`
- `release_name`
- `indicator_code`
- `indicator_name`
- `reference_period`
- `actual_value`
- `expected_value`
- `surprise`
- `impact`
- `direction`
- `category`
- `unit`
- `notes`

`impact` must be numeric so the frontend can sort or aggregate it cleanly.

For model-backed indicators, `notes` may carry release status labels such as:

- `new_release`
- `carried_forward`
- `pending`

## Current sample coverage

The scaffold publishes:

- US GDP
- US inflation
- US exports
- US imports
- AU GDP
- AU inflation

US GDP can be generated from the FRED bridge model. The other initial outputs are deterministic sample data that exercise the same static contract.

## Change policy

If this contract changes, update all of these together:

- publish code
- validation code
- site consumers
- tests and fixtures
- this document
