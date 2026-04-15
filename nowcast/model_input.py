"""Load downloaded model-input scaffolds and shape them for publishing."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REQUIRED_MODEL_INPUT_COLUMNS = {
    "as_of_date",
    "reference_period",
    "baseline_nowcast",
    "series_code",
    "series_name",
    "release_date",
    "actual_value",
    "expected_value",
    "impact_weight",
    "category",
    "units",
}


@dataclass(frozen=True)
class SourceObservation:
    as_of_date: date
    reference_period: str
    baseline_nowcast: float
    series_code: str
    series_name: str
    release_date: date
    actual_value: float
    expected_value: float
    impact_weight: float
    category: str
    units: str
    release_status: str = "released"

    @property
    def surprise(self) -> float:
        return self.actual_value - self.expected_value

    @property
    def impact_on_nowcast(self) -> float:
        return self.surprise * self.impact_weight


@dataclass(frozen=True)
class ModelSnapshot:
    as_of_date: date
    reference_period: str
    nowcast_value: float
    prior_nowcast_value: float | None
    source_observations: tuple[SourceObservation, ...]

    @property
    def delta_vs_prior(self) -> float | None:
        if self.prior_nowcast_value is None:
            return None
        return self.nowcast_value - self.prior_nowcast_value


@dataclass(frozen=True)
class ModelRun:
    snapshots: tuple[ModelSnapshot, ...]

    @property
    def latest(self) -> ModelSnapshot:
        return self.snapshots[-1]


def default_model_input_path(country_code: str, input_dir: Path | str = "runs/input") -> Path:
    """Return the expected downloaded input path for a country."""

    return Path(input_dir) / country_code / "model_input.csv"


def fixture_model_input_path(country_code: str) -> Path:
    """Return the committed scaffold fixture path for a country."""

    return Path("tests") / "fixtures" / country_code / "model_input.csv"


def resolve_model_input_path(
    country_code: str,
    *,
    input_dir: Path | str = "runs/input",
    input_path: Path | str | None = None,
) -> Path:
    """Prefer downloaded input, then fall back to the committed scaffold fixture."""

    if input_path is not None:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"missing model input: {path}")
        return path

    downloaded_path = default_model_input_path(country_code, input_dir)
    if downloaded_path.exists():
        return downloaded_path

    fixture_path = fixture_model_input_path(country_code)
    if fixture_path.exists():
        return fixture_path

    raise FileNotFoundError(
        f"missing model input for {country_code}; expected {downloaded_path} or {fixture_path}"
    )


def load_model_run(path: Path | str, *, as_of: date | None = None) -> ModelRun:
    """Load source observations and calculate scaffold nowcast snapshots."""

    observations = _load_observations(Path(path))
    if as_of is not None:
        observations = [item for item in observations if item.as_of_date <= as_of]
    if not observations:
        raise ValueError(f"no model input observations available in {path}")

    snapshots: list[ModelSnapshot] = []
    for as_of_date in sorted({item.as_of_date for item in observations}):
        rows = [item for item in observations if item.as_of_date == as_of_date]
        reference_periods = {item.reference_period for item in rows}
        if len(reference_periods) != 1:
            raise ValueError(f"{path}: as_of_date {as_of_date} has multiple reference periods")
        baselines = {item.baseline_nowcast for item in rows}
        if len(baselines) != 1:
            raise ValueError(f"{path}: as_of_date {as_of_date} has multiple baseline_nowcast values")

        nowcast_value = round(rows[0].baseline_nowcast + sum(item.impact_on_nowcast for item in rows), 10)
        prior = snapshots[-1].nowcast_value if snapshots else None
        snapshots.append(
            ModelSnapshot(
                as_of_date=as_of_date,
                reference_period=rows[0].reference_period,
                nowcast_value=nowcast_value,
                prior_nowcast_value=prior,
                source_observations=tuple(sorted(rows, key=lambda item: (item.release_date, item.series_code))),
            )
        )

    return ModelRun(tuple(snapshots))


def _load_observations(path: Path) -> list[SourceObservation]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header row")
        missing = REQUIRED_MODEL_INPUT_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return [_row_to_observation(path, index, row) for index, row in enumerate(reader, start=2)]


def _row_to_observation(path: Path, index: int, row: dict[str, str]) -> SourceObservation:
    try:
        return SourceObservation(
            as_of_date=date.fromisoformat(row["as_of_date"]),
            reference_period=_required_text(path, index, row, "reference_period"),
            baseline_nowcast=float(row["baseline_nowcast"]),
            series_code=_required_text(path, index, row, "series_code"),
            series_name=_required_text(path, index, row, "series_name"),
            release_date=date.fromisoformat(row["release_date"]),
            actual_value=float(row["actual_value"]),
            expected_value=float(row["expected_value"]),
            impact_weight=float(row["impact_weight"]),
            category=_required_text(path, index, row, "category"),
            units=_required_text(path, index, row, "units"),
            release_status=row.get("release_status", "released").strip() or "released",
        )
    except ValueError as exc:
        raise ValueError(f"{path}: row {index} has invalid data: {exc}") from exc


def _required_text(path: Path, index: int, row: dict[str, str], field: str) -> str:
    value = row[field].strip()
    if not value:
        raise ValueError(f"{path}: row {index} field {field} is required")
    return value
