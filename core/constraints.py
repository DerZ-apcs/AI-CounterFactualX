"""Assumed three-month feasibility limits, measured relative to the original."""

from dataclasses import dataclass
from math import isclose

from core.model import Application, nonnegative_finite


@dataclass(frozen=True)
class Constraints:
    """Synthetic practical assumptions, not guarantees about employment outcomes."""

    max_income_increase: float = 5.0
    max_experience_increase: float = 0.25
    can_obtain_certification: bool = True
    income_cannot_decrease: bool = False

    def __post_init__(self) -> None:
        nonnegative_finite(self.max_income_increase, "Maximum income increase")
        nonnegative_finite(self.max_experience_increase, "Maximum experience increase")
        if not isinstance(self.can_obtain_certification, bool):
            raise ValueError("Certification permission must be a boolean.")
        if not isinstance(self.income_cannot_decrease, bool):
            raise ValueError("Income non-decrease policy must be a boolean.")


@dataclass(frozen=True)
class Feasibility:
    """Separate mandatory immutability from optional practical feasibility."""

    immutable_preserved: bool
    violations: tuple[str, ...]

    @property
    def feasible(self) -> bool:
        return not self.violations


def _exceeds(increase: float, limit: float) -> bool:
    # Avoid spurious failures from subtraction at an inclusive numeric boundary.
    # A zero limit is exact: even a tiny strictly positive increase is disallowed.
    return increase > limit and (
        limit == 0 or not isclose(increase, limit, rel_tol=1e-12, abs_tol=0)
    )


def evaluate_feasibility(
    original: Application,
    candidate: Application,
    constraints: Constraints | None = None,
) -> Feasibility:
    """Check validated domains, immutable context, and all practical limits.

    Applications enforce domains on construction. This assessment always reports
    practical feasibility, even when a caller elects not to enforce those limits.
    """
    limits = constraints if constraints is not None else Constraints()
    violations = []
    immutable_preserved = candidate.birth_year == original.birth_year
    if not immutable_preserved:
        violations.append("Birth year is immutable and must remain unchanged.")
    income_increase = candidate.income - original.income
    experience_increase = candidate.experience - original.experience
    if limits.income_cannot_decrease and income_increase < 0:
        violations.append("Income cannot decrease.")
    if _exceeds(income_increase, limits.max_income_increase):
        violations.append(
            f"Income increase {income_increase:g} exceeds the allowed "
            f"{limits.max_income_increase:g} million VND/month."
        )
    if experience_increase < 0:
        violations.append("Experience cannot decrease.")
    if _exceeds(experience_increase, limits.max_experience_increase):
        violations.append(
            f"Experience increase {experience_increase:g} exceeds the allowed "
            f"{limits.max_experience_increase:g} years."
        )
    if (
        original.certification == 0
        and candidate.certification == 1
        and not limits.can_obtain_certification
    ):
        violations.append("Obtaining certification is not allowed in this scenario.")
    return Feasibility(immutable_preserved, tuple(violations))
