"""Exact Plotly decision regions; no search grid or sampled decision boundary."""

from collections.abc import Sequence

import plotly.graph_objects as go

from core.generator import Candidate
from core.model import Application, EXPERIENCE_THRESHOLD, INCOME_THRESHOLD, predict
from ui_theme import COLORS, SANS, SERIF, plotly_presentation


def decision_region_figure(
    original: Application,
    candidates: Sequence[Candidate],
    certification: int,
    recommendation: Candidate | None = None,
    *,
    selected: Candidate | None = None,
    closest: Candidate | None = None,
    feasible: Candidate | None = None,
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

    region(0, 0, xmax, ymax, "Rejected region", COLORS["rejected_region"])
    if certification == 0:
        region(INCOME_THRESHOLD, EXPERIENCE_THRESHOLD, xmax, ymax,
               "Accepted region", COLORS["accepted_region"])
    else:
        region(INCOME_THRESHOLD, 0, xmax, ymax, "Accepted region", COLORS["accepted_region"])
        region(0, EXPERIENCE_THRESHOLD, INCOME_THRESHOLD, ymax,
               "Accepted region", COLORS["accepted_region"], False)
    figure.add_vline(x=INCOME_THRESHOLD, line_dash="dot", line_color=COLORS["boundary"])
    figure.add_hline(y=EXPERIENCE_THRESHOLD, line_dash="dot", line_color=COLORS["boundary"])

    if original.certification == certification:
        figure.add_trace(go.Scatter(
            x=[original.income], y=[original.experience], mode="markers+text",
            text=["Original"], textposition="bottom left", name="Original",
            marker={"size": 17, "symbol": "star", "color": COLORS["ink"]},
            customdata=[[certification, "Accepted" if predict(original) else "Rejected"]],
            hovertemplate="Original<br>Income: %{x:g}<br>Experience: %{y:g}"
                          "<br>Certification: %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            cliponaxis=False,
        ))
    for is_feasible in (True, False):
        visible = [item for item in candidates
                   if item.application.certification == certification
                   and item.feasibility.feasible == is_feasible]
        if not visible:
            continue
        figure.add_trace(go.Scatter(
            x=[item.application.income for item in visible],
            y=[item.application.experience for item in visible], mode="markers",
            name="Feasible CF" if is_feasible else "Infeasible CF",
            text=[item.candidate_id for item in visible], textposition="top right",
            customdata=[[item.candidate_id, certification, item.distance] for item in visible],
            hovertext=[f"Feasible: {'Yes' if item.feasibility.feasible else 'No'}"
                       f"<br>Sparsity: {item.sparsity}" for item in visible],
            marker={"size": 13, "symbol": "circle" if is_feasible else "x",
                    "color": COLORS["feasible"] if is_feasible else COLORS["infeasible"]},
            hovertemplate="%{customdata[0]}<br>Income: %{x:g}<br>Experience: %{y:g}"
                          "<br>Certification: %{customdata[1]}<br>Distance: %{customdata[2]:.4f}"
                          "<br>%{hovertext}"
                          "<extra>%{fullData.name}</extra>",
            cliponaxis=False,
        ))
    for candidate, name, symbol, color, size in (
        (closest, "Closest CF", "diamond-open", COLORS["ink"], 22),
        (feasible, "Closest feasible", "square-open", COLORS["accepted"], 22),
        (recommendation, "Recommended", "circle-open", COLORS["accent"], 28),
        (selected, "Selected", "circle-open", COLORS["accent"], 34),
    ):
        if candidate is None or candidate.application.certification != certification:
            continue
        if name == "Recommended" and candidate == selected:
            continue  # One selection ring is enough when it is also recommended.
        label = candidate.candidate_id if name == "Selected" or (name == "Closest CF" and candidate != selected) else None
        figure.add_trace(go.Scatter(
            x=[candidate.application.income], y=[candidate.application.experience],
            mode="markers+text" if label else "markers", name=name,
            text=[label] if label else None, textposition="top right",
            marker={"size": size, "symbol": symbol, "color": color, "line": {"width": 2}},
            hoverinfo="skip", cliponaxis=False,
        ))
    figure.update_layout(
        template="plotly_white", height=380,
        margin={"l": 20, "r": 25, "t": 12, "b": 35},
        xaxis={"title": {"text": "Income (M VND/month)", "font": {"family": SANS, "size": 14, "color": COLORS["ink"]}},
               "range": [0, xmax], "showgrid": False,
               "showline": True, "linecolor": COLORS["border"], "tickfont": {"size": 13, "color": COLORS["muted"]}},
        yaxis={"title": {"text": "Experience (years)", "font": {"family": SANS, "size": 14, "color": COLORS["ink"]}},
               "range": [0, ymax], "showgrid": False,
               "showline": True, "linecolor": COLORS["border"], "tickfont": {"size": 13, "color": COLORS["muted"]}},
        legend={"orientation": "h", "y": -0.25, "font": {"family": SANS, "size": 12, "color": COLORS["muted"]},
                "bgcolor": "rgba(0,0,0,0)"},
        **plotly_presentation(),
    )
    return figure


def candidate_distance_figure(
    candidates: Sequence[Candidate], selected: Candidate | None = None,
) -> go.Figure:
    """Current-metric distances in ranked order, with explicit feasibility cues."""
    figure = go.Figure(go.Bar(
        x=[item.distance for item in candidates],
        y=[item.candidate_id for item in candidates], orientation="h",
        text=[f"{item.distance:.2f}" for item in candidates], textposition="outside",
        customdata=[[
            item.application.income, item.application.experience, item.application.certification,
            "Yes" if item.feasibility.feasible else "No",
        ] for item in candidates],
        marker={
            "color": [COLORS["feasible"] if item.feasibility.feasible else COLORS["infeasible"] for item in candidates],
            "pattern": {"shape": ["" if item.feasibility.feasible else "/" for item in candidates]},
            "line": {"width": [3 if item == selected else 0 for item in candidates], "color": COLORS["accent"]},
        },
        hovertemplate="%{y}<br>(%{customdata[0]:g}, %{customdata[1]:g}, %{customdata[2]})"
                      "<br>Distance: %{x:.6g}<br>Feasible: %{customdata[3]}<extra></extra>",
    ))
    figure.update_layout(
        title={"text": "Distance sensitivity", "font": {"family": SERIF, "size": 18, "color": COLORS["ink"]}},
        template="plotly_white", height=230, showlegend=False,
        margin={"l": 5, "r": 35, "t": 35, "b": 15},
        xaxis={"title": {"text": "Normalized distance", "font": {"family": SANS, "size": 13, "color": COLORS["ink"]}},
               "range": [0, max((item.distance for item in candidates), default=1) * 1.18],
               "gridcolor": COLORS["border"], "zerolinecolor": COLORS["border"],
               "tickfont": {"size": 12, "color": COLORS["muted"]}},
        yaxis={"autorange": "reversed", "tickfont": {"size": 12, "color": COLORS["muted"]}},
        **plotly_presentation(),
    )
    return figure
