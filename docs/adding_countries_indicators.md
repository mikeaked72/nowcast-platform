# Adding countries and indicators

## Add a country

1. Create `country_packs/{country_code}/country.json`.
2. Include country metadata and the enabled indicator list.
3. Run pack validation:

```powershell
python -m nowcast.cli run --country us --skip-model-run --no-validate
```

Example:

```json
{
  "code": "au",
  "name": "Australia",
  "default_target": "GDP QoQ saar",
  "target_code": "gdp_qoq_saar",
  "target_name": "GDP QoQ saar",
  "units": "percent",
  "enabled": true,
  "indicators": ["gdp", "inflation"]
}
```

Country-specific configuration belongs in `country_packs/`. Do not add country-specific branches to generic package files unless the behaviour is parameterised through packs.

## Add an indicator

1. Add indicator metadata in `nowcast/publish.py` under `INDICATORS`.
2. Add the indicator code to each country pack that supports it.
3. Teach the model pipeline to write that indicator's run data, or add deterministic sample data while the real model is pending.
4. Regenerate site data:

```powershell
python scripts\run_all_countries.py --countries us,au,de,br --publish-dir site\data
```

5. Validate the output contract:

```powershell
python scripts\validate_outputs.py --countries us,au,de,br --publish-dir site\data
```

## Model-output mapping

Future model code should produce a country/indicator run object that maps cleanly into:

- `latest.json`: one current estimate
- `history.csv`: estimate evolution over time
- `contributions.csv`: component-level drivers
- `release_impacts.csv`: release-level surprises and impacts
- `metadata.json`: display, methodology, FAQ, cadence, and download metadata

The site is static and only consumes those published files. It should not contain modelling logic or schema repair logic.
