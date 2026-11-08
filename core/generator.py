"""Exact threshold-aware enumeration for this specific monotonic classifier.

For positive weighted L1 distance, an optimal accepted point only needs to keep
each original value or raise an unsatisfied condition to its exact threshold.
Any extra movement can be undone without losing acceptance or increasing cost.
Shrinking increases also preserves the practical upper-bound constraints used
here. This argument does not extend to arbitrary models or feasibility sets.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import product

from core.constraints import Constraints, Feasibility, evaluate_feasibility
from core.distance import (
    changed_features,
    distance_contributions,
    sparsity,
    validate_normalization,
)
from core.model import (
    Application,
    EXPERIENCE_THRESHOLD,
    INCOME_THRESHOLD,
    nonnegative_finite,
    predict,
)

TARGET = 1


@dataclass(frozen=True)
class Candidate:
    """One evaluated application, with validity independent of feasibility."""

    candidate_id: str
    application: Application
    prediction: int
    distance: float
    sparsity: int
    objective: float
    contributions: dict[str, float]
    changes: tuple[str, ...]
    feasibility: Feasibility

    @property
    def valid(self) -> bool:
        return self.prediction == TARGET


@dataclass(frozen=True)
class SearchTrace:
    """Actual enumeration, including unchanged/rejected points before filtering.

    ``evaluated`` follows itertools.product order. ``candidates`` is the same
    distance-ranked valid-only output exposed by generate_counterfactuals.
    An already-accepted original short-circuits with no enumerated points.
    """

    original: Application
    options: dict[str, tuple[float | int, ...]]
    evaluated: tuple[Candidate, ...]
    candidates: tuple[Candidate, ...]


def threshold_options(original: Application) -> dict[str, tuple[float | int, ...]]:
    """Expose the original enumeration rule without introducing a search grid."""
    return {
        "income": tuple(sorted({original.income, max(original.income, INCOME_THRESHOLD)})),
        "experience": tuple(sorted({original.experience, max(original.experience, EXPERIENCE_THRESHOLD)})),
        "certification": tuple(sorted({original.certification, 1})),
    }


def evaluate_candidate(
    original: Application,
    application: Application,
    *,
    normalization: Mapping[str, float] | None = None,
    lambda_value: float = 10.0,
    constraints: Constraints | None = None,
    candidate_id: str = "Example",
) -> Candidate:
    """Evaluate any domain-valid point, including an educational rejected point."""
    nonnegative_finite(lambda_value, "Lambda")
    contributions = distance_contributions(original, application, normalization)
    distance = sum(contributions.values())
    prediction = predict(application)
    return Candidate(
        candidate_id=candidate_id,
        application=application,
        prediction=prediction,
        distance=distance,
        sparsity=sparsity(original, application),
        objective=lambda_value * int(prediction != TARGET) + distance,
        contributions=contributions,
        changes=changed_features(original, application),
        feasibility=evaluate_feasibility(original, application, constraints),
    )


def generate_counterfactuals(
    original: Application,
    *,
    normalization: Mapping[str, float] | None = None,
    lambda_value: float = 10.0,
    constraints: Constraints | None = None,
) -> list[Candidate]:
    """Enumerate at most eight combinations, then rank target-valid changes.

    Already-accepted applications return an empty list: no recourse is needed.
    Practical feasibility does not hide candidates from the comparison table;
    it is enforced separately by select_recommendation.
    """
    return list(enumerate_search(
        original, normalization=normalization, lambda_value=lambda_value,
        constraints=constraints,
    ).candidates)


def enumerate_search(
    original: Application,
    *,
    normalization: Mapping[str, float] | None = None,
    lambda_value: float = 10.0,
    constraints: Constraints | None = None,
) -> SearchTrace:
    """Run the shared V1 enumeration with an inspectable computation trace.

    Evaluation of rejected points is diagnostic only: recommendation still
    filters the unchanged original and all non-target points before ranking.
    """
    factors = validate_normalization(normalization)
    nonnegative_finite(lambda_value, "Lambda")
    options = threshold_options(original)
    if predict(original) == TARGET:
        return SearchTrace(original, options, (), ())
    evaluated = []
    for index, (income, experience, certification) in enumerate(product(*options.values()), 1):
        application = Application(income, experience, certification, original.birth_year)
        evaluated.append(
            evaluate_candidate(
                original,
                application,
                normalization=factors,
                lambda_value=lambda_value,
                constraints=constraints,
                candidate_id="Original" if application == original else f"T{index}",
            )
        )
    candidates = [item for item in evaluated if item.application != original and item.valid]
    candidates.sort(
        key=lambda item: (
            item.distance,
            item.sparsity,
            item.application.income,
            item.application.experience,
            item.application.certification,
        )
    )
    ranked = tuple(replace(item, candidate_id=f"CF{index}") for index, item in enumerate(candidates, 1))
    identifiers = {item.application: item.candidate_id for item in ranked}
    evaluated = tuple(
        replace(item, candidate_id=identifiers.get(item.application, item.candidate_id))
        for item in evaluated
    )
    return SearchTrace(original, options, evaluated, ranked)


def select_recommendation(
    candidates: Sequence[Candidate], *, enforce_feasibility: bool = True
) -> Candidate | None:
    """Enforce target and immutability first, then minimize eligible distance.

    Lambda never trades target validity away. Practical limits alone may be
    ignored; domains are always enforced by Application construction.
    """
    eligible = [
        item
        for item in candidates
        if item.valid
        and item.feasibility.immutable_preserved
        and (not enforce_feasibility or item.feasibility.feasible)
    ]
    return min(eligible, key=lambda item: (item.distance, item.sparsity, item.candidate_id), default=None)
