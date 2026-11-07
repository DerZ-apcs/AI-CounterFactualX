"""Counterfactual Explorer: a lightweight, offline-capable academic demo.

Run with: python -m streamlit run app.py
All calculations live in core/; this module only orchestrates the interface.
"""

import pandas as pd
import streamlit as st

from core.constraints import Constraints
from core.generator import Candidate, evaluate_candidate, generate_counterfactuals, select_recommendation
from core.model import Application, condition_results, predict
from visualization import decision_region_figure


def point_label(application: Application) -> str:
    return f"({application.income:g}, {application.experience:g}, {application.certification:g})"


def recommendation_card(label: str, candidate: Candidate | None) -> None:
    """Use semantic Streamlit elements so recommendations are also testable."""
    if candidate is None:
        st.metric(label, "None", "No feasible counterfactual", delta_color="off")
    else:
        st.metric(label, point_label(candidate.application),
                  f"{candidate.candidate_id} · distance {candidate.distance:.2f}", delta_color="off")


def candidate_table(candidates: list[Candidate]) -> pd.DataFrame:
    """Keep numeric columns numeric for correct client-side sorting."""
    return pd.DataFrame([
        {
            "Candidate ID": item.candidate_id,
            "Income": item.application.income,
            "Experience": item.application.experience,
            "Certification": item.application.certification,
            "Prediction": "Accepted" if item.valid else "Rejected",
            "Distance": item.distance,
            "Sparsity": item.sparsity,
            "Changed Features": "; ".join(item.changes),
            "Feasibility": "Feasible" if item.feasibility.feasible else "Infeasible",
            "Constraint Details": "; ".join(item.feasibility.violations) or "All assumed limits satisfied",
            "Objective": item.objective,
        }
        for item in candidates
    ])


def mathematical_explanation(normalization: dict[str, float], lambda_value: float) -> None:
    with st.expander("Mathematics, assumptions & algorithm"):
        st.markdown("**Classifier** — two of three conditions must pass. Birth year is never used.")
        st.latex(r"f(I,E,C)=\mathbf{1}\left[\mathbf{1}[I\geq25]+\mathbf{1}[E\geq3]+\mathbf{1}[C=1]\geq2\right]")
        st.markdown("**Educational penalty objective**")
        st.latex(r"L(x')=\lambda\,\mathbf{1}[f(x')\ne1]+d(x,x')")
        st.latex(r"d(x,x')=\frac{|I-I'|}{s_I}+\frac{|E-E'|}{s_E}+\frac{|C-C'|}{s_C}")
        st.write(f"Current scales: income = {normalization['income']:g}, "
                 f"experience = {normalization['experience']:g}, certification = {normalization['certification']:g}. "
                 f"λ = {lambda_value:g}.")
        st.markdown(
            "The scales are **manually chosen educational factors**, not training-data MAD values. "
            "Lambda and L are diagnostics. A finite λ, including 10, does **not** always make an "
            "accepted point preferable under L: the unchanged rejected point has L = λ. "
            "Our recommendation instead **requires acceptance first**, then minimizes distance "
            "subject to domains, immutability, and the enabled practical limits. "
            "Consequently L = distance for every generated, accepted candidate."
        )
        st.latex(r"\min_{x'} d(x,x')\quad\text{subject to }f(x')=1,\;x'\in\mathcal{D},\;x'\in\mathcal{F}\text{ when enabled}")
        st.markdown(
            "**Feasibility:** relative to the current original, income increase must not exceed "
            "its limit; experience cannot decrease and its increase must not exceed its limit; "
            "obtaining certification requires permission. Certification remains binary and "
            "birth year always stays unchanged. These are assumed three-month limits."
        )
        st.code(
            "if predict(original) == Accepted:\n"
            "    return []  # no recourse needed\n"
            "for each predictive feature:\n"
            "    values = {original value}\n"
            "    if its condition is not satisfied:\n"
            "        add the exact minimum satisfying value\n"
            "for point in product(income_values, experience_values, cert_values):\n"
            "    preserve immutable context and validate domains\n"
            "    skip unchanged or rejected points\n"
            "    compute distance, sparsity, objective, changes, feasibility\n"
            "sort valid candidates by distance (then sparsity and stable tie-breaks)\n"
            "eligible = valid candidates satisfying mandatory constraints\n"
            "if practical constraints enabled: keep only feasible candidates\n"
            "return nearest eligible candidate, or an explicit no-solution result",
            language="text",
        )
        st.markdown(
            "**Why this search is exact here:** acceptance depends only on three monotonic threshold "
            "conditions. From any accepted point, undo changes unnecessary for its passing conditions "
            "and reduce remaining increases to their thresholds. Acceptance is preserved and positive "
            "weighted Manhattan distance cannot increase. Reducing increases also preserves these "
            "upper-bound feasibility limits. Thus one of the at most eight threshold combinations "
            "is optimal. This is a model-specific argument, not a guarantee for arbitrary black boxes. "
            "The search enumerates threshold combinations, not a fixed-step continuous grid."
        )
        st.caption("Inspired by Wachter et al.'s optimization formulation; not their Adam-based experimental implementation.")


def main() -> None:
    st.set_page_config(page_title="Counterfactual Explorer", page_icon="🔎", layout="wide")
    st.title("Counterfactual Explorer")
    st.markdown("**Understanding how small changes in input features can change AI predictions.**")
    st.caption("A synthetic screening model accepts an application when at least two of three threshold conditions pass. No training or external API is used.")

    st.subheader("1 · Original application")
    income_col, experience_col, cert_col = st.columns(3)
    with income_col:
        income = st.number_input("Monthly income (million VND/month)", min_value=0.0,
                                 value=24.0, step=0.1, format="%.4f", key="income")
    with experience_col:
        experience = st.number_input("Years of experience", min_value=0.0,
                                     value=2.0, step=0.05, format="%.4f", key="experience")
    with cert_col:
        certification = st.selectbox("Professional certification", options=[0, 1],
                                      format_func=lambda value: "Yes (1)" if value else "No (0)", key="certification")
    birth_year = None
    with st.expander("Optional immutable context"):
        if st.checkbox("Include birth year", key="include_birth_year"):
            birth_year = st.number_input("Birth year (not used in prediction)", min_value=1,
                                         value=2000, step=1, key="birth_year")
            st.caption("Editable for the original application; unchanged in every counterfactual.")
    try:
        original = Application(income, experience, certification, birth_year)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    conditions = condition_results(original)
    prediction = predict(original)
    st.metric("Prediction", "ACCEPTED" if prediction else "REJECTED",
              f"Conditions satisfied: {sum(conditions.values())} / 3", delta_color="off")
    labels = {"income": "Income ≥ 25", "experience": "Experience ≥ 3", "certification": "Certification = 1"}
    for column, (feature, passed) in zip(st.columns(3), conditions.items()):
        with column:
            st.markdown(f"{'✅' if passed else '❌'} **{labels[feature]}** — {'Passed' if passed else 'Not satisfied'}")

    st.subheader("2 · Constraint explorer")
    enabled = st.toggle("Enable Real-world Constraints", value=True, key="constraints_enabled")
    st.caption("Time horizon: 3 months · Synthetic assumptions, not verified promises about employment outcomes.")
    limit_income, limit_experience, limit_certification = st.columns(3)
    with limit_income:
        max_income = st.number_input("Maximum income increase (million VND/month)",
                                     min_value=0.0, value=5.0, step=0.5, key="max_income")
    with limit_experience:
        max_experience = st.number_input("Maximum experience increase (years)",
                                         min_value=0.0, value=0.25, step=0.05, key="max_experience")
    with limit_certification:
        can_certify = st.checkbox("Certification can be obtained", value=True, key="can_certify")
    with st.expander("Advanced settings · distance scales & lambda"):
        st.caption("All scales must be finite and strictly positive. These are manual scales, not MAD estimates. Input step sizes are editing conveniences; search does not use a grid.")
        scale_columns = st.columns(3)
        normalization = {}
        for column, name, default in zip(scale_columns, ("income", "experience", "certification"), (10.0, 5.0, 1.0)):
            with column:
                normalization[name] = st.number_input(f"{name.title()} normalization", min_value=0.0,
                                                      value=default, step=0.1, format="%.6f", key=f"scale_{name}")
        lambda_value = st.number_input("Lambda (diagnostic only)", min_value=0.0,
                                       value=10.0, step=1.0, key="lambda_value")

    try:
        constraints = Constraints(max_income, max_experience, can_certify)
        candidates = generate_counterfactuals(original, normalization=normalization,
                                               lambda_value=lambda_value, constraints=constraints)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    st.subheader("3 · Counterfactuals & recommendation")
    if st.button("Generate Counterfactuals", type="primary", key="generate"):
        st.session_state["generated"] = True
    generated = st.session_state.get("generated", False)
    closest = select_recommendation(candidates, enforce_feasibility=False)
    feasible = select_recommendation(candidates, enforce_feasibility=True)
    recommended = feasible if enabled else closest
    if prediction:
        st.success("The original application is already Accepted. No recourse is necessary for target = 1.")
        displayed = []
        recommended = None
    elif not generated:
        st.info("Click Generate Counterfactuals, then toggle constraints to compare the recommendations. Results will stay live as you edit inputs and settings.")
        displayed = []
        recommended = None
    else:
        displayed = candidates
        col_closest, col_feasible = st.columns(2)
        with col_closest:
            recommendation_card("Closest valid counterfactual", closest)
        with col_feasible:
            recommendation_card("Closest feasible counterfactual", feasible)
        if recommended is None:
            st.error("No feasible counterfactual exists under the current constraints. No infeasible solution is recommended.")
            st.write("At least two conditions must pass, but no accepted threshold combination satisfies all current limits. Review the violations in the table or relax a practical limit.")
        else:
            st.success(f"Recommended: {point_label(recommended.application)} · {recommended.candidate_id} · Distance: {recommended.distance:.2f}")
            st.write("**Required changes:** " + "; ".join(recommended.changes))
            if original.birth_year is not None:
                st.caption(f"Birth year: {original.birth_year} → {recommended.application.birth_year} (immutable; excluded from prediction and distance).")
        if closest is not None and not closest.feasibility.feasible:
            st.warning(f"The closest valid option, {closest.candidate_id}, violates the assumed practical limits: "
                       + " ".join(closest.feasibility.violations))
            if feasible is not None:
                st.write(f"With constraints OFF: **{point_label(closest.application)}**, distance **{closest.distance:.2f}**. "
                         f"With constraints ON: **{point_label(feasible.application)}**, distance **{feasible.distance:.2f}**. "
                         "The feasible option costs more in this distance metric, but satisfies the assumed limits.")
        elif closest is not None:
            st.info("The closest valid option is also feasible, so the constraint toggle does not change this recommendation.")
        if not enabled:
            st.caption("Practical limits are ignored for recommendation. The table still assesses feasibility using the limits above. Feature domains and immutable context remain enforced.")

        frame = candidate_table(candidates)

        def highlight(row):
            is_recommended = recommended is not None and row["Candidate ID"] == recommended.candidate_id
            return ["background-color: #D4F0E1; color: #162338; font-weight: 600" if is_recommended else ""] * len(row)

        st.dataframe(frame.style.apply(highlight, axis=1), hide_index=True, width="stretch",
                     column_config={"Distance": st.column_config.NumberColumn(format="%.4f"),
                                    "Objective": st.column_config.NumberColumn(format="%.4f")})
        st.caption("Click column headers to sort. Green row = current recommendation. Candidate IDs are assigned by the current distance ranking. Validity means Accepted; feasibility means satisfying the assumed limits.")
        with st.expander("Inspect each candidate · changes, distances & feasibility"):
            for item in candidates:
                st.markdown(f"**{item.candidate_id} — {point_label(item.application)}**")
                st.write("; ".join(item.changes))
                terms = [f"|{getattr(original, name):g} − {getattr(item.application, name):g}| / {normalization[name]:g}"
                         for name in normalization]
                parts = " + ".join(f"{item.contributions[name]:.6g}" for name in normalization)
                st.code("d = " + " + ".join(terms) + f" = {parts} = {item.distance:.6g}", language="text")
                st.write(f"Validity: {item.valid} · Sparsity: {item.sparsity} · "
                         f"Feasible: {item.feasibility.feasible} · L = {item.objective:.6g}")
                for violation in item.feasibility.violations:
                    st.caption(violation)

    st.subheader("4 · Decision regions")
    for column, cert in zip(st.columns(2), (0, 1)):
        with column:
            st.plotly_chart(decision_region_figure(original, displayed, cert, recommended),
                            width="stretch", key=f"decision_{cert}", config={"displaylogo": False})
    st.caption("Dotted lines are inclusive thresholds at income 25 and experience 3. Each point appears only in its own certification view. Blue circles: feasible; orange crosses: infeasible; purple ring: recommended. Hover or zoom for detail.")
    mathematical_explanation(normalization, lambda_value)
    with st.expander("Why acceptance alone is not enough"):
        example_application = Application(max(500.0, income), max(3.0, experience),
                                          certification, original.birth_year)
        example = evaluate_candidate(original, example_application, normalization=normalization,
                                      lambda_value=lambda_value, constraints=constraints)
        st.write(f"An intentionally excessive income example: **{point_label(example.application)}**. "
                 f"Prediction: Accepted · Distance: **{example.distance:.2f}** · "
                 f"Feasible under current limits: **{example.feasibility.feasible}**.")
        st.caption("Computed from current inputs and settings; shown separately from the optimal search. At default inputs its distance is 47.80.")
        st.write("A prediction flip alone says little about proximity or actionability.")
    st.info("**The nearest counterfactual is not necessarily the nearest feasible counterfactual.**")
    st.markdown("### Limitations & attribution")
    st.markdown(
        "- The classifier is synthetic; income as a hiring feature can introduce unfair bias.\n"
        "- Prediction changes do not establish causality or guarantee real-world outcomes.\n"
        "- Feasibility uses assumed three-month limits; it does not capture all personal costs or opportunities.\n"
        "- Threshold enumeration is specific to this model, not a general black-box search method.\n"
        "- This is not a reproduction of Wachter et al.'s Adam optimization experiments.\n\n"
        "Wachter, S., Mittelstadt, B., & Russell, C. (2018). *Counterfactual Explanations without "
        "Opening the Black Box: Automated Decisions and the GDPR.* [Paper](https://arxiv.org/abs/1711.00399). "
        "Their optimization formulation and MAD-weighted distance approach motivate the lesson; "
        "our classifier, manual scales, enumeration, and feasibility assumptions are educational choices."
    )


if __name__ == "__main__":
    main()
