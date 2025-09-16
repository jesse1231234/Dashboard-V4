# ui/charts.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _pct(x):
    """Convert a fraction (0..1) Series/array to 0..100 list safely."""
    if x is None:
        return []
    s = pd.Series(x, dtype="float64")
    return (s * 100.0).tolist()


def chart_gradebook_combo(df: pd.DataFrame) -> go.Figure:
    """
    Two straight lines on a single 0–100% y-axis:
      - Avg % Turned In
      - Avg Average Excluding Zeros
    Expects fractions (0..1) in the DataFrame.
    """
    if df is None or df.empty:
        return go.Figure()

    x = df["Module"].astype(str).tolist()
    y_turnedin = _pct(df["Avg % Turned In"])
    y_excl0 = _pct(df["Avg Average Excluding Zeros"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=y_turnedin, mode="lines+markers",
            name="% Turned In", hovertemplate="%{y:.1f}%<extra>% Turned In</extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=y_excl0, mode="lines+markers",
            name="Avg Excl Zeros", hovertemplate="%{y:.1f}%<extra>Avg Excl Zeros</extra>"
        )
    )

    fig.update_yaxes(title_text="Percent", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title_text="Module")
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h"),
        hovermode="x unified",
    )
    return fig


def chart_echo_combo(module_table: pd.DataFrame) -> go.Figure:
    """
    Stacked columns + dual-axis lines:
      - Bars (stacked): # of Students, # of Unique Viewers (# of Students Viewing)
      - Lines (secondary axis): Average View %, Overall View %
    Expects fractions (0..1) for the percent series.
    """
    if module_table is None or module_table.empty:
        return go.Figure()

    df = module_table.copy()

    # Coerce expected columns; fall back to zeros if missing
    x = df["Module"].astype(str).tolist()

    n_students = df["# of Students"].tolist() if "# of Students" in df else [0] * len(df)
    n_viewers = df["# of Students Viewing"].tolist() if "# of Students Viewing" in df else [0] * len(df)

    avg_view = _pct(df["Average View %"]) if "Average View %" in df else [0] * len(df)
    overall_view = _pct(df["Overall View %"]) if "Overall View %" in df else [0] * len(df)

    fig = go.Figure()

    # Stacked bars
    fig.add_trace(
        go.Bar(
            x=x, y=n_students, name="# of Students",
            hovertemplate="%{y:,}<extra># of Students</extra>", offsetgroup=0
        )
    )
    fig.add_trace(
        go.Bar(
            x=x, y=n_viewers, name="# of Unique Viewers",
            hovertemplate="%{y:,}<extra># of Unique Viewers</extra>", offsetgroup=0
        )
    )

    # Lines on secondary axis
    fig.add_trace(
        go.Scatter(
            x=x, y=avg_view, mode="lines+markers", name="Avg View %",
            yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg View %</extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=overall_view, mode="lines+markers", name="Avg Overall View %",
            yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg Overall View %</extra>"
        )
    )

    fig.update_layout(
        yaxis=dict(title="Students"),
        yaxis2=dict(title="Percent", overlaying="y", side="right", range=[0, 100], ticksuffix="%"),
        barmode="stack",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h"),
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="Module")

    return fig
