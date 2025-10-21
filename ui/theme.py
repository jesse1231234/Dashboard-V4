# ui/theme.py
from __future__ import annotations
import streamlit as st

def apply_theme(
    *,
    brand="#3B82F6",          # primary accent (indigo-500)
    radius="12px",            # global corner radius
    card_shadow="0 6px 18px rgba(0,0,0,.06)",
    compact_tables=True,      # slightly denser tables
):
    """Injects CSS to give the app a modern, polished look (no functional changes)."""
    base = st.get_option("theme.base") or "light"
    is_dark = (base == "dark")

    # Google Font (Inter) + CSS variables
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

      :root {{
        --brand: {brand};
        --radius: {radius};
        --card-shadow: {card_shadow};
      }}

      html, body, [class*="css"] {{
        font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }}

      /* Page + container spacing */
      section.main > div.block-container {{
        padding-top: 1.2rem;
        padding-bottom: 2rem;
      }}

      /* Headings */
      h1, h2, h3 {{
        letter-spacing: .2px;
      }}

      /* Buttons */
      .stButton > button {{
        border-radius: var(--radius);
        padding: 0.55rem 0.9rem;
        font-weight: 600;
        border: 1px solid rgba(0,0,0,.06);
        box-shadow: 0 2px 6px rgba(0,0,0,.05);
      }}
      .stButton > button:hover {{
        transform: translateY(-1px);
        transition: all .15s ease;
        box-shadow: 0 6px 14px rgba(0,0,0,.08);
      }}

      /* Primary button style for common actions */
      .stButton > button[kind="primary"] {{
        background: var(--brand) !important;
        color: white !important;
        border: none !important;
      }}

      /* Metrics as cards */
      div[data-testid="stMetric"]{{
        background: {"#0f172a" if is_dark else "white"};
        border: 1px solid {"rgba(255,255,255,.08)" if is_dark else "rgba(0,0,0,.06)"};
        border-radius: var(--radius);
        padding: 14px 16px;
        box-shadow: var(--card-shadow);
      }}
      div[data-testid="stMetric"] label {{ opacity: .75; font-size: .9rem; }}
      div[data-testid="stMetric"] [data-testid="stMetricValue"]{{ font-weight: 700; }}

      /* Tabs as pills */
      div[role="tablist"] {{
        gap: 8px;
      }}
      button[role="tab"] {{
        border-radius: 999px !important;
        padding: 6px 14px !important;
        border: 1px solid {"rgba(255,255,255,.12)" if is_dark else "rgba(0,0,0,.08)"} !important;
        background: {"#0b1220" if is_dark else "#fff"} !important;
      }}
      button[aria-selected="true"][role="tab"] {{
        color: {"#111827" if is_dark else "white"} !important;
        background: var(--brand) !important;
        border-color: var(--brand) !important;
      }}

      /* DataFrames */
      [data-testid="stDataFrame"] thead tr th {{
        border-bottom: 1px solid {"rgba(255,255,255,.12)" if is_dark else "rgba(0,0,0,.08)"} !important;
        font-weight: 600;
      }}
      [data-testid="stDataFrame"] tbody tr:hover td {{
        background: {"rgba(255,255,255,.03)" if is_dark else "rgba(0,0,0,.02)"} !important;
      }}
      {"[data-testid='stDataFrame'] .row_heading, [data-testid='stDataFrame'] .blank {display: none}" if compact_tables else ""}

      /* Legend at top (we already moved it in your chart code; this ensures spacing) */
      .legendtop {{ margin-bottom: 6px; }}

      /* Subtle section dividers */
      .stDivider {{ opacity: .8; }}
    </style>
    """, unsafe_allow_html=True)

def hero(title: str, subtitle: str | None = None, emoji: str = "📊"):
    """A simple header block you can use atop the dashboard."""
    st.markdown(f"""
    <div style="
      background: linear-gradient(135deg, rgba(59,130,246,.12), rgba(59,130,246,.03));
      border: 1px solid rgba(59,130,246,.18);
      border-radius: var(--radius);
      padding: 18px 18px 16px 18px;
      box-shadow: var(--card-shadow);
      margin-bottom: 12px;
    ">
      <div style="font-size:20px;font-weight:700;margin-bottom:4px;">{emoji} {title}</div>
      {"<div style='opacity:.8'>" + subtitle + "</div>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)
