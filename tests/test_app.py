from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.model import Application

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app():
    test_app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not test_app.exception
    return test_app


def html_text(app):
    return " ".join(element.proto.body for element in app.get("html"))


def cards(app):
    return [element.proto.body for element in app.get("html")
            if element.proto.body.startswith('<section class="cfx-card')]


def test_default_generation_and_constraint_toggle(app):
    # Results first: both mathematical problems are visible before any click.
    assert "REJECTED" in html_text(app)
    assert "0 / 3 conditions" in html_text(app)
    assert "(25, 3, 0)" in cards(app)[0] and "0.30" in cards(app)[0]
    assert "(25, 2, 1)" in cards(app)[1] and "1.10" in cards(app)[1]
    assert app.session_state["recommendation"].application == Application(25, 2, 1)
    app.button(key="generate").click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 4
    assert list(app.dataframe[0].value["Distance"]) == pytest.approx([.3, 1.1, 1.2, 1.3])
    app.toggle(key="constraints_enabled").set_value(False).run()
    assert not app.exception
    assert app.session_state["recommendation"].application == Application(25, 3, 0)
    # The feasible card must not inherit the OFF toggle.
    assert "(25, 2, 1)" in cards(app)[1]
    assert list(app.dataframe[0].value["Feasible"]) == [False, True, False, False]


def test_no_feasible_result_then_recover_by_disabling_limits(app):
    app.checkbox(key="can_certify").uncheck().run()
    assert not app.exception
    assert "No feasible counterfactual" in cards(app)[1]
    assert app.session_state["recommendation"] is None
    app.toggle(key="constraints_enabled").set_value(False).run()
    assert app.session_state["recommendation"].application == Application(25, 3, 0)
    assert "No feasible counterfactual" in cards(app)[1]


def test_live_input_changes_and_already_accepted_state(app):
    app.number_input(key="income").set_value(25.0).run()
    assert app.session_state["recommendation"].application == Application(25, 2, 1)
    assert app.dataframe[0].value.iloc[0]["Distance"] == pytest.approx(.2)
    app.selectbox(key="certification").set_value(1).run()
    assert not app.exception
    assert "ACCEPTED" in html_text(app)
    assert "Not needed" in cards(app)[0]
    assert any("No recourse is necessary" in element.value for element in app.caption)
    assert len(app.dataframe) == 0
    assert app.session_state["search_trace"].evaluated == ()
    assert app.button(key="next_step").disabled
    app.selectbox(key="certification").set_value(0).run()
    assert len(app.dataframe) == 1


def test_settings_recompute_ranking_objective_and_feasibility(app):
    app.number_input(key="max_experience").set_value(1.0).run()
    assert app.session_state["recommendation"].application == Application(25, 3, 0)
    app.number_input(key="scale_experience").set_value(.1).run()
    assert app.session_state["recommendation"].application == Application(25, 2, 1)
    assert "(25, 2, 1)" in cards(app)[0]
    app.number_input(key="lambda_value").set_value(0.0).run()
    assert not app.exception
    assert all(item.objective == item.distance for item in app.session_state["search_trace"].candidates)


def test_zero_normalization_is_reported_without_crashing(app):
    app.number_input(key="scale_income").set_value(0.0).run()
    assert not app.exception
    assert any("strictly positive" in element.value for element in app.error)
    assert len(app.dataframe) == 0
    assert not cards(app)


def test_context_is_not_predictive_and_stays_immutable(app):
    app.checkbox(key="include_birth_year").check().run()
    app.number_input(key="birth_year").set_value(1998).run()
    assert not app.exception
    assert app.session_state["recommendation"].application == Application(25, 2, 1, 1998)
    assert all(item.application.birth_year == 1998 for item in app.session_state["search_trace"].evaluated)
    assert any("1998 → 1998" in element.value for element in app.caption)


def test_search_navigation_shows_complete_evaluation_and_resets(app):
    app.button(key="next_step").click().run()
    assert app.session_state["search_step"] == "Thresholds"
    assert app.dataframe[0].value.iloc[0]["Values enumerated"] == "24, 25"
    app.button(key="next_step").click().run()
    assert app.session_state["search_step"] == "Candidates"
    assert html_text(app).count('class="cfx-node"') == 8
    app.button(key="next_step").click().run()
    frame = app.dataframe[0].value
    assert len(frame) == 8
    assert frame["Valid"].sum() == 4
    assert frame["Retained"].sum() == 4
    assert frame.iloc[0]["Point"] == "Original"
    app.button(key="previous_step").click().run()
    assert app.session_state["search_step"] == "Candidates"
    app.button(key="reset_search").click().run()
    assert app.session_state["search_step"] == "Original"
    assert app.button(key="previous_step").disabled


@pytest.mark.parametrize("edit", ["input", "constraints", "metric", "toggle", "lambda", "generate"])
def test_search_state_is_invalidated_by_problem_or_policy_changes(app, edit):
    app.radio(key="search_step").set_value("Result").run()
    app.selectbox(key="selected_candidate").set_value("CF4").run()
    old_trace = app.session_state["search_trace"]
    if edit == "input":
        app.number_input(key="income").set_value(23.75).run()
    elif edit == "constraints":
        app.number_input(key="max_experience").set_value(1.0).run()
    elif edit == "metric":
        app.number_input(key="scale_experience").set_value(.1).run()
    elif edit == "toggle":
        app.toggle(key="constraints_enabled").set_value(False).run()
    elif edit == "lambda":
        app.number_input(key="lambda_value").set_value(0.0).run()
    else:
        app.button(key="generate").click().run()
    assert not app.exception
    assert app.session_state["search_step"] == "Original"
    assert app.session_state["selected_candidate"] == app.session_state["recommendation"].candidate_id
    if edit == "input":
        assert app.session_state["search_trace"].original.income == 23.75
        assert app.session_state["search_trace"] != old_trace


def test_highlight_selection_changes_slice_but_not_recommendation_or_inputs(app):
    app.radio(key="search_step").set_value("Evaluation").run()
    app.selectbox(key="selected_candidate").set_value("CF1").run()
    assert app.radio(key="view_certification").value == 0
    assert app.session_state["search_step"] == "Evaluation"
    assert app.number_input(key="income").value == 24.0
    assert app.session_state["recommendation"].candidate_id == "CF2"
    app.radio(key="view_certification").set_value(1).run()
    assert any("CF1 belongs to certification 0" in element.value for element in app.caption)


def test_feasible_filter_and_filter_empty_state(app):
    app.checkbox(key="feasible_only").check().run()
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["Candidate"] == "CF2"
    app.checkbox(key="can_certify").uncheck().run()
    assert not app.exception
    assert any("No feasible candidates match" in element.value for element in app.info)
    assert len(app.dataframe) == 0


def test_feasibility_step_respects_policy_without_altering_assessments(app):
    app.radio(key="search_step").set_value("Feasibility").run()
    assert list(app.dataframe[0].value["Eligible"]) == [False, True, False, False]
    app.toggle(key="constraints_enabled").set_value(False).run()
    app.radio(key="search_step").set_value("Feasibility").run()
    assert list(app.dataframe[0].value["Eligible"]) == [True] * 4
    assert list(app.dataframe[0].value["Feasible"]) == [False, True, False, False]


def test_technical_explanations_are_collapsed(app):
    for label in ("Mathematical Details", "Search Algorithm", "Assumptions & Limitations", "Additional Settings"):
        assert not next(expander for expander in app.expander if expander.label == label).proto.expanded
