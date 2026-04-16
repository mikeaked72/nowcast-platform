from __future__ import annotations

import math

import pytest

from nowcast.g10.transforms import transform_values


def test_fred_tcode_level_and_differences() -> None:
    assert transform_values([1, 3, 6], 1) == [1.0, 3.0, 6.0]
    assert transform_values([1, 3, 6], 2) == [None, 2.0, 3.0]
    assert transform_values([1, 3, 6], 3) == [None, None, 1.0]


def test_fred_tcode_log_transforms() -> None:
    values = transform_values([1, math.e, math.e * math.e], 5)
    assert values[0] is None
    assert values[1] == pytest.approx(1.0)
    assert values[2] == pytest.approx(1.0)
    assert transform_values([1, -1, 2], 4) == [0.0, None, math.log(2)]


def test_fred_tcode_growth_rate_change() -> None:
    values = transform_values([100, 110, 132], 7)
    assert values[0] is None
    assert values[1] is None
    assert values[2] == pytest.approx(0.10)


def test_unknown_tcode_fails() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        transform_values([1, 2, 3], 99)

