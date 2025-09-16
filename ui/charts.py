# ui/charts.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _pct(x):
    if x is None:
        return []
    s = pd.Series(x, dtype="float64")
    return (s * 100.0).tolist()


def chart_gradebook_combo(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return go.Figure()

    x = df["Module"].astype(str).tolist()
    y_turnedin = _pct(df["Avg % Turned In"])
    y_excl0 = _pct(df["Avg Average Excluding Zeros"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y_turnedin, mode="lines+markers",
                             name="% Turned In", hovertemplate="%{y:.1f}%<extra>% Turned In</extra>"))
    fig.add_trace(go.Scatter(x=x, y=y_excl0, mode="lines+markers",
                             name="Avg Excl Zeros", hovertemplate="%{y:.1f}%<extra>Avg Excl Zeros</extra>"))

    fig.update_yaxes(title_text="Percent", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title_text="Module")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"), hovermode="x unified")
    return fig


def chart_echo_combo(
    module_table: pd.DataFrame,
    students_total: int | None = None,
    barmode: str = "stack",   # keep stacked per your spec; switch to "group" if you prefer side-by-side
) -> go.Figure:
    """
    Stacked columns + dual-axis lines:
      - Bars: "# of Students" (constant across modules) and "# of Unique Viewers" (aka "# of Students Viewing")
      - Lines (secondary axis): Average View %, Overall View %
    Ensures Y-axis has headroom so labels never get cut off.
    """
    if module_table is None or module_table.empty:
        return go.Figure()

    df = module_table.copy()

    # X labels
    x = df["Module"].astype(str).tolist()

    # Counts
    viewers_col = "# of Students Viewing" if "# of Students Viewing" in df else "# of Unique Viewers"
    n_viewers = pd.to_numeric(df.get(viewers_col, pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int).tolist()

    if students_total is not None:
        n_students = [int(students_total)] * len(x)
    else:
        n_students = pd.to_numeric(df.get("# of Students", pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int).tolist()

    # Percent lines (0..1 -> 0..100)
    avg_view = _pct(df.get("Average View %", pd.Series([np.nan]*len(df))))
    overall_view = _pct(df.get("Overall View %", pd.Series([np.nan]*len(df))))

    # Compute headroom for the left axis
    if barmode == "stack":
        stacked_tops = [a + b for a, b in zip(n_students, n_viewers)]
        max_left = max(stacked_tops + ([students_total] if students_total else []), default=0)
    else:
        max_left = max(max(n_students or [0]), max(n_viewers or [0]), (students_total or 0))
    # Add 10–15% headroom to avoid cutoffs
    headroom = max(5, int(round(max_left * 0.12)))
    y_max = max_left + headroom

    fig = go.Figure()

    # Bars
    fig.add_trace(
        go.Bar(x=x, y=n_students, name="# of Students",
               hovertemplate="%{y:,}<extra># of Students</extra>", offsetgroup=0)
    )
    fig.add_trace(
        go.Bar(x=x, y=n_viewers, name="# of Unique Viewers",
               hovertemplate="%{y:,}<extra># of Unique Viewers</extra>", offsetgroup=0)
    )

    # Lines on secondary axis
    if any(pd.notna(avg_view)):
        fig.add_trace(
            go.Scatter(x=x, y=avg_view, mode="lines+markers", name="Avg View %",
                       yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg View %</extra>")
        )
    if any(pd.notna(overall_view)):
        fig.add_trace(
            go.Scatter(x=x, y=overall_view, mode="lines+markers", name="Avg Overall View %",
                       yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg Overall View %</extra>")
        )

    fig.update_layout(
        barmode=barmode,
        yaxis=dict(title="Students", range=[0, y_max]),
        yaxis2=dict(title="Percent", overlaying="y", side="right", range=[0, 100], ticksuffix="%"),
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h"),
        hovermode="x unified",
    )

    # Optional: draw a horizontal line at the total student count for clarity
    if students_total:
        try:
            fig.add_hline(y=students_total, line_dash="dot", line_width=1)
        except Exception:
            # Fallback for older Plotly versions
            fig.add_shape(type="line", x0=-0.5, x1=len(x)-0.5, y0=students_total, y1=students_total)

    fig.update_xaxes(title_text="Module")
    return fig
