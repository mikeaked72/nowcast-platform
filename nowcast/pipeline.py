"""Country pipeline orchestration for creating published nowcast outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from nowcast.publish import load_country_pack, publish_sample_country, validate_country_pack, write_countries_json
from nowcast.schemas import ValidationResult, validate_publish_dir
from nowcast.us_model import run_us_gdp_nowcast


@dataclass(frozen=True)
class CountryRunResult:
    country_code: str
    publish_dir: Path
    country_publish_dir: Path
    input_path: Path
    validation: ValidationResult


def parse_as_of(value: str | None) -> date | None:
    """Parse YYYY-MM-DD or YYYY-MM into a date."""

    if value is None:
        return None
    if len(value) == 7:
        year, month = (int(part) for part in value.split("-"))
        return _month_end(year, month)
    return date.fromisoformat(value)


def run_country_pipeline(
    country_code: str,
    *,
    publish_dir: Path | str = "site/data",
    packs_dir: Path | str = "country_packs",
    input_dir: Path | str = "runs/input",
    input_path: Path | str | None = None,
    source_dir: Path | str = "runs/source",
    as_of: date | None = None,
    skip_model_run: bool = False,
    download: bool = True,
    validate: bool = True,
) -> CountryRunResult:
    """Create model input, publish site payloads, and optionally validate them."""

    validate_country_pack(country_code, packs_dir)
    resolved_input_path = Path(input_path) if input_path is not None else None

    if country_code == "us" and resolved_input_path is None and not skip_model_run:
        resolved_input_path = run_us_gdp_nowcast(
            source_dir=Path(source_dir) / country_code / "fred",
            input_dir=Path(input_dir) / country_code,
            download=download,
        )

    country_publish_dir = publish_sample_country(
        country_code,
        Path(publish_dir),
        packs_dir=Path(packs_dir),
        input_dir=Path(input_dir),
        input_path=resolved_input_path,
        as_of=as_of,
    )

    validation = ValidationResult(())
    if validate:
        validation = validate_publish_dir(Path(publish_dir), countries=[country_code])
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))

    return CountryRunResult(
        country_code=country_code,
        publish_dir=Path(publish_dir),
        country_publish_dir=country_publish_dir,
        input_path=resolved_input_path or Path(input_dir) / country_code / "model_input.csv",
        validation=validation,
    )


def run_countries_pipeline(
    country_codes: list[str],
    *,
    publish_dir: Path | str = "site/data",
    packs_dir: Path | str = "country_packs",
    input_dir: Path | str = "runs/input",
    source_dir: Path | str = "runs/source",
    skip_model_run: bool = False,
    download: bool = True,
    validate: bool = True,
) -> list[CountryRunResult]:
    """Run the output pipeline for multiple countries."""

    if not country_codes:
        raise ValueError("at least one country is required")

    results = [
        run_country_pipeline(
            country_code,
            publish_dir=publish_dir,
            packs_dir=packs_dir,
            input_dir=input_dir,
            source_dir=source_dir,
            skip_model_run=skip_model_run,
            download=download,
            validate=False,
        )
        for country_code in country_codes
    ]

    packs = [load_country_pack(country_code, packs_dir) for country_code in country_codes]
    write_countries_json(Path(publish_dir), packs)

    if validate:
        validation = validate_publish_dir(Path(publish_dir), countries=country_codes)
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))

    return results


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    first_next_month = date(year, month + 1, 1)
    return date.fromordinal(first_next_month.toordinal() - 1)
