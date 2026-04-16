from __future__ import annotations

import pytest

from nowcast.g10.dfm import build_factor_mapping, fit_dynamic_factor_mq, statsmodels_available


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

