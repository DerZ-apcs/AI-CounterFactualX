"""Counterfactual Explorer V3: compact dashboard and analytical experiments."""

from html import escape

import pandas as pd
import streamlit as st

from core.constraints import Constraints
from core.generator import Candidate, SearchTrace, enumerate_search, select_recommendation
from core.model import Application, FEATURES, condition_results, predict
from core.scenarios import SCENARIO_NAMES, evaluate_scenarios
from analytics_views import scenario_view, sensitivity_view
from dashboard_details import render_details
from dashboard_state import (
    active_constraints, apply_scenario, edit_custom_constraints, initialize_state,
    normalization_controls, reset_defaults, sync_scenario_selector,
)
from visualization import candidate_distance_figure, decision_region_figure
from ui_theme import CSS

STEPS = ("Original", "Thresholds", "Candidates", "Evaluation", "Feasibility", "Result")


def point_label(application: Application) -> str:
    """Compact (income, experience, certification) label; no search rounding."""
    return f"({application.income:g}, {application.experience:g}, {application.certification:g})"


def short_changes(original: Application, candidate: Candidate) -> str:
    """Show signed changes without duplicating full feature descriptions."""
    return ", ".join(
        f"{label}{getattr(candidate.application, name) - getattr(original, name):+g}"
        for name, label in zip(FEATURES, ("I", "E", "C"))
        if getattr(candidate.application, name) != getattr(original, name)
    ) or "Unchanged"


def settings() -> tuple[Constraints, dict[str, float], float, int | None]:
    """All detailed configuration stays inside the header popover."""
    with st.popover("Settings ⚙", width="stretch"):
        st.markdown(f"**Practical limits · {st.session_state['practical_profile']}**")
        st.number_input("Max income increase (M VND/month)", min_value=0.0,
                         step=.5, key="max_income", on_change=edit_custom_constraints)
        st.number_input("Max experience increase (years)", min_value=0.0,
                         step=.05, key="max_experience", on_change=edit_custom_constraints,
                         help="Income and experience cannot decrease. Editing a limit selects Custom.")
        st.checkbox("Certification can be obtained", key="can_certify", on_change=edit_custom_constraints)
        with st.expander("Additional Settings", expanded=False):
            if st.session_state["mode"] == "Basic":
                st.caption("Manual scales · Full analysis in Advanced mode.")
                normalization_controls(inline=False)
            lambda_value = st.number_input("Lambda (diagnostic only)", min_value=0.0,
                                           step=1.0, key="lambda_value",
                                           help="Never replaces the requirement that a recommendation is Accepted.")
            birth_year = None
            if st.checkbox("Include birth year", key="include_birth_year"):
                birth_year = st.number_input("Birth year (immutable context)", min_value=1,
                                              step=1, key="birth_year",
                                              help="Not predictive; preserved in every counterfactual.")
        st.button("Reset to Defaults", key="reset_defaults", on_click=reset_defaults, width="stretch",
                   help="Restore original (24, 2, 0), default scales, three-month limits, and Basic mode.")
    return active_constraints(), dict(st.session_state["normalization"]), lambda_value, birth_year


def recommendation_card(
    title: str, original: Application, candidate: Candidate | None, *, active: bool, accepted: bool, scope: str = "",
) -> None:
    """A small semantic card with CSS scoped only to our own elements."""
    if accepted:
        value, distance, changes = "Not needed", "—", "Original already Accepted"
    elif candidate is None:
        value, distance, changes = "No feasible counterfactual", "—", "Review limits in Settings"
    else:
        value = point_label(candidate.application)
        distance = f"{candidate.distance:.2f}"
        changes = f"{candidate.candidate_id} · {short_changes(original, candidate)}"
    tag = '<span class="tag">Recommended</span>' if active and candidate else ""
    st.html(
        f'<section class="cfx-card{" active" if active else ""}" aria-label="{escape(title)}">'
        f'<header>{escape(title)} <small>{escape(scope)}</small>{tag}</header>'
        f'<div class="values"><span title="(Income, Experience, Certification)">{escape(value)}</span>'
        f'<span class="distance"><small>Distance </small>{distance}</span></div>'
        f'<div class="changes">{escape(changes)} <small>· (I, E, C)</small></div></section>'
    )


def exclusion_summary(original: Application, candidate: Candidate, constraints: Constraints) -> str:
    """Summarize an actual violation; full diagnostics remain in candidate details."""
    violation = candidate.feasibility.violations[0]
    if violation.startswith("Experience increase"):
        reason = (f"experience {candidate.application.experience - original.experience:+g} > "
                  f"+{constraints.max_experience_increase:g} years")
    elif violation.startswith("Income increase"):
        reason = (f"income {candidate.application.income - original.income:+g} > "
                  f"+{constraints.max_income_increase:g} M VND")
    elif violation.startswith("Obtaining certification"):
        reason = "certification unavailable"
    else:
        reason = violation
    return f"{candidate.candidate_id} excluded: {reason}."


def synchronize(
    original: Application, constraints: Constraints, normalization: dict[str, float],
    lambda_value: float, enabled: bool, recalculate: bool,
) -> SearchTrace:
    """Generate only on an input edit; metric/scenario edits reuse cached points."""
    if original != st.session_state.get("geometry_signature") or recalculate:
        st.session_state["baseline_trace"] = enumerate_search(original)
        st.session_state["geometry_signature"] = original
    problem = (original, constraints, tuple(normalization.items()), lambda_value,
               st.session_state["custom_constraints"])
    if problem != st.session_state.get("problem_signature") or recalculate:
        st.session_state["scenario_results"] = evaluate_scenarios(
            st.session_state["baseline_trace"], normalization=normalization,
            lambda_value=lambda_value, custom=st.session_state["custom_constraints"],
        )
        st.session_state["problem_signature"] = problem
    profile = st.session_state["practical_profile"]
    results = st.session_state["scenario_results"]
    trace = results[profile].trace
    st.session_state["search_trace"] = trace
    closest = select_recommendation(trace.candidates, enforce_feasibility=False)
    feasible = results[profile].recommendation
    recommended = feasible if enabled else closest
    view_signature = (problem, enabled, profile)
    if view_signature != st.session_state.get("view_signature") or recalculate:
        st.session_state["search_step"] = STEPS[0]
        selected = recommended or closest
        st.session_state["selected_candidate"] = selected.candidate_id if selected else "None"
        st.session_state["view_certification"] = selected.application.certification if selected else original.certification
        st.session_state["view_signature"] = view_signature
        st.session_state["revision"] = st.session_state.get("revision", 0) + 1
    st.session_state["recommendation"] = recommended
    return trace


def select_candidate(identifier: str) -> None:
    """Share selection across the table and chart; navigate to the matching slice."""
    item = next((item for item in st.session_state["search_trace"].candidates
                 if item.candidate_id == identifier), None)
    if item is not None:
        st.session_state["selected_candidate"] = identifier
        st.session_state["view_certification"] = item.application.certification


def on_candidate_change() -> None:
    select_candidate(st.session_state["selected_candidate"])


def move_step(offset: int | None = None) -> None:
    """Callbacks run before rendering, so the stepper cannot lag one rerun."""
    index = STEPS.index(st.session_state["search_step"])
    st.session_state["search_step"] = STEPS[0 if offset is None else max(0, min(len(STEPS) - 1, index + offset))]


def candidate_table(original: Application, candidates: tuple[Candidate, ...]) -> pd.DataFrame:
    """Numeric distances remain sortable; validity and feasibility stay distinct."""
    return pd.DataFrame([
        {"Candidate": item.candidate_id, "Changes": short_changes(original, item),
         "Distance": item.distance, "Valid": item.valid, "Feasible": item.feasibility.feasible}
        for item in candidates
    ], columns=["Candidate", "Changes", "Distance", "Valid", "Feasible"])


def search_process(trace: SearchTrace, enabled: bool) -> None:
    """Reveal actual evaluated points, including unsuccessful combinations."""
    accepted = bool(predict(trace.original))
    stage = st.radio("Search stage", STEPS, key="search_step", horizontal=True,
                     label_visibility="collapsed", disabled=accepted)
    index = STEPS.index(stage)
    previous, following, reset, _ = st.columns([1, 1, 1, 3])
    previous.button("Previous Step", key="previous_step", on_click=move_step, args=(-1,),
                    disabled=accepted or index == 0, width="stretch")
    following.button("Next Step", key="next_step", on_click=move_step, args=(1,),
                     disabled=accepted or index == len(STEPS) - 1, width="stretch")
    reset.button("Reset", key="reset_search", on_click=move_step, disabled=accepted, width="stretch")
    if accepted:
        st.info("Already Accepted · Search skipped · No recourse needed.")
        return
    if stage == "Original":
        st.markdown(f"**Original {point_label(trace.original)} → Rejected**")
        st.caption("Target: Accepted · Threshold-aware enumeration.")
    elif stage == "Thresholds":
        st.dataframe(pd.DataFrame([
            {"Feature": name.title(), "Original": getattr(trace.original, name),
             "Values enumerated": ", ".join(f"{value:g}" for value in values),
             "Condition passes": condition_results(trace.original)[name]}
            for name, values in trace.options.items()
        ]), hide_index=True, width="stretch")
        st.caption("Keep original values; add missing exact thresholds. No grid.")
    elif stage == "Candidates":
        nodes = "".join(
            f'<div class="cfx-node"><b>{item.candidate_id}</b>{point_label(item.application)}'
            f'<br><small>{"Unchanged baseline" if item.application == trace.original else "Threshold combination"}</small></div>'
            for item in trace.evaluated
        )
        st.html(f'<div class="cfx-nodes">{nodes}</div>')
        st.caption(f"{len(trace.evaluated)} product combinations · Includes unchanged original.")
    elif stage == "Evaluation":
        st.dataframe(pd.DataFrame([
            {"Point": item.candidate_id, "(I, E, C)": point_label(item.application),
             "Distance": item.distance, "Valid": item.valid, "L": item.objective,
             "Retained": item.valid and item.application != trace.original}
            for item in trace.evaluated
        ]), hide_index=True, width="stretch", column_config={
            "Distance": st.column_config.NumberColumn(format="%.4f"),
            "L": st.column_config.NumberColumn(format="%.4f"),
        })
        st.caption(f"{len(trace.evaluated)} evaluated → {len(trace.candidates)} accepted changes. Original/rejected points excluded.")
    elif stage == "Feasibility":
        frame = candidate_table(trace.original, trace.candidates)
        frame["Eligible"] = [item.feasibility.feasible if enabled else True for item in trace.candidates]
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Constraints ON: retain feasible points." if enabled else
                   "Constraints OFF: all target-valid changes remain eligible.")
    else:
        item = st.session_state["recommendation"]
        if item is None:
            st.warning("No feasible counterfactual under the configured limits.")
        else:
            st.success(f"Selected: {item.candidate_id} {point_label(item.application)} · Distance {item.distance:.2f}")
        st.caption(f"Accepted + {'feasibility' if enabled else 'mandatory limits'} first; then minimize distance.")


def candidates_panel(trace: SearchTrace, selected: Candidate | None) -> None:
    """Compact selectable comparison plus metric sensitivity, with details on demand."""
    if not trace.candidates:
        st.info("Original already Accepted. No generated explanations are needed.")
        return
    feasible_only = st.checkbox("Feasible only", key="feasible_only")
    visible = tuple(item for item in trace.candidates if not feasible_only or item.feasibility.feasible)
    table_key = f"candidate_table_{st.session_state['revision']}_{feasible_only}"

    def on_row_select() -> None:
        rows = st.session_state[table_key]["selection"]["rows"]
        if rows:
            select_candidate(visible[rows[0]].candidate_id)

    table_column, chart_column = st.columns([3, 2])
    with table_column:
        if visible:
            st.dataframe(candidate_table(trace.original, visible), key=table_key, hide_index=True,
                         width="stretch", on_select=on_row_select, selection_mode="single-row",
                         column_config={"Distance": st.column_config.NumberColumn(format="%.4f")})
            st.caption("Select a row to highlight its point. Click Distance to sort.")
        else:
            st.info("No feasible candidates match this filter.")
    with chart_column:
        st.plotly_chart(candidate_distance_figure(trace.candidates, selected), width="stretch",
                        key="distances", config={"displaylogo": False})
    st.caption("Full distance analysis: Advanced mode.")
    if selected:
        with st.expander(f"Candidate Details · {selected.candidate_id}", expanded=False):
            st.write(f"**{point_label(selected.application)}** · Valid: {selected.valid} · "
                     f"Feasible: {selected.feasibility.feasible} · Sparsity: {selected.sparsity} · L: {selected.objective:.6g}")
            st.write("; ".join(selected.changes))
            normalization = dict(st.session_state["problem_signature"][2])
            terms = [f"|{getattr(trace.original, name):g} − {getattr(selected.application, name):g}| / {normalization[name]:g}"
                     for name in FEATURES]
            st.code("d = " + " + ".join(terms) + f" = {selected.distance:.6g}", language="text")
            for violation in selected.feasibility.violations:
                st.caption(violation)


def main() -> None:
    st.set_page_config(page_title="Counterfactual Explorer", page_icon="🔍", layout="wide",
                       initial_sidebar_state="collapsed")
    initialize_state()
    st.html(CSS)
    with st.container(gap="xsmall", key="dashboard_shell"):
        with st.container(key="page_header"):
            heading, mode_column, configuration = st.columns([4, 2, 1], vertical_alignment="center")
            with heading:
                st.html('<h1 class="cfx-title">Counterfactual Explorer <small>Explainable AI · Counterfactual Analysis</small></h1>')
            with mode_column:
                mode = st.radio("Mode", ["Basic", "Advanced"], key="mode", horizontal=True,
                                 label_visibility="collapsed")
            with configuration:
                try:
                    constraints, normalization, lambda_value, birth_year = settings()
                except ValueError as error:
                    st.error(str(error))
                    st.stop()
        with st.container(key="application_inputs"):
            income_col, experience_col, cert_col, button_col, constraint_col = st.columns(
                [1.4, 1.4, 1, 1, 1.2], vertical_alignment="bottom",
            )
            income = income_col.number_input("Income (M VND)", min_value=0.0,
                                             step=.1, format="%g", key="income",
                                             help="Million VND/month. Condition: income ≥ 25.")
            experience = experience_col.number_input("Experience (years)", min_value=0.0,
                                                     step=.05, format="%g", key="experience",
                                                     help="Continuous years. Condition: experience ≥ 3.")
            certification = cert_col.selectbox("Certified", [0, 1], key="certification",
                                                format_func=lambda value: "Yes" if value else "No")
            recalculate = button_col.button("Generate", type="primary", key="generate", width="stretch",
                                            help="Recalculate and restart the search trace. Results also update automatically.")
            enabled = constraint_col.toggle("Constraints", key="constraints_enabled",
                                             on_change=sync_scenario_selector,
                                             help="Choose the active recommendation. Both comparison cards keep their own constraints.")
        # Allocate positions first, then render analytical controls before computing.
        # This preserves results-first layout without a one-rerun calculation lag.
        status_container = st.container()
        cards_container = st.container()
        summary_container = st.empty()
        if mode == "Basic":
            decision_tab, search_tab, candidates_tab = st.tabs(
                ["Decision Boundary", "Search Process", "Candidates"], key="dashboard_tabs",
            )
        else:
            sensitivity_tab, scenario_tab = st.tabs(
                ["Sensitivity Analysis", "Scenario Comparison"], key="advanced_tabs",
            )
            with sensitivity_tab:
                normalization = normalization_controls()
            with scenario_tab:
                st.radio("Scenario", SCENARIO_NAMES, horizontal=True, key="scenario_selector",
                          label_visibility="collapsed", on_change=apply_scenario)
        try:
            original = Application(income, experience, certification, birth_year)
            trace = synchronize(original, constraints, normalization, lambda_value, enabled, recalculate)
        except ValueError as error:
            st.error(str(error))
            st.stop()
        conditions = condition_results(original)
        accepted = bool(predict(original))
        badges = " &nbsp; ".join(
            f'<span title="{explanation}">{name} {"✓" if conditions[feature] else "✕"}</span>'
            for feature, name, explanation in (
                ("income", "Income", "Income ≥ 25 million VND/month"),
                ("experience", "Experience", "Experience ≥ 3 years"),
                ("certification", "Certification", "Certification = 1"),
            )
        )
        with status_container:
            st.html(f'<div class="cfx-status" role="status"><span>Current prediction: '
                    f'<b class="{"pass" if accepted else "fail"}">{"ACCEPTED" if accepted else "REJECTED"}</b></span>'
                    f'<span>{sum(conditions.values())} / 3 conditions</span><span>{badges}</span></div>')
        closest = select_recommendation(trace.candidates, enforce_feasibility=False)
        feasible = select_recommendation(trace.candidates, enforce_feasibility=True)
        with cards_container:
            left, right = st.columns(2)
            with left:
                recommendation_card("Closest CF", original, closest, active=not enabled, accepted=accepted)
            with right:
                recommendation_card("Closest Feasible CF", original, feasible, active=enabled, accepted=accepted,
                                    scope=st.session_state["practical_profile"])
        if accepted:
            summary_container.caption("Original already Accepted. No recourse is necessary for target = 1.")
        elif closest and not closest.feasibility.feasible:
            summary_container.caption(exclusion_summary(original, closest, constraints))
        else:
            summary_container.caption("Closest and closest feasible coincide under the current limits.")
        selected = next((item for item in trace.candidates
                         if item.candidate_id == st.session_state["selected_candidate"]), None)
        if mode == "Advanced":
            with sensitivity_tab:
                sensitivity_view(st.session_state["baseline_trace"], trace, normalization, constraints)
            with scenario_tab:
                scenario_view(st.session_state["scenario_results"], st.session_state["scenario_selector"], normalization)
        else:
            basic_views(decision_tab, search_tab, candidates_tab, original, trace, closest, feasible, selected, enabled)
        render_details(original, normalization, lambda_value, constraints,
                        trace=trace if mode == "Basic" else None, enforce_feasibility=enabled)


def basic_views(decision_tab, search_tab, candidates_tab, original, trace, closest, feasible, selected, enabled) -> None:
    """The original V2 views, shared unchanged by Basic mode."""
    with decision_tab:
        slice_column, select_column = st.columns([1, 2], vertical_alignment="bottom")
        with slice_column:
            slice_value = st.radio("Certification slice", [0, 1], horizontal=True,
                                   key="view_certification", help="C=0: income AND experience. C=1: income OR experience.")
        with select_column:
            st.selectbox("Highlight candidate", [item.candidate_id for item in trace.candidates] or ["None"],
                          key="selected_candidate", on_change=on_candidate_change,
                          disabled=not trace.candidates,
                          format_func=lambda identifier: next(
                              (f"{identifier} · {point_label(item.application)} · d {item.distance:.2f}"
                               for item in trace.candidates if item.candidate_id == identifier), "No recourse needed"))
        st.plotly_chart(decision_region_figure(
            original, trace.candidates, slice_value, st.session_state["recommendation"],
            selected=selected, closest=closest, feasible=feasible,
        ), width="stretch", key="decision", config={"displaylogo": False})
        if selected and selected.application.certification != slice_value:
            st.caption(f"{selected.candidate_id} belongs to certification {selected.application.certification}; switch slices to see it.")
    with search_tab:
        search_process(trace, enabled)
    with candidates_tab:
        candidates_panel(trace, selected)


if __name__ == "__main__":
    main()
