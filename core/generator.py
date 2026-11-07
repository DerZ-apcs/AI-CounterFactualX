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
    factors = validate_normalization(normalization)
    nonnegative_finite(lambda_value, "Lambda")
    if predict(original) == TARGET:
        return []
    incomes = sorted({original.income, max(original.income, INCOME_THRESHOLD)})
    experiences = sorted(
        {original.experience, max(original.experience, EXPERIENCE_THRESHOLD)}
    )
    certifications = sorted({original.certification, 1})
    candidates = []
    for income, experience, certification in product(incomes, experiences, certifications):
        application = Application(income, experience, certification, original.birth_year)
        if application == original or predict(application) != TARGET:
            continue
        candidates.append(
            evaluate_candidate(
                original,
                application,
                normalization=factors,
                lambda_value=lambda_value,
                constraints=constraints,
            )
        )
    candidates.sort(
        key=lambda item: (
            item.distance,
            item.sparsity,
            item.application.income,
            item.application.experience,
            item.application.certification,
        )
    )
    return [replace(item, candidate_id=f"CF{index}") for index, item in enumerate(candidates, 1)]


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
