"""Adapter types for publishing G10 DFM outputs through the existing site contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nowcast.model_input import ModelRun, ModelSnapshot, SourceObservation


@dataclass(frozen=True)
class G10NowcastPoint:
    iso: str
    target: str
    vintage_date: date
    impact_date: str
    nowcast: float
    stderr: float | None = None


@dataclass(frozen=True)
class G10NewsImpact:
    series_id: str
    series_name: str
    release_date: date
    actual_value: float
    expected_value: float
    impact: float
    category: str = "dfm news"
    status: str = "new_release"
    source_url: str = ""


def g10_points_to_model_run(
    points: list[G10NowcastPoint],
    *,
    news: dict[date, list[G10NewsImpact]] | None = None,
) -> ModelRun:
    """Convert DFM nowcast/news rows into the current publisher's model input shape.

    This keeps the static website contract stable while the underlying model
    migrates from the interim US component bridge to the G10 DynamicFactorMQ
    pipeline.
    """

    if not points:
        raise ValueError("at least one G10 nowcast point is required")
    ordered = sorted(points, key=lambda point: point.vintage_date)
    baseline = ordered[0].nowcast
    snapshots = []
    prior: float | None = None
    for point in ordered:
        impacts = (news or {}).get(point.vintage_date, [])
        if not impacts:
            impacts = [
                G10NewsImpact(
                    series_id=point.target,
                    series_name=point.target.upper(),
                    release_date=point.vintage_date,
                    actual_value=point.nowcast,
                    expected_value=baseline,
                    impact=point.nowcast - baseline,
                    category="dfm nowcast",
                    status="carried_forward",
                )
            ]
        observations = tuple(
            SourceObservation(
                as_of_date=point.vintage_date,
                reference_period=point.impact_date,
                baseline_nowcast=baseline,
                series_code=impact.series_id,
                series_name=impact.series_name,
                release_date=impact.release_date,
                actual_value=impact.actual_value,
                expected_value=impact.expected_value,
                impact_weight=_impact_weight(impact),
                category=impact.category,
                units="percentage points",
                release_status=impact.status,
                source_url=impact.source_url,
            )
            for impact in impacts
        )
        snapshots.append(
            ModelSnapshot(
                as_of_date=point.vintage_date,
                reference_period=point.impact_date,
                nowcast_value=point.nowcast,
                prior_nowcast_value=prior,
                source_observations=observations,
            )
        )
        prior = point.nowcast
    return ModelRun(tuple(snapshots))


def _impact_weight(impact: G10NewsImpact) -> float:
    surprise = impact.actual_value - impact.expected_value
    if surprise == 0:
        return 0.0
    return impact.impact / surprise
