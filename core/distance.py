"""Manually normalized Manhattan distance and human-readable change metrics."""

from collections.abc import Mapping
from math import isfinite
from types import MappingProxyType

from core.model import Application, FEATURES, nonnegative_finite

# Synthetic educational scales, NOT dataset MAD estimates.
NORMALIZATION: Mapping[str, float] = MappingProxyType(
    {"income": 10.0, "experience": 5.0, "certification": 1.0}
)


def validate_normalization(
    normalization: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Require exactly one finite, strictly positive scale per feature."""
    factors = dict(NORMALIZATION if normalization is None else normalization)
    if set(factors) != set(FEATURES):
        raise ValueError(f"Normalization must contain exactly {FEATURES}.")
    for feature, factor in factors.items():
        nonnegative_finite(factor, f"{feature} normalization")
        if factor == 0:
            raise ValueError("Normalization factors must be strictly positive.")
    return factors


def distance_contributions(
    original: Application,
    candidate: Application,
    normalization: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return |x_j - x'_j| / scale_j for each predictive feature."""
    factors = validate_normalization(normalization)
    contributions = {
        feature: abs(getattr(original, feature) - getattr(candidate, feature))
        / factors[feature]
        for feature in FEATURES
    }
    if not isfinite(sum(contributions.values())):
        raise ValueError("Distance exceeds floating-point range; use larger normalization scales.")
    return contributions


def normalized_manhattan(
    original: Application,
    candidate: Application,
    normalization: Mapping[str, float] | None = None,
) -> float:
    """Sum predictive-feature contributions; contextual birth year is excluded."""
    return sum(distance_contributions(original, candidate, normalization).values())


def sparsity(original: Application, candidate: Application) -> int:
    """Count exact predictive-feature changes (no grid or rounding tolerance)."""
    return sum(getattr(original, name) != getattr(candidate, name) for name in FEATURES)


def changed_features(original: Application, candidate: Application) -> tuple[str, ...]:
    """Describe changes in original units, including direction and magnitude."""
    descriptions = []
    labels = {
        "income": ("Income", " million VND/month"),
        "experience": ("Experience", " years"),
        "certification": ("Certification", ""),
    }
    for feature in FEATURES:
        before, after = getattr(original, feature), getattr(candidate, feature)
        if before != after:
            label, unit = labels[feature]
            if feature == "experience" and abs(after - before) == 1:
                unit = " year"
            descriptions.append(
                f"{label}: {before:g} → {after:g} ({after - before:+g}{unit})"
            )
    return tuple(descriptions)
