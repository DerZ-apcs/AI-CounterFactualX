from itertools import product

import pytest

from core.constraints import Constraints, evaluate_feasibility
from core.distance import normalized_manhattan
from core.generator import evaluate_candidate, generate_counterfactuals, select_recommendation
from core.model import Application, predict


def test_default_candidates_are_generated_and_ranked():
    original = Application()
    candidates = generate_counterfactuals(original)
    assert [c.application for c in candidates] == [Application(25, 3, 0), Application(25, 2, 1),
                                                 Application(24, 3, 1), Application(25, 3, 1)]
    assert [c.distance for c in candidates] == pytest.approx([.3, 1.1, 1.2, 1.3])
    assert [c.sparsity for c in candidates] == [2, 2, 2, 3]
    assert len({c.application for c in candidates}) == len(candidates)
    assert all(c.valid and c.application != original for c in candidates)
    assert all(c.application.certification in (0, 1) for c in candidates)


def test_continuous_values_and_no_unnecessary_satisfied_condition_changes():
    original = Application(25.12345, 2.98765, 0)
    candidates = generate_counterfactuals(original)
    best = select_recommendation(candidates, enforce_feasibility=False)
    assert best.application == Application(25.12345, 3, 0)
    assert best.distance == pytest.approx(.01235 / 5)
    assert all(c.application.income == original.income for c in candidates)
    assert candidates != generate_counterfactuals(Application())


@pytest.mark.parametrize("original", [Application(25, 3, 0), Application(25, 2, 1), Application(24, 3, 1)])
def test_already_accepted(original):
    assert generate_counterfactuals(original) == []


def test_lambda_is_diagnostic_not_a_validity_tradeoff():
    original = Application(0, 0, 0)
    for penalty in (0, .01, 10):
        candidates = generate_counterfactuals(original, lambda_value=penalty)
        assert all(c.valid and c.objective == c.distance for c in candidates)
        assert select_recommendation(candidates, enforce_feasibility=False).application == Application(0, 3, 1)
    assert evaluate_candidate(original, original, lambda_value=.01).objective == .01
    # Even lambda=10 need not dominate distance with user-selected scales.
    candidates = generate_counterfactuals(original, normalization={"income": .01, "experience": .01, "certification": .01})
    assert candidates[0].distance > 10
    assert select_recommendation(candidates, enforce_feasibility=False).valid


def test_normalization_changes_ranking():
    candidates = generate_counterfactuals(Application(), normalization={"income": 10, "experience": .1, "certification": 1})
    assert candidates[0].application == Application(25, 2, 1)


@pytest.mark.parametrize("penalty", [-1, float("nan"), float("inf")])
def test_invalid_lambda(penalty):
    with pytest.raises(ValueError):
        generate_counterfactuals(Application(), lambda_value=penalty)


def test_exact_search_dominates_independent_continuous_probe_points():
    """A finite probe is a regression check, not the proof of optimality."""
    for original in (Application(24.17, 2.87, 0), Application(12.3, 4.2, 0), Application(0, 0, 1)):
        limits = Constraints(20, 2, True)
        generated = generate_counterfactuals(original, constraints=limits)
        for constrained in (False, True):
            best = select_recommendation(generated, enforce_feasibility=constrained)
            for income, experience, cert in product(
                [original.income, 25, 25.013, 40.7],
                [original.experience, 3, 3.019, 5.73], [0, 1]
            ):
                point = Application(income, experience, cert)
                if not predict(point) or (constrained and not evaluate_feasibility(original, point, limits).feasible):
                    continue
                assert best is not None
                assert best.distance <= normalized_manhattan(original, point) + 1e-12
