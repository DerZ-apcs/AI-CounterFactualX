import pytest

from core.model import Application, condition_results, predict


@pytest.mark.parametrize(
    "values,expected",
    [((24, 2, 0), 0), ((25, 3, 0), 1), ((25, 2, 1), 1), ((24, 3, 1), 1),
     ((25, 0, 0), 0), ((0, 3, 0), 0), ((0, 0, 1), 0), ((25, 3, 1), 1)],
)
def test_predictions(values, expected):
    assert predict(Application(*values)) == expected


def test_default_conditions_and_birth_year_independence():
    assert sum(condition_results(Application()).values()) == 0
    assert predict(Application(25, 3, 0, 1990)) == predict(Application(25, 3, 0, 2000))


@pytest.mark.parametrize("certification", [-1, 2, 0.5, "1", None, True, float("nan")])
def test_invalid_certification(certification):
    with pytest.raises(ValueError, match="binary"):
        Application(certification=certification)


@pytest.mark.parametrize("feature", ["income", "experience"])
@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf"), "25", True])
def test_invalid_numeric_features(feature, value):
    with pytest.raises(ValueError):
        Application(**{feature: value})


def test_exact_continuous_threshold_boundary():
    assert predict(Application(24.999999999, 3, 0)) == 0
    assert predict(Application(25, 3, 0)) == 1
