from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from nowcast.g10.vintage import validate_vintage_frame


def _frame(**overrides: object) -> pd.DataFrame:
    payload = {
        "date": [date(2026, 1, 1), date(2026, 2, 1)],
        "series_id": ["A", "A"],
        "value": [1.0, 2.0],
        "freq": ["M", "M"],
        "tcode": [5, 5],
        "vintage_date": [date(2026, 3, 1), date(2026, 3, 1)],
        "vintage_kind": ["real", "real"],
    }
    payload.update(overrides)
    return pd.DataFrame(payload)


def test_validate_vintage_frame_accepts_single_real_vintage() -> None:
    result = validate_vintage_frame(_frame(), as_of=date(2026, 3, 1))
    assert result.row_count == 2
    assert result.series_count == 1
    assert result.vintage_date == date(2026, 3, 1)
    assert result.vintage_kind == "real"


def test_validate_vintage_frame_rejects_mixed_kind() -> None:
    with pytest.raises(ValueError, match="may not mix"):
        validate_vintage_frame(_frame(vintage_kind=["real", "pseudo"]))


def test_validate_vintage_frame_rejects_future_vintage() -> None:
    with pytest.raises(ValueError, match="after as_of"):
        validate_vintage_frame(_frame(), as_of=date(2026, 2, 28))


def test_validate_vintage_frame_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_vintage_frame(_frame().drop(columns=["tcode"]))

