"""V3 analytics and mode lifecycle checks, in addition to the unchanged V2 suite."""

from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from core.constraints import Constraints
from core.distance import NORMALIZATION
from core.model import Application

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app():
    instance = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not instance.exception
    return instance


def test_basic_default_and_mode_specific_tabs(app):
    assert app.radio(key="mode").value == "Basic"
    assert [tab.label for tab in app.tabs] == ["Decision Boundary", "Search Process", "Candidates"]
    app.radio(key="mode").set_value("Advanced").run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Sensitivity Analysis", "Scenario Comparison"]
    assert app.session_state["recommendation"].application == Application(25, 2, 1)


def test_advanced_sensitivity_and_metric_insight_are_live(app):
    app.radio(key="mode").set_value("Advanced").run()
    app.number_input(key="scale_experience").set_value(.5).run()
    assert not app.exception
    assert any("CF1 → CF2" in caption.value for caption in app.caption)
    trace = app.session_state["search_trace"]
    assert {item.candidate_id: item.distance for item in trace.candidates} == pytest.approx(
        {"CF1": 2.1, "CF2": 1.1, "CF3": 3, "CF4": 3.1})
    assert app.session_state["recommendation"].application == Application(25, 2, 1)
    assert list(app.dataframe[0].value["CF"]) == ["CF2", "CF1", "CF3", "CF4"]
    assert app.session_state["normalization"] == {"income": 10, "experience": .5, "certification": 1}


def test_presets_scope_empty_state_without_overwriting_input_or_metric(app):
    app.number_input(key="income").set_value(24.25).run()
    app.radio(key="mode").set_value("Advanced").run()
    app.number_input(key="scale_experience").set_value(.5).run()
    for name in ("No Constraints", "3 Months", "No Certificate", "Custom"):
        app.radio(key="scenario_selector").set_value(name).run()
        assert not app.exception
        assert app.number_input(key="income").value == 24.25
        assert app.number_input(key="scale_experience").value == .5
        assert all(result.trace.original == Application(24.25, 2, 0)
                   for result in app.session_state["scenario_results"].values())
        if name == "No Certificate":
            assert app.session_state["recommendation"] is None
            assert any("No feasible CF in No Certificate" in warning.value for warning in app.warning)
        else:
            assert app.session_state["recommendation"] is not None


def test_custom_limits_survive_preset_switches(app):
    app.number_input(key="max_income").set_value(1.0).run()
    app.number_input(key="max_experience").set_value(1.0).run()
    app.checkbox(key="can_certify").uncheck().run()
    saved = app.session_state["custom_constraints"]
    assert saved == Constraints(1, 1, False)
    app.radio(key="mode").set_value("Advanced").run()
    assert app.radio(key="scenario_selector").value == "Custom"
    app.radio(key="scenario_selector").set_value("3 Months").run()
    assert app.checkbox(key="can_certify").value
    assert app.session_state["custom_constraints"] == saved
    app.radio(key="scenario_selector").set_value("Custom").run()
    assert not app.exception
    assert app.number_input(key="max_experience").value == 1
    assert not app.checkbox(key="can_certify").value
    assert app.session_state["recommendation"].application == Application(25, 3, 0)


def test_mode_switch_preserves_inspection_state_over_multiple_reruns(app):
    app.number_input(key="income").set_value(24.125).run()
    app.radio(key="search_step").set_value("Evaluation").run()
    app.selectbox(key="selected_candidate").set_value("CF3").run()
    app.radio(key="mode").set_value("Advanced").run()
    app.run()  # exercise cleanup of widgets absent for more than one run
    app.radio(key="mode").set_value("Basic").run()
    assert not app.exception
    assert app.number_input(key="income").value == 24.125
    assert app.radio(key="search_step").value == "Evaluation"
    assert app.selectbox(key="selected_candidate").value == "CF3"
    assert app.radio(key="view_certification").value == 1


def test_only_original_edits_regenerate_candidate_geometry(app):
    with patch("core.generator.product", side_effect=AssertionError("Candidates regenerated")):
        app.radio(key="mode").set_value("Advanced").run()
        assert not app.exception
        app.number_input(key="scale_experience").set_value(.5).run()
        assert not app.exception
        app.radio(key="scenario_selector").set_value("No Certificate").run()
        assert not app.exception
        app.radio(key="scenario_selector").set_value("No Constraints").run()
        assert not app.exception
        app.radio(key="mode").set_value("Basic").run()
        assert not app.exception
    app.number_input(key="income").set_value(25.0).run()
    assert app.session_state["baseline_trace"].original == Application(25, 2, 0)
    assert len(app.session_state["baseline_trace"].evaluated) == 4


def test_reset_defaults_restores_entire_worked_example(app):
    app.number_input(key="income").set_value(30.25).run()
    app.radio(key="mode").set_value("Advanced").run()
    app.number_input(key="scale_experience").set_value(.5).run()
    app.radio(key="scenario_selector").set_value("No Certificate").run()
    app.number_input(key="lambda_value").set_value(0.0).run()
    app.button(key="reset_defaults").click().run()
    assert not app.exception
    assert app.radio(key="mode").value == "Basic"
    assert app.number_input(key="income").value == 24
    assert app.number_input(key="experience").value == 2
    assert app.session_state["normalization"] == dict(NORMALIZATION)
    assert app.session_state["scenario_selector"] == "3 Months"
    assert app.session_state["custom_constraints"] == Constraints()
    assert app.session_state["recommendation"].application == Application(25, 2, 1)
    assert app.session_state["search_trace"].candidates[0].distance == pytest.approx(.3)


def test_comparison_updates_with_original_and_handles_accepted(app):
    app.radio(key="mode").set_value("Advanced").run()
    app.number_input(key="experience").set_value(2.9).run()
    assert app.session_state["scenario_results"]["No Certificate"].recommendation is not None
    app.selectbox(key="certification").set_value(1).run()
    app.number_input(key="income").set_value(25.0).run()
    assert not app.exception
    assert all(result.status == "Already Accepted" and result.recommendation is None
               for result in app.session_state["scenario_results"].values())
    assert any("Original already Accepted" in message.value for message in app.info)


def test_scenario_selector_and_basic_toggle_stay_synchronized(app):
    app.toggle(key="constraints_enabled").set_value(False).run()
    app.radio(key="mode").set_value("Advanced").run()
    assert app.radio(key="scenario_selector").value == "No Constraints"
    app.radio(key="scenario_selector").set_value("No Certificate").run()
    app.radio(key="mode").set_value("Basic").run()
    assert app.toggle(key="constraints_enabled").value
    assert app.session_state["recommendation"] is None
    app.toggle(key="constraints_enabled").set_value(False).run()
    assert app.session_state["recommendation"].application == Application(25, 3, 0)
    assert app.session_state["practical_profile"] == "No Certificate"


def test_scales_persist_when_controls_move_between_modes(app):
    app.number_input(key="scale_income").set_value(.75).run()
    app.radio(key="mode").set_value("Advanced").run()
    assert app.number_input(key="scale_income").value == .75
    app.number_input(key="scale_experience").set_value(.5).run()
    app.radio(key="mode").set_value("Basic").run()
    assert app.number_input(key="scale_experience").value == .5
    assert app.number_input(key="scale_income").value == .75


def test_advanced_invalid_scale_shows_error_without_stale_cards(app):
    app.radio(key="mode").set_value("Advanced").run()
    app.number_input(key="scale_experience").set_value(0.0).run()
    assert not app.exception
    assert any("strictly positive" in message.value for message in app.error)
    assert not any(element.proto.body.startswith('<section class="cfx-card') for element in app.get("html"))


def test_scenario_summary_shows_dash_for_missing_distances(app):
    app.radio(key="mode").set_value("Advanced").run()
    frame = next(table.value for table in app.dataframe if "Scenario" in table.value.columns)
    assert frame.loc[frame["Scenario"] == "No Certificate", "Distance"].item() == "—"
    assert frame.loc[frame["Scenario"] == "3 Months", "Distance"].item() == "1.1000"
    assert app.session_state["scenario_results"]["No Certificate"].distance is None
