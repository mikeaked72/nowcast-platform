.PHONY: help install daily replay refit test lint typecheck ci test-vintage test-replay-smoke site-preview validate clean

help:
	@echo "Targets:"
	@echo "  install              pip install -e '.[dev]'"
	@echo "  daily                future G10 daily loop placeholder"
	@echo "  replay COUNTRY=US    future G10 historical replay placeholder"
	@echo "  refit COUNTRY=US     future full DFM refit placeholder"
	@echo "  test                 pytest -q"
	@echo "  lint                 ruff check ."
	@echo "  typecheck            mypy nowcast"
	@echo "  validate             validate generated site outputs"
	@echo "  site-preview         python -m http.server 3000 -d site"

install:
	pip install -e '.[dev]'

daily:
	python -m nowcast.cli g10-daily

replay:
	python -m nowcast.cli g10-replay --iso $(or $(COUNTRY),US) $(if $(START),--start $(START)) $(if $(END),--end $(END))

refit:
	python -m nowcast.cli g10-refit --iso $(or $(COUNTRY),US)

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy nowcast

ci: test lint typecheck

test-vintage:
	pytest -q tests/test_g10_transforms.py tests/test_g10_vintage.py tests/test_fred_md_loader.py

test-replay-smoke:
	pytest -q -m "not slow and not network" tests/test_g10_dfm.py

validate:
	python scripts/validate_outputs.py --countries us,au,de,br --publish-dir site/data

site-preview:
	python -m http.server 3000 -d site

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
