from __future__ import annotations

from datetime import date

import pytest

from nowcast.g10.site_adapter import G10NewsImpact, G10NowcastPoint, g10_points_to_model_run


def test_g10_points_to_model_run_preserves_nowcast_and_news() -> None:
    run = g10_points_to_model_run(
        [
            G10NowcastPoint("US", "gdp", date(2026, 3, 1), "2026Q1", 2.0),
            G10NowcastPoint("US", "gdp", date(2026, 4, 1), "2026Q1", 2.4),
        ],
        news={
            date(2026, 4, 1): [
                G10NewsImpact(
                    series_id="INDPRO",
                    series_name="Industrial production",
                    release_date=date(2026, 4, 1),
                    actual_value=0.5,
                    expected_value=0.1,
                    impact=0.4,
                    category="real",
                    source_url="https://fred.stlouisfed.org/series/INDPRO",
                )
            ]
        },
    )

    assert run.latest.nowcast_value == 2.4
    assert run.latest.delta_vs_prior == pytest.approx(0.4)
    assert run.latest.source_observations[0].series_code == "INDPRO"
    assert run.latest.source_observations[0].impact_on_nowcast == 0.4
    assert run.latest.source_observations[0].source_url == "https://fred.stlouisfed.org/series/INDPRO"
