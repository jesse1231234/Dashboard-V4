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


def chart_gradebook_combo(df: pd.DataFrame, title: str = "Canvas Data") -> go.Figure:
    """
    Two straight lines on a single 0–100% y-axis:
      - Avg % Turned In
      - Avg Average Excluding Zeros
    """
    if df is None or df.empty:
        return go.Figure()

    x = df["Module"].astype(str).tolist()
    y_turnedin = _pct(df["Avg % Turned In"])
    y_excl0 = _pct(df["Avg Average Excluding Zeros"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y_turnedin, mode="lines+markers",
        name="% Turned In", hovertemplate="%{y:.1f}%<extra>% Turned In</extra>"
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y_excl0, mode="lines+markers",
        name="Avg Excl Zeros", hovertemplate="%{y:.1f}%<extra>Avg Excl Zeros</extra>"
    ))

    fig.update_yaxes(title_text="Percent", autorange=True, rangemode="tozero", ticksuffix="%")
    fig.update_xaxes(title_text="Module")
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=70, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0.0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    return fig


def chart_echo_combo(
    module_table: pd.DataFrame,
    students_total: int | None = None,
    barmode: str = "stack",
    title: str = "Echo Data",
) -> go.Figure:
    """
    Bars represent the TOTAL # of students per module (constant height),
    with the 'Viewed' portion filling up to '# of Unique Viewers' and the
    remainder as 'Not Viewed'. Lines (secondary axis) show percent series.
    """
    if module_table is None or module_table.empty:
        return go.Figure()

    df = module_table.copy()
    x = df["Module"].astype(str).tolist()

    # Use "# of Students Viewing" from the module table (now the average-of-unique-viewers),
    # clamp to [0, students_total], and compute the complementary "Not Viewed".
    viewers_col = "# of Students Viewing" if "# of Students Viewing" in df else "# of Unique Viewers"
    raw_viewers = pd.to_numeric(df.get(viewers_col, pd.Series([0]*len(df))), errors="coerce").fillna(0)

    if students_total is not None and students_total > 0:
        viewed = raw_viewers.clip(lower=0, upper=students_total).round(0).astype(int).tolist()
        not_viewed = (students_total - pd.Series(viewed)).clip(lower=0).astype(int).tolist()
        total_bars = [students_total] * len(x)
        y_left_max = students_total
    else:
        # Fallback: if we don't know the total, show what we have and derive a pseudo-total.
        n_students_series = pd.to_numeric(df.get("# of Students", pd.Series([0]*len(df))), errors="coerce").fillna(0)
        # If absent, infer per-module total as max(viewers, '# of Students')
        total_bars = np.maximum(raw_viewers, n_students_series).round(0).astype(int).tolist()
        viewed = raw_viewers.round(0).astype(int).tolist()
        not_viewed = (pd.Series(total_bars) - pd.Series(viewed)).clip(lower=0).astype(int).tolist()
        y_left_max = max(total_bars) if total_bars else 0

    # Percent lines (0..1 -> 0..100)
    avg_view = _pct(df.get("Average View %", pd.Series([np.nan]*len(df))))
    overall_view = _pct(df.get("Overall View %", pd.Series([np.nan]*len(df))))

    # Headroom so bars/labels never get clipped
    headroom = max(5, int(round(y_left_max * 0.12)))
    y_max = y_left_max + headroom

    fig = go.Figure()

    # Stacked bars: Viewed + Not Viewed = Total
    fig.add_trace(
        go.Bar(
            x=x, y=viewed, name="# of Unique Viewers",
            hovertemplate="%{y:,}<extra># of Unique Viewers</extra>", offsetgroup=0
        )
    )
    fig.add_trace(
        go.Bar(
            x=x, y=not_viewed, name="Not Viewed",
            hovertemplate="%{y:,}<extra>Not Viewed</extra>", offsetgroup=0
        )
    )

    # Lines on secondary axis
    if any(pd.notna(avg_view)):
        fig.add_trace(
            go.Scatter(
                x=x, y=avg_view, mode="lines+markers", name="Avg View %",
                yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg View %</extra>"
            )
        )
    if any(pd.notna(overall_view)):
        fig.add_trace(
            go.Scatter(
                x=x, y=overall_view, mode="lines+markers", name="Avg Overall View %",
                yaxis="y2", hovertemplate="%{y:.1f}%<extra>Avg Overall View %</extra>"
            )
        )

    yaxis_config = dict(title="Students", rangemode="tozero")
    if y_max:
        yaxis_config.update(range=[0, y_max], autorange=False)
    else:
        yaxis_config.update(autorange=True)

    fig.update_layout(
        title=title,                  # keep your existing title var
        barmode=barmode,
        yaxis=yaxis_config,
        yaxis2=dict(
            title="Percent",
            overlaying="y",           # <-- important, keeps lines on a right-hand axis
            side="right",
            autorange=True,
            rangemode="tozero",
            ticksuffix="%",
        ),
        margin=dict(l=10, r=10, t=70, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0.0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )


    # Optional dotted line at total (visual anchor)
    if students_total:
        try:
            fig.add_hline(y=students_total, line_dash="dot", line_width=1)
        except Exception:
            fig.add_shape(type="line", x0=-0.5, x1=len(x)-0.5, y0=students_total, y1=students_total)

    fig.update_xaxes(title_text="Module")
    return fig
