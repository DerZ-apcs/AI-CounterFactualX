from unittest.mock import patch

import pytest

from core.constraints import Constraints, evaluate_feasibility
from core.generator import enumerate_search, evaluate_candidate, select_recommendation
from core.model import Application
from core.scenarios import evaluate_scenarios, scenario_definitions


def test_required_scenarios_and_explicit_empty_state():
    results = evaluate_scenarios(enumerate_search(Application()))
    assert results["No Constraints"].recommendation.application == Application(25, 3, 0)
    assert results["No Constraints"].distance == pytest.approx(.3)
    assert results["3 Months"].recommendation.application == Application(25, 2, 1)
    assert results["3 Months"].distance == pytest.approx(1.1)
    assert results["No Certificate"].recommendation is None
    assert results["No Certificate"].distance is None
    assert results["No Certificate"].status == "No feasible CF"


def test_custom_does_not_modify_presets_or_input_and_does_not_regenerate():
    original = Application(24, 2, 0, 1998)
    baseline = enumerate_search(original)
    with patch("core.generator.product", side_effect=AssertionError("Unexpected regeneration")):
        results = evaluate_scenarios(baseline, custom=Constraints(1, 1, False))
    assert results["Custom"].recommendation.application == Application(25, 3, 0, 1998)
    assert results["3 Months"].recommendation.application == Application(25, 2, 1, 1998)
    assert results["No Certificate"].recommendation is None
    assert baseline.original == original == Application(24, 2, 0, 1998)


def test_scenario_comparison_uses_current_metric():
    baseline = enumerate_search(Application())
    results = evaluate_scenarios(baseline, normalization={"income": 10, "experience": .5, "certification": 1})
    assert results["No Constraints"].recommendation.application == results["3 Months"].recommendation.application
    assert results["No Constraints"].distance == pytest.approx(1.1)


@pytest.mark.parametrize("original", [Application(25, 2.9, 0), Application(24.3, 2.9, 0), Application(24, 2, 1)])
def test_comparison_updates_with_original_and_existing_certification(original):
    results = evaluate_scenarios(enumerate_search(original))
    assert results["No Certificate"].recommendation is not None
    assert all(result.trace.original == original for result in results.values())


def test_zero_limits_and_already_accepted():
    results = evaluate_scenarios(enumerate_search(Application()), custom=Constraints(0, 0, False))
    assert results["Custom"].recommendation is None
    accepted = evaluate_scenarios(enumerate_search(Application(25, 3, 0)))
    assert all(result.status == "Already Accepted" and result.distance is None and result.recommendation is None
               for result in accepted.values())


def test_scenario_domains_immutability_and_income_non_decrease():
    scenario = scenario_definitions()[1]
    assert not evaluate_feasibility(Application(30, 3, 0), Application(25, 3, 0), scenario.constraints).feasible
    # Mandatory immutability is enforced even by the unconstrained selector.
    illegal = evaluate_candidate(Application(birth_year=1990), Application(25, 3, 0, 2000))
    assert select_recommendation([illegal], enforce_feasibility=False) is None
    with pytest.raises(ValueError):
        Application(-1, 3, 0)
    with pytest.raises(ValueError):
        Application(25, 3, 2)
