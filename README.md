# Nowcast Platform

This repository builds multi-country macro nowcast outputs and publishes static
site artifacts for the dashboard in `site/`.

## Main Folders

- `nowcast/` - Python package for the nowcast model, publishing, and site output.
- `country_packs/` - country configuration.
- `pipeline/` - macro data download and processed-panel build scripts.
- `specs/` - macro data-store source mappings and technical notes.
- `site/` - static frontend.
- `site/data/` - generated dashboard payloads.
- `store/` - macro data-store manifest plus ignored raw/processed data.
- `docs/` - contracts and implementation notes.
- `tests/` - unit, smoke, and contract tests.

The original imported package is retained in `data_store_package/` as the source
handoff. Active integrated scripts are in `pipeline/` and `specs/`.

## Common Commands

```powershell
python -m pytest -q
python scripts\validate_outputs.py --countries us,au --publish-dir site\data
python -m http.server 3000 -d site
```

Macro data-store commands:

```powershell
.\.venv\Scripts\python.exe pipeline\update_fred.py
.\.venv\Scripts\python.exe pipeline\update_aus.py
.\.venv\Scripts\python.exe pipeline\update_international.py
.\.venv\Scripts\python.exe pipeline\build_processed.py
.\.venv\Scripts\python.exe pipeline\validate_data_store.py
```

Or run the data refresh end to end:

```powershell
.\.venv\Scripts\python.exe pipeline\update_all_data.py
```

See `docs/data_store.md` for the data-store status and known follow-ups.
