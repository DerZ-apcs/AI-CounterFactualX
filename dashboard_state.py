"""Streamlit presentation state and callbacks; computations remain in core/."""

import streamlit as st

from core.constraints import Constraints
from core.distance import NORMALIZATION
from core.scenarios import scenario_definitions


def initialize_state() -> None:
    """Keep view widgets alive when Basic/Advanced temporarily hides them."""
    defaults = {
        "income": 24.0, "experience": 2.0, "certification": 0,
        "birth_year": 2000, "include_birth_year": False,
        "mode": "Basic", "practical_profile": "3 Months", "custom_constraints": Constraints(),
        "normalization": dict(NORMALIZATION), "constraints_enabled": True,
        "max_income": 5.0, "max_experience": .25, "can_certify": True,
        "lambda_value": 10.0, "scenario_selector": "3 Months",
    }
    defaults.update({f"scale_{name}": value for name, value in NORMALIZATION.items()})
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Documented Streamlit keep-alive technique: self-assignment detaches a key
    # from widget cleanup. These controls can disappear on a mode/tab change.
    for key in ("selected_candidate", "view_certification", "search_step", "feasible_only",
                "scenario_selector", "max_income", "max_experience", "can_certify",
                "scale_income", "scale_experience", "scale_certification"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def save_normalization() -> None:
    st.session_state["normalization"] = {
        name: st.session_state[f"scale_{name}"] for name in NORMALIZATION
    }


def normalization_controls(*, inline: bool = True) -> dict[str, float]:
    """One widget per scale, in the popover in Basic and inline in Advanced."""
    columns = st.columns(3) if inline else [st.container() for _ in NORMALIZATION]
    for column, name in zip(columns, NORMALIZATION):
        column.number_input(
            f"{name.title()} normalization", min_value=0.0, step=.1, format="%g",
            key=f"scale_{name}", on_change=save_normalization,
            help="Smaller normalization scales increase the penalty for changing that feature. Must be positive.",
        )
    return dict(st.session_state["normalization"])


def edit_custom_constraints() -> None:
    """Editing the V2 settings explicitly selects the Custom practical profile."""
    st.session_state["custom_constraints"] = Constraints(
        st.session_state["max_income"], st.session_state["max_experience"], st.session_state["can_certify"],
    )
    st.session_state["practical_profile"] = "Custom"
    sync_scenario_selector()


def sync_scenario_selector() -> None:
    st.session_state["scenario_selector"] = (
        st.session_state["practical_profile"] if st.session_state["constraints_enabled"] else "No Constraints"
    )


def apply_scenario() -> None:
    """Preserve input/scales and the saved Custom configuration across presets."""
    name = st.session_state["scenario_selector"]
    st.session_state["constraints_enabled"] = name != "No Constraints"
    if name == "No Constraints":
        return  # Keep the right card's explicitly labeled practical comparison.
    st.session_state["practical_profile"] = name
    scenario = next(item for item in scenario_definitions(st.session_state["custom_constraints"]) if item.name == name)
    limits = scenario.constraints
    st.session_state["max_income"] = float(limits.max_income_increase)
    st.session_state["max_experience"] = float(limits.max_experience_increase)
    st.session_state["can_certify"] = limits.can_obtain_certification


def active_constraints() -> Constraints:
    return next(item.constraints for item in scenario_definitions(st.session_state["custom_constraints"])
                if item.name == st.session_state["practical_profile"])


def reset_defaults() -> None:
    """Restore the entire original worked example before widgets are rendered."""
    st.session_state.update({
        "income": 24.0, "experience": 2.0, "certification": 0,
        "mode": "Basic", "constraints_enabled": True,
        "practical_profile": "3 Months", "scenario_selector": "3 Months",
        "custom_constraints": Constraints(), "max_income": 5.0, "max_experience": .25, "can_certify": True,
        "normalization": dict(NORMALIZATION), "lambda_value": 10.0,
        "include_birth_year": False, "birth_year": 2000,
        "selected_candidate": "CF2", "view_certification": 1, "search_step": "Original", "feasible_only": False,
        **{f"scale_{name}": value for name, value in NORMALIZATION.items()},
    })
    for key in ("geometry_signature", "problem_signature", "view_signature"):
        st.session_state.pop(key, None)
