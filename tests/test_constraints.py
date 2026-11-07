from dataclasses import replace

import pytest

from core.constraints import Constraints, evaluate_feasibility
from core.generator import evaluate_candidate, generate_counterfactuals, select_recommendation
from core.model import Application


def test_default_recommendations():
    candidates = generate_counterfactuals(Application())
    assert select_recommendation(candidates, enforce_feasibility=False).application == Application(25, 3, 0)
    assert select_recommendation(candidates).application == Application(25, 2, 1)
    assert [c.feasibility.feasible for c in candidates] == [False, True, False, False]


def test_no_feasible_counterfactual_and_disabled_limits():
    candidates = generate_counterfactuals(
        Application(), constraints=Constraints(can_obtain_certification=False)
    )
    assert select_recommendation(candidates) is None
    assert select_recommendation(candidates, enforce_feasibility=False) is not None


def test_limits_relative_to_current_original():
    assert evaluate_feasibility(Application(20, 2.9, 0), Application(25, 3, 0)).feasible
    assert not evaluate_feasibility(Application(19, 2.9, 0), Application(25, 3, 0)).feasible


def test_zero_increases_and_existing_certification():
    limits = Constraints(0, 0, True)
    assert select_recommendation(generate_counterfactuals(Application(), constraints=limits)) is None
    candidates = generate_counterfactuals(Application(25, 0, 0), constraints=limits)
    assert select_recommendation(candidates).application == Application(25, 0, 1)
    assert not evaluate_feasibility(Application(), Application(24 + 1e-10, 2, 0), limits).feasible
    assert evaluate_feasibility(Application(24, 2, 1), Application(25, 2, 1), Constraints(5, 0, False)).feasible


def test_experience_cannot_decrease():
    assessment = evaluate_feasibility(Application(24, 4, 0), Application(25, 3, 0))
    assert not assessment.feasible
    assert "Experience cannot decrease." in assessment.violations


def test_immutable_cannot_change_even_with_practical_limits_disabled():
    original = Application(birth_year=1990)
    candidates = generate_counterfactuals(original)
    assert all(c.application.birth_year == 1990 for c in candidates)
    illegal = evaluate_candidate(original, Application(25, 3, 0, 2000))
    assert not illegal.feasibility.immutable_preserved
    assert select_recommendation([illegal], enforce_feasibility=False) is None
    assert select_recommendation([replace(illegal, prediction=0)]) is None


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_limits(value):
    with pytest.raises(ValueError):
        Constraints(max_income_increase=value)
    with pytest.raises(ValueError):
        Constraints(max_experience_increase=value)
