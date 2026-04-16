"""Thin wrapper around statsmodels DynamicFactorMQ."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DFMOptions:
    factor_orders: int = 2
    standardize: bool = True
    idiosyncratic_ar1: bool = True
    maxiter: int = 500
    tolerance: float = 1e-6


def build_factor_mapping(series_blocks: dict[str, list[str]]) -> dict[str, list[str]]:
    """Ensure each series loads on the global factor plus configured blocks."""

    factors: dict[str, list[str]] = {}
    for series_id, blocks in series_blocks.items():
        ordered = ["global", *[block for block in blocks if block != "global"]]
        factors[series_id] = list(dict.fromkeys(ordered))
    return factors


def fit_dynamic_factor_mq(
    monthly: Any,
    *,
    quarterly: Any | None = None,
    factors: dict[str, list[str]] | None = None,
    factor_multiplicities: dict[str, int] | None = None,
    options: DFMOptions | None = None,
) -> Any:
    """Fit the spec-approved mixed-frequency DFM.

    Statsmodels is imported lazily so the rest of the repo can run lightweight
    contract/site tests in environments where the heavy model dependency has
    not yet been installed.
    """

    try:
        from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
    except ImportError as exc:
        raise RuntimeError(
            "statsmodels>=0.14 is required for the G10 DynamicFactorMQ model. "
            "Install project dependencies with `pip install -e .`."
        ) from exc

    resolved = options or DFMOptions()
    model = DynamicFactorMQ(
        monthly,
        endog_quarterly=quarterly,
        factors=factors,
        factor_multiplicities=factor_multiplicities,
        factor_orders=resolved.factor_orders,
        idiosyncratic_ar1=resolved.idiosyncratic_ar1,
        standardize=resolved.standardize,
    )
    return model.fit(maxiter=resolved.maxiter, tolerance=resolved.tolerance, disp=False)


def statsmodels_available() -> bool:
    try:
        from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ  # noqa: F401
    except ImportError:
        return False
    return True

