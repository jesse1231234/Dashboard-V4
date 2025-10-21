# ui/charts.py
from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# Theme + typography that follow Streamlit's light/dark selection
TEMPLATE = "plotly_dark" if (st.get_option("theme.base") or "light") == "dark" else "plotly_white"
FONT = dict(family="Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif")


def _pct(series_like) -> list[float]:
    """Convert a numeric series of 0..1 fractions to 0..100 list (handles None/NaN)."""
    if series_like is None:
        return []
    s = pd.Series(series_like, dtype="float64")
    return (s * 100.0).tolist()


def chart_gradebook_combo(
    df: pd.DataFrame,
    title: str = "Canvas Data",
    autoscale: bool = True,
) -> go.Figure:
    """
    Two straight lines on a single percent axis:
      - Avg % Turned In
      - Avg Average Excluding Zeros
    Expects fraction columns in 0..1.
    """
    if df is None or df.empty:
        return go.Figure()

    data = df.copy()
    x = data["Module"].astype(str).tolist()
    y_turnedin = _pct(data.get("Avg % Turned In", pd.Series([np.nan] * len(data))))
    y_excl0 = _pct(data.get("Avg Average Excluding Zeros", pd.Series([np.nan] * len(data))))

    fig = go.Figure()

    # Straight lines (no smoothing)
    fig.add_trace(go.Scatter(
        x=x, y=y_turnedin, mode="lines+markers",
        name="% Turned In",
        hovertemplate="%{y:.1f}%<extra>% Turned In</extra>"
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y_excl0, mode="lines+markers",
        name="Avg Excl Zeros",
        hovertemplate="%{y:.1f}%<extra>Avg Excl Zeros</extra>"
    ))

    # Axes
    if autoscale:
        fig.update_yaxes(title_text="Percent", autorange=True, rangemode="tozero", ticksuffix="%")
    else:
        fig.update_yaxes(title_text="Percent", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title_text="Module", showgrid=False)

    # Layout polish
    fig.update_layout(
        template=TEMPLATE,
        font=FONT,
        title=title,
        title_x=0.0,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,           # legend above plot area
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=10, t=80, b=30),
        hovermode="x unified",
        legend_title_text="",
    )
    # Subtle grid on y
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.08)")
    return fig


def chart_echo_combo(
    module_table: pd.DataFrame,
    students_total: Optional[int] = None,
    title: str = "Echo Data",
    autoscale: bool = True,
) -> go.Figure:
    """
    Filled bars to cohort total + percent lines:
      - Bars (stacked): '# of Unique Viewers' + 'Not Viewed' = total students (constant per module)
      - Lines (on secondary axis): 'Average View %' and 'Avg Overall View %'
    Expects fraction columns in 0..1.
    """
    if module_table is None or module_table.empty:
        return go.Figure()

    df = module_table.copy()
    x = df["Module"].astype(str).tolist()

    # Viewers series (module-level average unique viewers from your pipeline)
    viewers_col = "# of Students Viewing" if "# of Students Viewing" in df.columns else "# of Unique Viewers"
    viewed_s = pd.to_numeric(df.get(viewers_col, pd.Series([0] * len(df))), errors="coerce").fillna(0)

    # Establish a total per module
    if students_total and students_total > 0:
        total_s = pd.Series([int(students_total)] * len(df), index=df.index)
    elif "# of Students" in df.columns:
        total_s = pd.to_numeric(df["# of Students"], errors="coerce").fillna(0)
        if not (total_s > 0).any():
            total_s = None
    else:
        total_s = None

    # Fallback: ensure non-negative totals, at least equal to viewers where possible
    if total_s is None:
        total_s = viewed_s.clip(lower=0)

    # Clamp & compute complementary not-viewed
    viewed_s = viewed_s.clip(lower=0)
    total_s = total_s.clip(lower=0)
    viewed_s = viewed_s.where(viewed_s <= total_s, total_s)

    viewed = viewed_s.round(0).astype(int).tolist()
    not_viewed = (total_s - viewed_s).clip(lower=0).round(0).astype(int).tolist()

    # Percent lines (secondary axis)
    avg_view = _pct(df.get("Average View %", pd.Series([np.nan] * len(df))))
    overall_view = _pct(df.get("Overall View %", pd.Series([np.nan] * len(df))))

    fig = go.Figure()

    # Bars: Viewed + Not Viewed = Total
    fig.add_trace(go.Bar(
        x=x, y=viewed, name="# of Unique Viewers",
        hovertemplate="%{y:,}<extra># of Unique Viewers</extra>", offsetgroup=0
    ))
    fig.add_trace(go.Bar(
        x=x, y=not_viewed, name="Not Viewed",
        hovertemplate="%{y:,}<extra>Not Viewed</extra>", offsetgroup=0
    ))

    # Lines (secondary axis)
    if any(pd.notna(avg_view)):
        fig.add_trace(go.Scatter(
            x=x, y=avg_view, mode="lines+markers", name="Avg View %",
            yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg View %</extra>"
        ))
    if any(pd.notna(overall_view)):
        fig.add_trace(go.Scatter(
            x=x, y=overall_view, mode="lines+markers", name="Avg Overall View %",
            yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg Overall View %</extra>"
        ))

    # Axes
    if autoscale:
        yaxis = dict(title="Students", autorange=True, rangemode="tozero")
        yaxis2 = dict(
            title="Percent", overlaying="y", side="right",
            autorange=True, rangemode="tozero", ticksuffix="%"
        )
    else:
        yaxis = dict(title="Students", rangemode="tozero", autorange=False)
        yaxis2 = dict(title="Percent", overlaying="y", side="right", range=[0, 100], ticksuffix="%")

    # Layout polish
    fig.update_layout(
        template=TEMPLATE,
        font=FONT,
        title=title,
        title_x=0.0,
        barmode="stack",
        yaxis=yaxis,
        yaxis2=yaxis2,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,           # legend above plot area
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=10, t=80, b=30),
        hovermode="x unified",
        legend_title_text="",
    )
    fig.update_xaxes(title_text="Module", showgrid=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.08)")
    return fig
