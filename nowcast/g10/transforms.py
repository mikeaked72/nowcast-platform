"""FRED-MD/FRED-QD transformation codes."""

from __future__ import annotations

import math
from collections.abc import Iterable


def transform_values(values: Iterable[float | None], tcode: int) -> list[float | None]:
    """Apply a FRED-MD transformation code to one ordered series.

    Codes follow McCracken-Ng conventions:
    1 level, 2 first difference, 3 second difference, 4 log level,
    5 log difference, 6 second log difference, 7 change in growth rate.
    Missing or non-positive values required by a log transform produce ``None``.
    """

    raw = [None if value is None else float(value) for value in values]
    if tcode == 1:
        return raw
    if tcode == 2:
        return _diff(raw)
    if tcode == 3:
        return _diff(_diff(raw))
    if tcode == 4:
        return [_log_or_none(value) for value in raw]
    if tcode == 5:
        return _diff([_log_or_none(value) for value in raw])
    if tcode == 6:
        return _diff(_diff([_log_or_none(value) for value in raw]))
    if tcode == 7:
        growth = _ratio_growth(raw)
        return _diff(growth)
    raise ValueError(f"unsupported FRED transformation code {tcode}")


def _diff(values: list[float | None]) -> list[float | None]:
    output: list[float | None] = [None]
    for current, prior in zip(values[1:], values[:-1]):
        output.append(None if current is None or prior is None else current - prior)
    return output


def _ratio_growth(values: list[float | None]) -> list[float | None]:
    output: list[float | None] = [None]
    for current, prior in zip(values[1:], values[:-1]):
        if current is None or prior is None or prior == 0:
            output.append(None)
        else:
            output.append(current / prior - 1.0)
    return output


def _log_or_none(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return math.log(value)

