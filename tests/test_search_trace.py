"""The teaching trace must be the real search, including unsuccessful points."""

import pytest

from core.constraints import Constraints
from core.generator import enumerate_search, generate_counterfactuals, select_recommendation
from core.model import Application


def test_complete_default_trace_includes_original_and_rejected_combinations():
    original = Application()
    trace = enumerate_search(original)
    assert trace.options == {"income": (24, 25), "experience": (2, 3), "certification": (0, 1)}
    assert [item.application for item in trace.evaluated] == [
        Application(24, 2, 0), Application(24, 2, 1),
        Application(24, 3, 0), Application(24, 3, 1),
        Application(25, 2, 0), Application(25, 2, 1),
        Application(25, 3, 0), Application(25, 3, 1),
    ]
    assert [item.valid for item in trace.evaluated] == [False, False, False, True, False, True, True, True]
    assert trace.evaluated[0].candidate_id == "Original"
    assert trace.evaluated[0].distance == 0
    assert trace.evaluated[0].objective == 10
    assert len({item.application for item in trace.evaluated}) == 8
    assert list(trace.candidates) == generate_counterfactuals(original)
    for item in trace.candidates:
        assert item == next(point for point in trace.evaluated if point.application == item.application)


def test_trace_is_dynamic_and_preserves_satisfied_conditions_and_context():
    original = Application(25.12345, 2.98765, 0, 1998)
    trace = enumerate_search(original)
    assert trace.options["income"] == (25.12345,)
    assert len(trace.evaluated) == 4
    assert len(trace.candidates) == 3
    assert all(item.application.birth_year == 1998 for item in trace.evaluated)
    assert trace.candidates[0].distance == pytest.approx(.01235 / 5)


def test_trace_uses_current_limits_metric_and_penalty_without_relaxing_validity():
    original = Application()
    limits = Constraints(can_obtain_certification=False)
    trace = enumerate_search(original, constraints=limits, lambda_value=0,
                             normalization={"income": 10, "experience": .1, "certification": 1})
    assert trace.evaluated[0].objective == 0
    assert trace.candidates[0].application == Application(25, 2, 1)
    assert trace.candidates[0].distance == pytest.approx(1.1)
    assert select_recommendation(trace.candidates) is None
    assert select_recommendation(trace.candidates, enforce_feasibility=False).valid
    assert next(item for item in trace.evaluated if item.application == Application(25, 2, 1)).candidate_id == "CF1"


def test_already_accepted_trace_does_not_invent_a_search():
    trace = enumerate_search(Application(25, 3, 0))
    assert trace.evaluated == trace.candidates == ()
    assert select_recommendation(trace.candidates) is None
