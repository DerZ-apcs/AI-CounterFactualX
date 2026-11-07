"""Exact Plotly decision regions; no search grid or sampled decision boundary."""

from collections.abc import Sequence

import plotly.graph_objects as go

from core.generator import Candidate
from core.model import Application, EXPERIENCE_THRESHOLD, INCOME_THRESHOLD, predict


def decision_region_figure(
    original: Application,
    candidates: Sequence[Candidate],
    certification: int,
    recommendation: Candidate | None = None,
) -> go.Figure:
    """Plot only points belonging to the selected certification slice.

    C=0 accepts I>=25 AND E>=3; C=1 accepts I>=25 OR E>=3. Polygons
    draw these exact continuous regions. Threshold boundaries are inclusive.
    Both slices use identical extents, including all displayed applications.
    """
    if certification not in (0, 1):
        raise ValueError("Certification slice must be 0 or 1.")
    points = [original, *(candidate.application for candidate in candidates)]
    xmax = max(35.0, *(point.income for point in points)) * 1.15
    ymax = max(5.0, *(point.experience for point in points)) * 1.15
    figure = go.Figure()

    def region(x0, y0, x1, y1, name, color, showlegend=True):
        figure.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0],
            mode="lines", fill="toself", fillcolor=color,
            line={"width": 0}, name=name, hoverinfo="skip", showlegend=showlegend,
        ))

    region(0, 0, xmax, ymax, "Rejected region", "#FCE6E6")
    if certification == 0:
        region(INCOME_THRESHOLD, EXPERIENCE_THRESHOLD, xmax, ymax,
               "Accepted region", "#D4F0E1")
    else:
        region(INCOME_THRESHOLD, 0, xmax, ymax, "Accepted region", "#D4F0E1")
        region(0, EXPERIENCE_THRESHOLD, INCOME_THRESHOLD, ymax,
               "Accepted region", "#D4F0E1", False)
    figure.add_vline(x=INCOME_THRESHOLD, line_dash="dot", line_color="#657387")
    figure.add_hline(y=EXPERIENCE_THRESHOLD, line_dash="dot", line_color="#657387")

    if original.certification == certification:
        figure.add_trace(go.Scatter(
            x=[original.income], y=[original.experience], mode="markers+text",
            text=["Original"], textposition="bottom left", name="Original",
            marker={"size": 17, "symbol": "star", "color": "#162338"},
            customdata=[[certification, "Accepted" if predict(original) else "Rejected"]],
            hovertemplate="Original<br>Income: %{x:g}<br>Experience: %{y:g}"
                          "<br>Certification: %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            cliponaxis=False,
        ))
    for feasible in (True, False):
        visible = [item for item in candidates
                   if item.application.certification == certification
                   and item.feasibility.feasible == feasible]
        if not visible:
            continue
        figure.add_trace(go.Scatter(
            x=[item.application.income for item in visible],
            y=[item.application.experience for item in visible], mode="markers+text",
            name="Feasible CF" if feasible else "Infeasible CF",
            text=[item.candidate_id for item in visible], textposition="top right",
            customdata=[[item.candidate_id, certification, item.distance] for item in visible],
            marker={"size": 13, "symbol": "circle" if feasible else "x",
                    "color": "#155EAD" if feasible else "#AD5700"},
            hovertemplate="%{customdata[0]}<br>Income: %{x:g}<br>Experience: %{y:g}"
                          "<br>Certification: %{customdata[1]}<br>Distance: %{customdata[2]:.4f}"
                          "<extra>%{fullData.name}</extra>",
            cliponaxis=False,
        ))
    if recommendation is not None and recommendation.application.certification == certification:
        figure.add_trace(go.Scatter(
            x=[recommendation.application.income], y=[recommendation.application.experience],
            mode="markers", name="Recommended",
            marker={"size": 25, "symbol": "circle-open", "color": "#6E37A8", "line": {"width": 3}},
            hoverinfo="skip", cliponaxis=False,
        ))
    figure.update_layout(
        title=f"Certification = {certification}", template="plotly_white", height=470,
        font={"size": 15, "color": "#162338"},
        margin={"l": 25, "r": 25, "t": 65, "b": 30},
        xaxis={"title": "Income (million VND/month)", "range": [0, xmax], "fixedrange": False},
        yaxis={"title": "Experience (years)", "range": [0, ymax], "fixedrange": False},
        legend={"orientation": "h", "y": -0.25, "font": {"size": 12}},
    )
    return figure
