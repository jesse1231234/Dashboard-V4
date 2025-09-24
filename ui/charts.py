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

def chart_gradebook_combo(df: pd.DataFrame, title: str = "Canvas Data", autoscale: bool = True) -> go.Figure:
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

    if autoscale:
        fig.update_yaxes(title_text="Percent", autorange=True, rangemode="tozero", ticksuffix="%")
    else:
        fig.update_yaxes(title_text="Percent", range=[0, 100], ticksuffix="%")

    fig.update_xaxes(title_text="Module")
    fig.update_layout(title=title, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h"), hovermode="x unified")
    return fig

def chart_echo_combo(
    module_table: pd.DataFrame,
    students_total: int | None = None,
    barmode: str = "stack",
    title: str = "Echo Data",
    autoscale: bool = True,
) -> go.Figure:
    if module_table is None or module_table.empty:
        return go.Figure()

    df = module_table.copy()
    x = df["Module"].astype(str).tolist()

    viewers_col = "# of Students Viewing" if "# of Students Viewing" in df else "# of Unique Viewers"
    raw_viewers = pd.to_numeric(df.get(viewers_col, pd.Series([0]*len(df))), errors="coerce").fillna(0)

    if students_total and students_total > 0:
        viewed = raw_viewers.clip(lower=0, upper=students_total).round(0).astype(int).tolist()
        not_viewed = (students_total - pd.Series(viewed)).clip(lower=0).astype(int).tolist()
    else:
        # fallback if total unknown
        total_guess = pd.to_numeric(df.get("# of Students", pd.Series([0]*len(df))), errors="coerce").fillna(0)
        viewed = raw_viewers.round(0).astype(int).tolist()
        not_viewed = (total_guess - pd.Series(viewed)).clip(lower=0).astype(int).tolist()

    avg_view = _pct(df.get("Average View %", pd.Series([np.nan]*len(df))))
    overall_view = _pct(df.get("Overall View %", pd.Series([np.nan]*len(df))))

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=viewed, name="# of Unique Viewers",
                         hovertemplate="%{y:,}<extra># of Unique Viewers</extra>", offsetgroup=0))
    fig.add_trace(go.Bar(x=x, y=not_viewed, name="Not Viewed",
                         hovertemplate="%{y:,}<extra>Not Viewed</extra>", offsetgroup=0))

    if any(pd.notna(avg_view)):
        fig.add_trace(go.Scatter(x=x, y=avg_view, mode="lines+markers", name="Avg View %",
                                 yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg View %</extra>"))
    if any(pd.notna(overall_view)):
        fig.add_trace(go.Scatter(x=x, y=overall_view, mode="lines+markers", name="Avg Overall View %",
                                 yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg Overall View %</extra>"))

    # Autoscale left axis (students) and right axis (percent) by default
    if autoscale:
        yaxis = dict(title="Students", autorange=True, rangemode="tozero")
        yaxis2 = dict(title="Percent", autorange=True, rangemode="tozero", ticksuffix="%")
    else:
        # legacy fixed ranges if you want them
        yaxis = dict(title="Students", rangemode="tozero", autorange=False)
        yaxis2 = dict(title="Percent", range=[0, 100], ticksuffix="%")

    fig.update_layout(
        title=title,
        barmode="stack",
        yaxis=yaxis,
        yaxis2=yaxis2,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h"),
        hovermode="x unified",
    )

    # optional dotted line at total
    if students_total and not autoscale:
        try:
            fig.add_hline(y=students_total, line_dash="dot", line_width=1)
        except Exception:
            fig.add_shape(type="line", x0=-0.5, x1=len(x)-0.5, y0=students_total, y1=students_total)

    fig.update_xaxes(title_text="Module")
    return fig
