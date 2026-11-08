"""Progressively disclosed teaching notes, kept off the primary dashboard."""

import streamlit as st

from core.constraints import Constraints
from core.generator import evaluate_candidate
from core.generator import SearchTrace
from core.model import Application
from analytics_views import optimality_explanation


def render_details(
    original: Application,
    normalization: dict[str, float],
    lambda_value: float,
    constraints: Constraints,
    *,
    trace: SearchTrace | None = None,
    enforce_feasibility: bool = True,
) -> None:
    """Preserve the V1 mathematical content in collapsed, focused sections."""
    with st.expander("Mathematical Details", expanded=False):
        st.latex(r"f(I,E,C)=\mathbf{1}\left[\mathbf{1}[I\geq25]+\mathbf{1}[E\geq3]+\mathbf{1}[C=1]\geq2\right]")
        st.latex(r"L(x')=\lambda\,\mathbf{1}[f(x')\ne1]+d(x,x')")
        st.latex(r"d(x,x')=\frac{|I-I'|}{s_I}+\frac{|E-E'|}{s_E}+\frac{|C-C'|}{s_C}")
        st.write(f"Current scales: I = {normalization['income']:g}, E = {normalization['experience']:g}, "
                 f"C = {normalization['certification']:g}. λ = {lambda_value:g}.")
        st.markdown(
            "**Prediction loss** is 0 for Accepted and 1 otherwise. Lambda and L are educational "
            "diagnostics: no finite λ, including 10, guarantees an accepted penalty minimum for "
            "all inputs and scales. The unchanged rejected original has L = λ.\n\n"
            "**Recommendation:** require target = 1 first, then minimize distance subject to domains, "
            "immutability, and the enabled practical limits. L equals distance for accepted candidates.\n\n"
            "**Validity:** Accepted. **Proximity:** normalized Manhattan distance. **Sparsity:** number "
            "of predictive features changed. **Feasibility:** satisfies configured assumptions. "
            "**Actionability:** broader personal costs and opportunities, not established by this demo.\n\n"
            "Normalization factors are **manual synthetic scales**, not empirical MAD values. "
            "Birth year is excluded from prediction, distance, and sparsity."
        )
        if trace is not None:
            optimality_explanation(trace, normalization, constraints,
                                   enforce_feasibility=enforce_feasibility, scope="Current recommendation")
    with st.expander("Search Algorithm", expanded=False):
        st.code(
            "validate original, scales, lambda, and practical limits\n"
            "if predict(original) == Accepted: stop; no recourse needed\n"
            "for each feature:\n"
            "    options = {original value}\n"
            "    if condition fails: add exact minimum satisfying value\n"
            "for point in itertools.product(feature options):\n"
            "    preserve context; evaluate prediction, distance, and feasibility\n"
            "    record point in trace (including original and rejected points)\n"
            "valid = changed points with prediction == Accepted\n"
            "rank valid by distance, sparsity, then stable feature values\n"
            "eligible = valid with mandatory domains and immutable context\n"
            "if constraints ON: retain only practically feasible points\n"
            "recommend nearest eligible point, or explicitly report none",
            language="text",
        )
        st.markdown(
            "**Why threshold enumeration is exact here:** acceptance depends only on monotonic "
            "threshold conditions. Undo unnecessary changes and reduce required increases to their "
            "exact thresholds. Acceptance is preserved and positively weighted Manhattan distance "
            "cannot increase. Reducing increases also preserves these upper-bound practical limits. "
            "Thus an optimum exists among the enumerated combinations. This argument does not "
            "apply to arbitrary black-box models or feasibility sets.\n\n"
            "**Complexity:** at most 2³ = 8 combinations; O(k × 2ᵏ) evaluation and "
            "O(2ᵏ log 2ᵏ) ranking for k binary threshold conditions. Here k = 3. "
            "Numeric input steps are editing conveniences, not a continuous search grid.\n\n"
            "Trace IDs Tn identify rejected product-order points. Dashboard CF IDs are assigned "
            "using default-scale ranking for the current original and remain stable when scales "
            "or scenarios change. The V2 enumeration API retains rank-based IDs for compatibility. "
            "The unchanged original is inspected but never recommended."
        )
    with st.expander("Assumptions & Limitations", expanded=False):
        st.markdown("**The nearest counterfactual is not necessarily the nearest feasible counterfactual.**")
        st.markdown(
            f"- **Three-month assumptions:** income increase ≤ {constraints.max_income_increase:g} "
            f"million VND/month; experience increase ≤ {constraints.max_experience_increase:g} years "
            "and no decrease; income cannot decrease in practical scenarios; certification requires permission; birth year never changes.\n"
            "- All limits are relative to the current original. Turning constraints OFF ignores only "
            "optional practical limits. Both comparison cards always solve their labeled problems.\n"
            "- The classifier is synthetic; income as a hiring feature can introduce unfair bias.\n"
            "- Prediction changes do not establish causality or guarantee employment outcomes.\n"
            "- Feasibility under assumptions does not establish real-world actionability.\n"
            "- Enumeration is model-specific, not A*, DiCE, gradient descent, or a general black-box optimizer.\n"
            "- Values displayed in cards are rounded; calculations use unrounded floats."
        )
        if original.birth_year is not None:
            st.caption(f"Birth year: {original.birth_year} → {original.birth_year} (immutable, nonpredictive).")
        example = evaluate_candidate(
            original,
            Application(max(500.0, original.income), max(3.0, original.experience),
                        original.certification, original.birth_year),
            normalization=normalization, lambda_value=lambda_value, constraints=constraints,
        )
        st.caption(f"Separate excessive-income illustration (not a search result): "
                   f"({example.application.income:g}, {example.application.experience:g}, {example.application.certification:g}); "
                   f"Accepted · d = {example.distance:.2f} · Feasible: {example.feasibility.feasible}. "
                   "At defaults, d = 47.80.")
        st.markdown(
            "**Attribution:** Wachter, S., Mittelstadt, B., & Russell, C. (2018). "
            "*Counterfactual Explanations without Opening the Black Box: Automated Decisions and the GDPR.* "
            "[Paper](https://arxiv.org/abs/1711.00399). Their counterfactual optimization formulation "
            "and MAD-weighted distance approach motivate the lesson. Our synthetic classifier, manual "
            "scales, enumeration, and feasibility assumptions are educational choices; this is not "
            "a reproduction of their Adam-based experiments."
        )
