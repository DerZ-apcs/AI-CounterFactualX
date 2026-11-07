from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app():
    test_app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not test_app.exception
    return test_app


def success_text(app):
    return " ".join(element.value for element in app.success)


def test_default_generation_and_constraint_toggle(app):
    assert app.metric[0].value == "REJECTED"
    assert "0 / 3" in app.metric[0].delta
    app.button(key="generate").click().run()
    assert not app.exception
    assert "Recommended: (25, 2, 1)" in success_text(app)
    assert len(app.dataframe[0].value) == 4
    assert list(app.dataframe[0].value["Distance"]) == pytest.approx([.3, 1.1, 1.2, 1.3])
    assert len(app.get("plotly_chart")) == 2
    app.toggle(key="constraints_enabled").set_value(False).run()
    assert not app.exception
    assert "Recommended: (25, 3, 0)" in success_text(app)
    assert list(app.dataframe[0].value["Feasibility"]) == ["Infeasible", "Feasible", "Infeasible", "Infeasible"]


def test_no_feasible_result_then_recover_by_disabling_limits(app):
    app.button(key="generate").click().run()
    app.checkbox(key="can_certify").uncheck().run()
    assert not app.exception
    assert any("No feasible counterfactual exists" in element.value for element in app.error)
    assert "Recommended:" not in success_text(app)
    app.toggle(key="constraints_enabled").set_value(False).run()
    assert "Recommended: (25, 3, 0)" in success_text(app)


def test_live_input_changes_and_already_accepted_state(app):
    app.button(key="generate").click().run()
    app.number_input(key="income").set_value(25.0).run()
    assert "Recommended: (25, 2, 1)" in success_text(app)
    assert app.dataframe[0].value.iloc[0]["Distance"] == pytest.approx(.2)
    app.selectbox(key="certification").set_value(1).run()
    assert not app.exception
    assert app.metric[0].value == "ACCEPTED"
    assert "No recourse is necessary" in success_text(app)
    assert len(app.dataframe) == 0
    app.selectbox(key="certification").set_value(0).run()
    assert len(app.dataframe) == 1


def test_settings_recompute_ranking_objective_and_feasibility(app):
    app.button(key="generate").click().run()
    app.number_input(key="max_experience").set_value(1.0).run()
    assert "Recommended: (25, 3, 0)" in success_text(app)
    app.number_input(key="scale_experience").set_value(.1).run()
    assert "Recommended: (25, 2, 1)" in success_text(app)
    app.number_input(key="lambda_value").set_value(0.0).run()
    assert not app.exception
    frame = app.dataframe[0].value
    assert list(frame["Objective"]) == list(frame["Distance"])


def test_zero_normalization_is_reported_without_crashing(app):
    app.number_input(key="scale_income").set_value(0.0).run()
    assert not app.exception
    assert any("strictly positive" in element.value for element in app.error)
    assert len(app.dataframe) == 0


def test_context_is_not_predictive_and_stays_immutable(app):
    app.checkbox(key="include_birth_year").check().run()
    app.number_input(key="birth_year").set_value(1998).run()
    app.button(key="generate").click().run()
    assert not app.exception
    assert "Recommended: (25, 2, 1)" in success_text(app)
    assert any("1998 → 1998" in element.value for element in app.caption)
