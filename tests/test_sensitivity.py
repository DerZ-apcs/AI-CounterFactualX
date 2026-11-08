from unittest.mock import patch

import pytest

from core.constraints import Constraints
from core.generator import enumerate_search, select_recommendation
from core.model import Application, predict
from core.sensitivity import ranking_insight, reassess_trace, threshold_costs


def test_required_sensitivity_example_and_stable_identity():
    baseline = enumerate_search(Application())
    changed = reassess_trace(baseline, normalization={"income": 10, "experience": .5, "certification": 1})
    assert {item.candidate_id: item.distance for item in changed.candidates} == pytest.approx(
        {"CF1": 2.1, "CF2": 1.1, "CF3": 3, "CF4": 3.1})
    assert [item.candidate_id for item in changed.candidates] == ["CF2", "CF1", "CF3", "CF4"]
    assert select_recommendation(changed.candidates, enforce_feasibility=False).application == Application(25, 2, 1)
    assert select_recommendation(changed.candidates).application == Application(25, 2, 1)
    assert "CF1 → CF2" in ranking_insight(baseline, changed, {"income": 10, "experience": .5, "certification": 1})
    assert [item.prediction for item in changed.evaluated] == [item.prediction for item in baseline.evaluated]
    assert all(item.objective == item.distance for item in changed.candidates)
    restored = reassess_trace(baseline)
    assert restored.candidates == baseline.candidates


def test_reweighting_does_not_enumerate_and_updates_feasible_rankings():
    baseline = enumerate_search(Application(24, 2, 0, 1998))
    with patch("core.generator.product", side_effect=AssertionError("Unexpected regeneration")):
        updated = reassess_trace(baseline, normalization={"income": 10, "experience": .5, "certification": 1},
                                 constraints=Constraints(max_experience_increase=1))
    assert select_recommendation(updated.candidates).application == Application(25, 2, 1, 1998)
    assert {item.application for item in updated.evaluated} == {item.application for item in baseline.evaluated}


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf")])
def test_invalid_factors(scale):
    with pytest.raises(ValueError):
        reassess_trace(enumerate_search(Application()), normalization={"income": 10, "experience": scale, "certification": 1})


def test_small_positive_scales_decimals_and_ties():
    baseline = enumerate_search(Application(24.125, 2.875, 0))
    changed = reassess_trace(baseline, normalization={"income": 1e-9, "experience": 1e-10, "certification": 1e-8})
    assert all(item.distance > 0 and predict(item.application) for item in changed.candidates)
    default = enumerate_search(Application())
    tied = reassess_trace(default, normalization={"income": 10, "experience": 1, "certification": 1})
    assert tied.candidates[0].distance == tied.candidates[1].distance
    assert select_recommendation(tuple(reversed(tied.candidates)), enforce_feasibility=False) == tied.candidates[0]
    assert "Tie-break" in ranking_insight(default, tied, {"income": 10, "experience": 1, "certification": 1})


def test_unrepresentable_distance_is_reported_instead_of_recommending_infinity():
    with pytest.raises(ValueError, match="floating-point range"):
        reassess_trace(enumerate_search(Application()), normalization={"income": 1e-320, "experience": 5, "certification": 1})


def test_threshold_costs_respond_to_inputs_metric_and_permissions():
    costs = threshold_costs(Application())
    assert [item.cost for item in costs] == pytest.approx([.1, .2, 1])
    assert [item.reachable for item in costs] == [True, False, True]
    blocked = threshold_costs(Application(), constraints=Constraints(can_obtain_certification=False))
    assert [item.reachable for item in blocked] == [True, False, False]
    certified = threshold_costs(Application(24.5, 2.9, 1), {"income": 10, "experience": .5, "certification": 1})
    assert [item.cost for item in certified] == pytest.approx([.05, .2, 0])
    assert all(item.reachable for item in certified)


def test_already_accepted_has_no_generated_recourses():
    baseline = enumerate_search(Application(25, 3, 0))
    assert reassess_trace(baseline).candidates == ()
    assert "Already Accepted" in ranking_insight(baseline, baseline, {"income": 10, "experience": 5, "certification": 1})
