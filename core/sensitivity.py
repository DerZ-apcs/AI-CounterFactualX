"""Reassess cached enumeration points without changing the classifier or search.

Use enumerate_search(original) once with default scales to establish identities.
Reassessment preserves those IDs while sorting by the current metric. The V2
enumeration API retains its original rank-based naming for compatibility.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace

from core.constraints import Constraints, evaluate_feasibility
from core.distance import NORMALIZATION, validate_normalization
from core.generator import SearchTrace, candidate_order, evaluate_candidate, select_recommendation
from core.model import Application, FEATURES, EXPERIENCE_THRESHOLD, INCOME_THRESHOLD, nonnegative_finite


def reassess_trace(
    baseline: SearchTrace,
    *,
    normalization: Mapping[str, float] | None = None,
    lambda_value: float = 10.0,
    constraints: Constraints | None = None,
) -> SearchTrace:
    """Reuse exactly the cached applications; recompute metrics and feasibility.

    No product, threshold generation, or additional candidate geometry is used.
    The original/rejected points remain in the trace, never in recommendations.
    """
    factors = validate_normalization(normalization)
    nonnegative_finite(lambda_value, "Lambda")
    evaluated = tuple(
        evaluate_candidate(
            baseline.original, item.application, normalization=factors,
            lambda_value=lambda_value, constraints=constraints, candidate_id=item.candidate_id,
        )
        for item in baseline.evaluated
    )
    candidates = tuple(sorted(
        (item for item in evaluated if item.valid and item.application != baseline.original),
        key=candidate_order,
    ))
    return SearchTrace(baseline.original, baseline.options, evaluated, candidates)


def ranking_insight(baseline: SearchTrace, current: SearchTrace, normalization: Mapping[str, float]) -> str:
    """Explain an identity-based change against default scales, including ties."""
    factors = validate_normalization(normalization)
    before = select_recommendation(baseline.candidates, enforce_feasibility=False)
    after = select_recommendation(current.candidates, enforce_feasibility=False)
    if before is None or after is None:
        return "Already Accepted · No recourse needed."
    changes = [f"{name.title()} changes cost {'more' if factors[name] < NORMALIZATION[name] else 'less'}"
               for name in FEATURES if factors[name] != NORMALIZATION[name]]
    effect = "; ".join(changes) or "Default metric"
    if before.application == after.application:
        return f"Optimal CF unchanged: {after.candidate_id} · {effect}."
    old_point_now = next(item for item in current.candidates if item.application == before.application)
    if old_point_now.distance == after.distance:
        return f"Equal-distance optima · Tie-break selects {after.candidate_id}."
    return f"Optimal CF changed: {before.candidate_id} → {after.candidate_id} · {effect}."


@dataclass(frozen=True)
class ThresholdCost:
    """Minimum nondecreasing change to make one condition pass."""

    feature: str
    original: float
    required: float
    cost: float
    reachable: bool
    reasons: tuple[str, ...]


def threshold_costs(
    original: Application,
    normalization: Mapping[str, float] | None = None,
    *,
    constraints: Constraints | None = None,
    enforce_feasibility: bool = True,
) -> tuple[ThresholdCost, ...]:
    """Costs/reachability for explanation only; selection uses the full trace."""
    factors = validate_normalization(normalization)
    thresholds = (INCOME_THRESHOLD, EXPERIENCE_THRESHOLD, 1)
    costs = []
    for name, threshold in zip(FEATURES, thresholds):
        before = getattr(original, name)
        required = max(before, threshold)
        point = replace(original, **{name: required})
        feasibility = evaluate_feasibility(original, point, constraints)
        reachable = feasibility.immutable_preserved and (not enforce_feasibility or feasibility.feasible)
        costs.append(ThresholdCost(name, before, required, (required - before) / factors[name],
                                   reachable, feasibility.violations if enforce_feasibility else ()))
    return tuple(costs)
