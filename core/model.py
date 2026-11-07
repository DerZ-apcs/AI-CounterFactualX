"""Synthetic screening model: acceptance requires two of three conditions."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real

INCOME_THRESHOLD = 25.0
EXPERIENCE_THRESHOLD = 3.0
FEATURES = ("income", "experience", "certification")


def nonnegative_finite(value: float, name: str) -> None:
    """Reject negative, nonnumeric, boolean, and nonfinite numeric inputs."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite nonnegative number.")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number.")


@dataclass(frozen=True)
class Application:
    """Predictive features and an optional immutable, nonpredictive birth year."""

    income: float = 24.0
    experience: float = 2.0
    certification: int = 0
    birth_year: int | None = None

    def __post_init__(self) -> None:
        nonnegative_finite(self.income, "Income")
        nonnegative_finite(self.experience, "Experience")
        if isinstance(self.certification, bool) or self.certification not in (0, 1):
            raise ValueError("Certification must be binary: 0 or 1.")
        if self.birth_year is not None and (
            isinstance(self.birth_year, bool)
            or not isinstance(self.birth_year, int)
            or self.birth_year <= 0
        ):
            raise ValueError("Birth year must be a positive integer or None.")


def condition_results(application: Application) -> dict[str, bool]:
    """Return the individual threshold tests used by the classifier."""
    return {
        "income": application.income >= INCOME_THRESHOLD,
        "experience": application.experience >= EXPERIENCE_THRESHOLD,
        "certification": application.certification == 1,
    }


def predict(application: Application) -> int:
    """Return 1 (Accepted) if at least two conditions pass; otherwise 0."""
    return int(sum(condition_results(application).values()) >= 2)
