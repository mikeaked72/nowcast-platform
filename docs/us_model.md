# US GDP nowcast model

## Purpose
This is the first working US GDP nowcast model. It is intentionally transparent and lightweight so the data, model run, publish step, and site contract can be exercised end to end before adding a richer econometric model.

## Data source
The model downloads public FRED graph CSV files into `runs/source/us/fred/`.

Series used:
- `GDPC1`: real gross domestic product, quarterly target
- `INDPRO`: industrial production index
- `PAYEMS`: total nonfarm payrolls
- `RSAFS`: advance retail sales
- `HOUST`: housing starts
- `DSPIC96`: real disposable personal income

`runs/` remains local run data and should not be treated as committed source data.

## Model
The model is a bridge regression for quarterly real GDP growth, expressed as quarter-over-quarter annualized log growth.

Monthly indicators are converted to quarterly averages and then quarter-over-quarter annualized log growth rates. A small ridge penalty is used when solving the regression to keep the initial scaffold stable.

For the latest quarter, the model writes one row per indicator to `runs/input/us/model_input.csv`:
- `baseline_nowcast`: fitted value using long-run average indicator growth
- `actual_value`: latest quarterly indicator growth
- `expected_value`: training-sample average indicator growth
- `impact_weight`: fitted bridge coefficient

The publisher then converts these rows into the country/indicator output contract:
- `site/data/us/gdp/latest.json`
- `site/data/us/gdp/history.csv`
- `site/data/us/gdp/contributions.csv`
- `site/data/us/gdp/release_impacts.csv`
- `site/data/us/gdp/metadata.json`

## Current limitations
- FRED observation dates are used as the data cutoff dates; the model does not yet track actual release timestamps.
- Missing within-quarter monthly observations are handled through the available quarterly average, not a vintage-aware ragged-edge method.
- The model is a baseline bridge regression, not yet a full dynamic-factor or mixed-frequency nowcast.
- Revisions and real-time data vintages are not modelled yet.
