import pytest

from core.distance import changed_features, distance_contributions, normalized_manhattan, sparsity
from core.model import Application


@pytest.mark.parametrize(
    "point,expected", [((25, 3, 0), .30), ((25, 2, 1), 1.10),
                       ((24, 3, 1), 1.20), ((25, 3, 1), 1.30), ((500, 3, 0), 47.80)],
)
def test_worked_distances(point, expected):
    assert normalized_manhattan(Application(), Application(*point)) == pytest.approx(expected)


def test_change_metrics_and_immutable_exclusion():
    original, candidate = Application(birth_year=1990), Application(25, 3, 0, 2000)
    assert sparsity(original, candidate) == 2
    assert distance_contributions(original, candidate) == pytest.approx(
        {"income": .1, "experience": .2, "certification": 0}
    )
    assert changed_features(original, candidate) == (
        "Income: 24 → 25 (+1 million VND/month)", "Experience: 2 → 3 (+1 year)"
    )


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_invalid_normalization_values(value):
    with pytest.raises(ValueError):
        normalized_manhattan(Application(), Application(25, 3, 0),
                             {"income": value, "experience": 5, "certification": 1})


@pytest.mark.parametrize("factors", [{}, {"income": 10},
                                    {"income": 10, "experience": 5, "certification": 1, "extra": 1}])
def test_missing_or_extra_normalization_keys(factors):
    with pytest.raises(ValueError):
        normalized_manhattan(Application(), Application(), factors)


def test_zero_distance_and_custom_scales():
    assert normalized_manhattan(Application(), Application()) == 0
    assert normalized_manhattan(Application(), Application(25, 3, 0),
                                {"income": 1, "experience": 1, "certification": 2}) == 2
