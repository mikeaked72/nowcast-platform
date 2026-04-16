"""Vintage integrity checks for model-ready country panels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


REQUIRED_VINTAGE_COLUMNS = (
    "date",
    "series_id",
    "value",
    "freq",
    "tcode",
    "vintage_date",
    "vintage_kind",
)
VALID_VINTAGE_KINDS = {"real", "pseudo"}


@dataclass(frozen=True)
class VintageIntegrity:
    row_count: int
    series_count: int
    vintage_date: date
    vintage_kind: str


def validate_vintage_frame(frame: Any, *, as_of: date | None = None) -> VintageIntegrity:
    """Validate the spec's tidy vintage frame invariant.

    ``frame`` is intentionally duck-typed so tests and early loaders can use
    pandas without making this module import pandas at import time.
    """

    missing = [column for column in REQUIRED_VINTAGE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"vintage frame missing columns {missing}")
    key_columns = ["date", "series_id", "freq", "tcode", "vintage_date", "vintage_kind"]
    if bool(frame[key_columns].isnull().any().any()):
        raise ValueError("vintage frame has nulls in key columns")

    vintage_dates = {_to_date(value) for value in frame["vintage_date"].unique()}
    if len(vintage_dates) != 1:
        raise ValueError("vintage frame must contain exactly one vintage_date")
    vintage_date = next(iter(vintage_dates))
    if as_of is not None and vintage_date > as_of:
        raise ValueError(f"vintage_date {vintage_date} is after as_of {as_of}")

    kinds = {str(value) for value in frame["vintage_kind"].unique()}
    if len(kinds) != 1:
        raise ValueError("vintage frame may not mix real and pseudo vintages")
    vintage_kind = next(iter(kinds))
    if vintage_kind not in VALID_VINTAGE_KINDS:
        raise ValueError(f"unsupported vintage_kind {vintage_kind}")

    return VintageIntegrity(
        row_count=int(len(frame)),
        series_count=int(frame["series_id"].nunique()),
        vintage_date=vintage_date,
        vintage_kind=vintage_kind,
    )


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])

