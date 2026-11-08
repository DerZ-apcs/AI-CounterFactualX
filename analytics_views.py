"""Compact V3 analytical views, reusing the validated trace and Plotly chart."""

import pandas as pd
import streamlit as st

from core.constraints import Constraints
from core.generator import SearchTrace, select_recommendation
from core.model import Application, condition_results, predict
from core.scenarios import ScenarioResult
from core.sensitivity import ranking_insight, threshold_costs
from visualization import candidate_distance_figure


def point_label(application: Application) -> str:
    return f"({application.income:g}, {application.experience:g}, {application.certification:g})"


def optimality_explanation(
    trace: SearchTrace, normalization: dict[str, float], constraints: Constraints | None,
    *, enforce_feasibility: bool, scope: str,
    key: str | None = None,
) -> None:
    """A truthful calculation-based proof over the exact threshold candidate set."""
    with st.expander("Why this counterfactual?", expanded=False, key=key or f"why_{scope}", on_change="rerun") as panel:
        if not panel.open:
            return
        st.caption(f"Scope: {scope} · Current metric")
        passed = sum(condition_results(trace.original).values())
        needed = max(0, 2 - passed)
        if predict(trace.original):
            st.info("Original already Accepted. No recourse or optimization is necessary.")
            return
        costs = threshold_costs(trace.original, normalization, constraints=constraints,
                                enforce_feasibility=enforce_feasibility)
        st.write(f"{passed} / 3 conditions already pass; {needed} additional condition(s) required.")
        st.dataframe(pd.DataFrame([
            {"Condition": item.feature.title(), "Original": item.original, "Required value": item.required,
             "Change": item.required - item.original, "Cost": item.cost, "Reachable": item.reachable,
             "Reason": "; ".join(item.reasons) or "Available / already satisfied"}
            for item in costs
        ]), hide_index=True, width="stretch", column_config={"Cost": st.column_config.NumberColumn(format="%.6g")})
        best = select_recommendation(trace.candidates, enforce_feasibility=enforce_feasibility)
        st.dataframe(pd.DataFrame([
            {"CF": item.candidate_id, "(I, E, C)": point_label(item.application), "Distance": item.distance,
             "Eligible": item.feasibility.immutable_preserved and (not enforce_feasibility or item.feasibility.feasible),
             "Excluded by": "; ".join(item.feasibility.violations) if enforce_feasibility else "—"}
            for item in trace.candidates
        ]), hide_index=True, width="stretch")
        if best:
            st.success(f"Minimum eligible distance = {best.distance:.6g}: {best.candidate_id} {point_label(best.application)}.")
            parts = " + ".join(f"{value:.6g}" for value in best.contributions.values())
            st.code(f"d = {parts} = {best.distance:.6g}", language="text")
        else:
            reachable_missing = sum(item.reachable and item.required > item.original for item in costs)
            st.warning(f"No feasible CF in {scope}: only {reachable_missing} additional condition(s) reachable; {needed} required.")
            for item in costs:
                if not item.reachable:
                    st.write(f"**{item.feature.title()}:** " + " ".join(item.reasons))
        st.caption("Exact for this monotonic threshold model and these constraints: moving an accepted point back to its necessary thresholds cannot increase positive weighted Manhattan distance. No arbitrary black-box guarantee.")


def sensitivity_view(
    baseline: SearchTrace, trace: SearchTrace, normalization: dict[str, float], constraints: Constraints,
) -> None:
    """Baseline/current distance comparison with stable IDs and feasible rankings."""
    st.caption(ranking_insight(baseline, trace, normalization))
    if not trace.candidates:
        optimality_explanation(trace, normalization, constraints, enforce_feasibility=False,
                               scope="No Constraints", key="sensitivity_optimality")
        return
    best = select_recommendation(trace.candidates, enforce_feasibility=False)
    feasible_order = {item.application: rank for rank, item in enumerate(
        (item for item in trace.candidates if item.feasibility.feasible), 1)}
    baseline_distances = {item.application: item.distance for item in baseline.candidates}
    chart_column, table_column = st.columns([3, 2])
    with chart_column:
        st.plotly_chart(candidate_distance_figure(trace.candidates, best), width="stretch",
                        key="sensitivity_distances", config={"displaylogo": False})
    with table_column:
        st.dataframe(pd.DataFrame([
            {"CF": item.candidate_id, "Default d": baseline_distances[item.application],
             "Current d": item.distance, "Feasible rank": str(feasible_order.get(item.application, "—"))}
            for item in trace.candidates
        ]), hide_index=True, width="stretch", column_config={
            "Default d": st.column_config.NumberColumn(format="%.4f"),
            "Current d": st.column_config.NumberColumn(format="%.4f"),
        })
    optimality_explanation(trace, normalization, constraints, enforce_feasibility=False,
                           scope="No Constraints", key="sensitivity_optimality")


def scenario_view(results: dict[str, ScenarioResult], selected_name: str, normalization: dict[str, float]) -> None:
    """All scenarios share the same input, current metric, and cached applications."""
    rows = [
        {"Scenario": name, "Best CF": point_label(result.recommendation.application) if result.recommendation
         else "Not needed" if result.status == "Already Accepted" else "—",
         "Distance": f"{result.distance:.4f}" if result.distance is not None else "—", "Status": result.status}
        for name, result in results.items()
    ]
    frame = pd.DataFrame(rows)
    # This four-row summary is presentation-only. Text avoids Streamlit's
    # numeric-null placeholder "None"; core results retain float | None values.
    styled = frame.style.apply(
        lambda row: ["background-color: #F2EAFA; color: #162338" if row["Scenario"] == selected_name else ""] * len(row),
        axis=1,
    )
    st.dataframe(styled, hide_index=True, width="stretch", key="scenario_comparison",
                 column_config={"Distance": st.column_config.TextColumn(
                     help="Normalized distance; — means no new counterfactual is recommended.")})
    result = results[selected_name]
    if result.status == "No feasible CF":
        st.warning(f"No feasible CF in {selected_name}. No candidate reaches the target under this scenario.")
    elif result.status == "Already Accepted":
        st.info("Original already Accepted. No recourse needed in any scenario.")
    if selected_name == "Custom":
        limits = result.scenario.constraints
        st.caption(f"Custom: income +{limits.max_income_increase:g} M VND, experience +{limits.max_experience_increase:g} years, "
                   f"certification {'allowed' if limits.can_obtain_certification else 'unavailable'} · Edit in Settings ⚙.")
    optimality_explanation(result.trace, normalization, result.scenario.constraints,
                           enforce_feasibility=result.scenario.enforce_feasibility, scope=selected_name,
                           key=f"scenario_optimality_{selected_name}")
