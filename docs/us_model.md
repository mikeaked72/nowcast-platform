# US GDP nowcast model

## Purpose
This is the first component-based US GDP nowcast model. It is intentionally transparent and lightweight so the data, model run, publish step, and site contract can be exercised end to end before adding richer econometrics.

## Data source
The model downloads public FRED graph CSV files into `runs/source/us/fred/`.

Quarterly target and component series:
- `GDPC1`: real gross domestic product
- `PCDGCC96`, `PCNDGC96`, `PCESVC96`: real PCE component levels
- `PNFI`, `PRFI`: real private fixed investment component levels
- `A014RE1Q156NBEA`: change in private inventories contribution
- `EXPGSC1`, `IMPGSC1`: real exports and imports
- `FGCEC1`, `SLCEC1`: real government consumption and investment

Monthly and daily bridge inputs:
- `RSAFS`, `DSPIC96`, `PAYEMS`: consumer spending and income conditions
- `DGORDER`, `AMTMNO`, `INDPRO`: production and investment signals
- `HOUST`, `PERMIT`, `TTLCONS`, `TLRESCONS`, `TLNRESCONS`: housing and construction activity
- `BUSINV`, `ISRATIO`, `CMRMTSPL`: inventories, sales, and trade-related demand
- `DTWEXBGS`, `FEDFUNDS`: external and financial conditions

`runs/` remains local run data and should not be treated as committed source data.

## Model
The model is a component bridge for quarterly real GDP growth, expressed as quarter-over-quarter annualized growth where component targets are levels. It is GDPNow-inspired in structure, but is not an Atlanta Fed model and does not use Atlanta Fed branding or proprietary methods.

Monthly and daily indicators are converted to quarterly averages and then quarter-over-quarter annualized log growth rates. For each GDP expenditure component, a small ridge-regularized bridge regression maps the relevant source indicators to component growth or contribution history. Component forecasts are then aggregated with latest component-to-GDP weights. Imports receive a negative aggregation sign, and the private-inventory contribution is treated directly as percentage points.

For each run date, the model writes one row per GDP component to `runs/input/us/model_input.csv`:
- `baseline_nowcast`: aggregate fitted value using each component's expected value
- `actual_value`: component bridge forecast available as of the run date
- `expected_value`: component expected value from the training sample
- `impact_weight`: latest GDP-share aggregation weight for the component

The publisher then converts these rows into the country/indicator output contract:
- `site/data/us/gdp/latest.json`
- `site/data/us/gdp/history.csv`
- `site/data/us/gdp/contributions.csv`
- `site/data/us/gdp/release_impacts.csv`
- `site/data/us/gdp/metadata.json`

## Current limitations
- Approximate release lags are used for FRED source series; the model does not yet track official real-time release timestamps or vintages.
- Missing within-quarter monthly observations are handled through the available quarterly average, not a vintage-aware ragged-edge method.
- The model is a transparent component bridge, not yet a full dynamic-factor, Bayesian, or mixed-frequency nowcast.
- Revisions and real-time data vintages are not modelled yet.
