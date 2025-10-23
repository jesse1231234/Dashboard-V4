# ui/theme.py
from __future__ import annotations
import streamlit as st

def apply_theme(
    *,
    brand="#3B82F6",          # primary accent (indigo-500)
    radius="12px",            # global corner radius
    card_shadow="0 20px 45px rgba(15,23,42,.18)",
    compact_tables=True,      # slightly denser tables
):
    """Inject CSS for a cohesive, modern visual style."""
    base = st.get_option("theme.base") or "light"
    is_dark = base == "dark"

    surface_bg = "#111827" if is_dark else "#ffffff"
    subtle_bg = "rgba(148,163,184,.18)" if is_dark else "rgba(148,163,184,.12)"
    border_color = "rgba(255,255,255,.14)" if is_dark else "rgba(15,23,42,.08)"
    muted_color = "rgba(226,232,240,.85)" if is_dark else "rgba(71,85,105,.85)"
    if is_dark:
        gradient_layers = (
            "radial-gradient(circle at 20% -10%, rgba(59,130,246,.45), transparent 55%),",
            " radial-gradient(circle at 80% -20%, rgba(14,165,233,.4), transparent 60%),",
            " linear-gradient(180deg, #0f172a 0%, #111827 100%)",
        )
    else:
        gradient_layers = (
            "radial-gradient(circle at 20% -10%, rgba(79,70,229,.12), transparent 55%),",
            " radial-gradient(circle at 80% -20%, rgba(14,165,233,.12), transparent 60%),",
            " linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
        )
    page_gradient = "".join(gradient_layers)

    input_bg = "rgba(15,23,42,.55)" if is_dark else "rgba(255,255,255,.9)"
    input_focus = "rgba(59,130,246,.45)" if is_dark else "rgba(59,130,246,.25)"

    # Google Font (Inter) + CSS variables
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      :root {{
        --brand: {brand};
        --radius: {radius};
        --card-shadow: {card_shadow};
      }}

      html, body, [class*="css"] {{
        font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background: {page_gradient};
      }}

      section.main > div.block-container {{
        padding: 2.4rem 2.8rem 3.4rem;
        max-width: 1200px;
        margin: 0 auto;
      }}

      h1, h2, h3 {{
        letter-spacing: .2px;
      }}

      h1 {{ font-size: clamp(1.7rem, 2.8vw, 2.4rem); }}

      /* Sidebar */
      section[data-testid="stSidebar"] > div {{
        background: {surface_bg};
        border-right: 1px solid {border_color};
        box-shadow: inset -1px 0 0 rgba(15,23,42,.25);
      }}

      section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {{
        color: {muted_color};
      }}

      /* Buttons */
      .stButton > button {{
        border-radius: var(--radius);
        padding: 0.6rem 1.05rem;
        font-weight: 600;
        border: 1px solid {border_color};
        background: {surface_bg};
        color: inherit;
        transition: all .18s ease;
        box-shadow: 0 10px 25px rgba(15,23,42,.08);
      }}
      .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 18px 35px rgba(15,23,42,.16);
      }}
      .stButton > button:focus {{ outline: none; box-shadow: 0 0 0 3px {input_focus}; }}

      .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, var(--brand), #6366f1) !important;
        color: white !important;
        border: none !important;
      }}

      /* Inputs */
      .stTextInput > div > div > input,
      .stTextArea textarea,
      .stNumberInput > div > div > input,
      .stSelectbox > div > div > select {{
        border-radius: var(--radius);
        border: 1px solid {border_color};
        background: {input_bg};
        color: inherit;
        padding: 0.55rem 0.75rem;
        transition: border .18s ease, box-shadow .18s ease;
      }}
      .stTextInput > div > div > input:focus,
      .stTextArea textarea:focus,
      .stNumberInput > div > div > input:focus,
      .stSelectbox > div > div > select:focus {{
        border-color: var(--brand);
        box-shadow: 0 0 0 3px {input_focus};
      }}

      label {{ font-weight: 500; color: {muted_color}; }}

      .stFileUploader > div {{
        border-radius: calc(var(--radius) + 4px);
        background: {surface_bg};
        border: 1px dashed {border_color};
      }}

      /* Metrics as cards */
      div[data-testid="stMetric"]{{
        background: {surface_bg};
        border: 1px solid {border_color};
        border-radius: var(--radius);
        padding: 14px 16px;
        box-shadow: var(--card-shadow);
      }}
      div[data-testid="stMetric"] label {{ opacity: .75; font-size: .9rem; }}
      div[data-testid="stMetric"] [data-testid="stMetricValue"]{{ font-weight: 700; }}

      /* Tabs as pills */
      div[role="tablist"] {{
        gap: 8px;
        margin-bottom: 0.75rem;
      }}
      button[role="tab"] {{
        border-radius: 999px !important;
        padding: 6px 14px !important;
        border: 1px solid {border_color} !important;
        background: {surface_bg} !important;
        color: inherit !important;
        box-shadow: inset 0 -1px 0 rgba(15,23,42,.08);
      }}
      button[aria-selected="true"][role="tab"] {{
        color: {"#111827" if is_dark else "white"} !important;
        background: linear-gradient(135deg, var(--brand), #6366f1) !important;
        border-color: transparent !important;
        box-shadow: 0 12px 20px rgba(99,102,241,.22);
      }}

      /* DataFrames */
      [data-testid="stDataFrame"] thead tr th {{
        border-bottom: 1px solid {border_color} !important;
        font-weight: 600;
      }}
      [data-testid="stDataFrame"] tbody tr:hover td {{
        background: {subtle_bg} !important;
      }}
      {"[data-testid='stDataFrame'] .row_heading, [data-testid='stDataFrame'] .blank {display: none}" if compact_tables else ""}

      /* Custom surfaces */
      .surface {{
        background: {surface_bg};
        border-radius: calc(var(--radius) + 2px);
        border: 1px solid {border_color};
        box-shadow: var(--card-shadow);
        padding: 1.6rem 1.4rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(12px);
      }}

      .callout {{
        border-radius: calc(var(--radius) + 2px);
        border: 1px solid {border_color};
        background: {subtle_bg};
        padding: 0.95rem 1.1rem;
        display: flex;
        gap: 0.85rem;
        align-items: flex-start;
        color: inherit;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
      }}
      .callout__icon {{
        font-size: 1.25rem;
        line-height: 1.6rem;
      }}
      .callout__body {{
        opacity: .85;
      }}

      .step-header {{
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.2rem 1.4rem;
        border-radius: calc(var(--radius) + 4px);
        background: {surface_bg};
        border: 1px solid {border_color};
        box-shadow: var(--card-shadow);
        margin-bottom: 1.2rem;
      }}
      .step-header__badge {{
        width: 36px;
        height: 36px;
        border-radius: 999px;
        display: grid;
        place-items: center;
        font-weight: 600;
        background: linear-gradient(135deg, var(--brand), #6366f1);
        color: white;
      }}
      .step-header__title {{
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 0.15rem;
      }}
      .step-header__subtitle {{
        color: {muted_color};
        font-size: .92rem;
      }}

      .legendtop {{ margin-bottom: 6px; }}

      .stDownloadButton button {{
        border-radius: var(--radius);
        border: 1px solid {border_color};
        background: {surface_bg};
        padding: 0.55rem 0.9rem;
        transition: all .18s ease;
      }}
      .stDownloadButton button:hover {{
        border-color: var(--brand);
        box-shadow: 0 10px 25px rgba(59,130,246,.15);
      }}

      .stAlert {{
        border-radius: calc(var(--radius) + 2px);
      }}

      .stDivider {{ opacity: .85; margin: 2rem 0; }}
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
