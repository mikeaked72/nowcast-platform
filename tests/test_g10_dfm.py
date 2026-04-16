from __future__ import annotations

import pytest

import pandas as pd

from nowcast.g10.dfm import DFMOptions, build_factor_mapping, fit_dynamic_factor_mq, load_panel_and_fit, statsmodels_available


def test_build_factor_mapping_adds_global_once() -> None:
    assert build_factor_mapping({"INDPRO": ["real"], "PAYEMS": ["global", "labour"]}) == {
        "INDPRO": ["global", "real"],
        "PAYEMS": ["global", "labour"],
    }


def test_fit_dynamic_factor_mq_reports_missing_statsmodels_cleanly() -> None:
    if statsmodels_available():
        pytest.skip("statsmodels is installed; smoke fit belongs in replay tests")
    with pytest.raises(RuntimeError, match="statsmodels"):
        fit_dynamic_factor_mq([])


@pytest.mark.skipif(not statsmodels_available(), reason="statsmodels is not installed")
def test_load_panel_and_fit_smoke_when_statsmodels_available(tmp_path) -> None:
    monthly = pd.DataFrame(
        {
            "INDPRO": [1.0, 1.2, 1.1, 1.3, 1.4, 1.5],
            "PAYEMS": [0.5, 0.6, 0.7, 0.8, 0.7, 0.9],
        },
        index=pd.date_range("2025-01-01", periods=6, freq="MS"),
    )
    path = tmp_path / "monthly.parquet"
    monthly.to_parquet(path)
    results = load_panel_and_fit(
        monthly_path=str(path),
        series_blocks={"INDPRO": ["real"], "PAYEMS": ["real"]},
        options=DFMOptions(factor_orders=1, maxiter=2, tolerance=1e-3),
    )
    assert hasattr(results, "model")
