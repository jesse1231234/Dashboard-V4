import io
from typing import Optional

import pandas as pd
import streamlit as st

from services.canvas import CanvasService
from processors.echo_adapter import build_echo_tables
from processors.grades_adapter import build_gradebook_tables
from ui.charts import chart_gradebook_combo, chart_echo_combo
from ui.kpis import compute_kpis
from ai.analysis import generate_analysis
import os

st.set_page_config(page_title="Canvas/Echo Dashboard", layout="wide")

st.markdown("""
<style>
/* Global tweaks */
html, body, [class*="css"] { -webkit-font-smoothing: antialiased; }

/* Page padding/width */
section.main > div { padding-top: .5rem; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }

/* Headings */
h1, h2, h3 { letter-spacing: .2px; }

/* KPI cards (style st.metric) */
div[data-testid="stMetric"]{
  background: var(--secondary-background-color, rgba(0,0,0,0.03));
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
div[data-testid="stMetric"] label { opacity: .75; font-size: .9rem; }
div[data-testid="stMetric"] [data-testid="stMetricValue"]{ font-weight: 700; }

/* Tabs */
div[role="tablist"] { gap: 6px; }
button[role="tab"]{
  border-radius: 999px !important;
  padding: 6px 14px !important;
}

/* DataFrames: cleaner header line */
[data-testid="stDataFrame"] thead tr th {
  border-bottom: 1px solid rgba(0,0,0,0.08) !important;
}
</style>
""", unsafe_allow_html=True)

NOTICE = "No identifying information will be present in this analysis. All data will be de-identified."
DEFAULT_BASE_URL = st.secrets.get("CANVAS_BASE_URL", "https://colostate.instructure.com")
TOKEN = st.secrets.get("CANVAS_TOKEN", "")

# ---------------- Caching helpers ----------------
@st.cache_resource(show_spinner=False)
def get_canvas_service(base_url: str, token: str) -> CanvasService:
    return CanvasService(base_url, token)

@st.cache_resource(show_spinner=True)
def fetch_canvas_order_df(base_url: str, token: str, course_id: str) -> pd.DataFrame:
    svc = get_canvas_service(base_url, token)
    return svc.build_order_df(int(course_id))

@st.cache_resource(show_spinner=False)
def fetch_student_count(base_url: str, token: str, course_id: str) -> Optional[int]:
    svc = get_canvas_service(base_url, token)
    return svc.get_student_count(int(course_id))

@st.cache_data(show_spinner=True)
def run_echo_tables(file_bytes: bytes, canvas_df: pd.DataFrame, students_total: Optional[int]):
    return build_echo_tables(io.BytesIO(file_bytes), canvas_df, class_total_students=students_total)


@st.cache_data(show_spinner=True)
def run_gradebook_tables(file_bytes: bytes, canvas_df: pd.DataFrame):
    return build_gradebook_tables(io.BytesIO(file_bytes), canvas_df)

def sort_by_canvas_order(df: pd.DataFrame, module_col: str, canvas_df: pd.DataFrame) -> pd.DataFrame:
    """Sort a dataframe by Canvas module order using module_position; tolerate duplicate names."""
    if (
        df is None or df.empty or
        canvas_df is None or canvas_df.empty or
        module_col not in df.columns
    ):
        return df

    # Build ordered list of module names (keep first occurrence only)
    order = (
        canvas_df[["module", "module_position"]]
        .dropna(subset=["module"])
        .sort_values(["module_position", "module"], kind="stable")
    )
    # Deduplicate module names while preserving order
    categories = pd.unique(order["module"].astype(str))

    if len(categories) == 0:
        return df

    out = df.copy()
    out[module_col] = out[module_col].astype(str)
    out[module_col] = pd.Categorical(out[module_col], categories=categories, ordered=True)
    out = out.sort_values(module_col).reset_index(drop=True)
    # Return as string for downstream display
    out[module_col] = out[module_col].astype(str)
    return out

# --- Table display helper (place at top level, not inside another function) ---
def _percentize_for_display(df: pd.DataFrame, percent_cols: list[str], decimals: int = 1):
    """
    Return (copy_of_df_with_selected_cols*100) and a Streamlit column_config for % formatting.
    """
    disp = df.copy()
    for col in percent_cols:
        if col in disp.columns:
            disp[col] = pd.to_numeric(disp[col], errors="coerce") * 100.0
    cfg = {
        col: st.column_config.NumberColumn(col, format=f"%.{decimals}f%%")
        for col in percent_cols if col in disp.columns
    }
    return disp, cfg

# ---------------- Wizard UI ----------------
st.session_state.setdefault("step", 1)

with st.sidebar:
    st.markdown("### Controls")
    if st.button("Restart wizard"):
        for k in ["canvas", "echo", "grades", "results", "base_url", "course_id", "student_count"]:
            st.session_state.pop(k, None)
        st.session_state.step = 1
        st.rerun()

if st.session_state.step == 1:
    st.header("Step 1 — Canvas Course Number")
    st.info(NOTICE)
    base_url = st.text_input("Canvas Base URL", value=DEFAULT_BASE_URL)
    course_id = st.text_input("Please provide the Canvas Course Number contained in the URL for the Canvas Course you are analyzing. For example, if the URL for your home page is 'https://colostate.instructure.com/courses/123456', then 123456 is your Canvas Course Number")
    if not TOKEN:
        st.warning("Missing CANVAS_TOKEN in Streamlit secrets. Add it before continuing.")
    if st.button("Continue") and base_url and course_id and TOKEN:
        try:
            with st.spinner("Fetching Canvas module order..."):
                canvas_df = fetch_canvas_order_df(base_url, TOKEN, course_id)
                st.session_state["canvas"] = canvas_df
                st.session_state["base_url"] = base_url
                st.session_state["course_id"] = course_id
                st.session_state["student_count"] = fetch_student_count(base_url, TOKEN, course_id)  # may be None
                st.session_state.step = 2
                st.rerun()
        except Exception as e:
            st.error(f"Canvas error: {e}")

elif st.session_state.step == 2:
    st.header("Step 2 — Echo CSV")
    st.info(NOTICE)
    echo_csv = st.file_uploader("Please provide the CSV file containing your course's Echo data.", type=["csv"])
    if echo_csv and st.button("Continue"):
        try:
            with st.spinner("Processing Echo data..."):
                st.session_state["echo"] = run_echo_tables(
                    echo_csv.getvalue(),
                    st.session_state["canvas"],
                    st.session_state.get("student_count"),
                )

                st.session_state.step = 3
                st.rerun()
        except Exception as e:
            st.error(f"Echo processing error: {e}")

elif st.session_state.step == 3:
    st.header("Step 3 — Gradebook CSV")
    st.info(NOTICE)
    gb_csv = st.file_uploader("Please provide the CSV file containing your gradebook data.", type=["csv"])
    if gb_csv and st.button("Process & View Dashboard"):
        try:
            with st.spinner("Processing gradebook data..."):
                st.session_state["grades"] = run_gradebook_tables(gb_csv.getvalue(), st.session_state["canvas"])
                st.session_state["results"] = True
                st.rerun()
        except Exception as e:
            st.error(f"Gradebook processing error: {e}")
            
# ---------------- Dashboard ----------------
if st.session_state.get("results"):
    echo_tables = st.session_state["echo"]
    gb_tables = st.session_state["grades"]
    canvas_df = st.session_state["canvas"]

    # Order by Canvas module order
    if hasattr(gb_tables, "module_assignment_metrics_df") and not gb_tables.module_assignment_metrics_df.empty:
        gb_tables.module_assignment_metrics_df = sort_by_canvas_order(
            gb_tables.module_assignment_metrics_df, "Module", canvas_df
        )
    if hasattr(echo_tables, "module_table") and not echo_tables.module_table.empty:
        echo_tables.module_table = sort_by_canvas_order(
            echo_tables.module_table, "Module", canvas_df
        )

    # KPIs (prefer Canvas student count when available)
    kpis = compute_kpis(
        echo_tables,
        gb_tables,
        students_from_canvas=st.session_state.get("student_count"),
    )
    
    # --- NEW: Constant "# of Students" across modules for the Echo chart ---
    students_total = (
        kpis.get("# Students")
        or st.session_state.get("student_count")
        or (len(gb_tables.gradebook_df.index) if getattr(gb_tables, "gradebook_df", None) is not None else None)
    )

    if students_total and hasattr(echo_tables, "module_table") and not echo_tables.module_table.empty:
        echo_tables.module_table = echo_tables.module_table.copy()
        echo_tables.module_table["# of Students"] = int(students_total)


    # KPI header
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("# Students", f"{kpis.get('# Students', 0):,}")
    avg_grade = kpis.get("Average Grade")
    c2.metric("Average Grade", f"{avg_grade:.1f}%" if avg_grade is not None else "—")
    c3.metric("Median Letter Grade", kpis.get("Median Letter Grade", "—"))
    avg_echo = kpis.get("Average Echo360 engagement")
    c4.metric("Avg Echo Engagement", f"{avg_echo:.1f}%" if avg_echo is not None else "—")
    c5.metric("# of Fs", f"{kpis.get('# of Fs', 0):,}")
    avg_assign = kpis.get("Avg Assignment Grade (class)")
    c6.metric("Avg Assignment Grade", f"{avg_assign*100:.1f}%" if avg_assign is not None else "—")

    tab1, tab2, tab3, tab4 = st.tabs(["Tables", "Charts", "Exports", "AI Analysis"])

    with tab1:
        st.subheader("Echo Summary (per media)")
        es_disp, es_cfg = _percentize_for_display(
            echo_tables.echo_summary,
            ["Average View %", "% of Students Viewing", "% of Video Viewed Overall"]
        )
        st.dataframe(es_disp, use_container_width=True, column_config=es_cfg)


        st.subheader("Echo Module Table")
        em_disp, em_cfg = _percentize_for_display(
            echo_tables.module_table,
            ["Average View %", "Overall View %"]
        )
        st.dataframe(em_disp, use_container_width=True, column_config=em_cfg)


        st.subheader("Gradebook Summary Rows")
        gb_sum_disp = gb_tables.gradebook_summary_df.copy()
        # all columns are fractions → scale to %
        gb_sum_disp = gb_sum_disp.apply(pd.to_numeric, errors="coerce") * 100.0
        gb_sum_cfg = {
            col: st.column_config.NumberColumn(col, format="%.1f%%")
            for col in gb_sum_disp.columns
        }
        st.dataframe(gb_sum_disp, use_container_width=True, column_config=gb_sum_cfg)


        st.subheader("Gradebook Module Metrics")
        gm_disp, gm_cfg = _percentize_for_display(
            gb_tables.module_assignment_metrics_df,
            ["Avg % Turned In", "Avg Average Excluding Zeros"]
        )
        st.dataframe(gm_disp, use_container_width=True, column_config=gm_cfg)

    with tab2:
        if not gb_tables.module_assignment_metrics_df.empty:
            st.plotly_chart(chart_gradebook_combo(gb_tables.module_assignment_metrics_df, title="Canvas Data"), use_container_width=True)
        else:
            st.info("No module-level gradebook metrics to plot.")

        if not echo_tables.module_table.empty:
            st.plotly_chart(
                chart_echo_combo(echo_tables.module_table, students_total=students_total, title="Echo Data"),
                use_container_width=True
            )

        else:
            st.info("No module-level Echo metrics to plot.")

    with tab3:
        def to_csv_bytes(df: pd.DataFrame) -> bytes:
            return df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Echo Summary CSV",
            to_csv_bytes(echo_tables.echo_summary),
            file_name="echo_summary.csv",
        )
        st.download_button(
            "Download Echo Module Table CSV",
            to_csv_bytes(echo_tables.module_table),
            file_name="echo_module_table.csv",
        )
        st.download_button(
            "Download Gradebook Summary CSV",
            gb_tables.gradebook_summary_df.to_csv().encode("utf-8"),
            file_name="gradebook_summary.csv",
        )
        st.download_button(
            "Download Gradebook Module Metrics CSV",
            to_csv_bytes(gb_tables.module_assignment_metrics_df),
            file_name="gradebook_module_metrics.csv",
        )

    with tab4:
        st.subheader("AI Analysis")
        st.caption("No identifying information will be present in this analysis. All data will be de-identified.")

        # Model + settings
        colA, colB = st.columns([2,1])
        with colA:
            model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"], index=0)
        with colB:
            temperature = st.slider("Creativity", 0.0, 1.0, 0.3, 0.1)

        # Confirm key present (use st.secrets or env)
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        if not openai_key:
            st.warning("Add OPENAI_API_KEY to Streamlit secrets to enable AI analysis.")
        else:
            # Button to generate
            if st.button("Generate analysis"):
                with st.spinner("Analyzing your dashboard data..."):
                    try:
                        text = generate_analysis(
                            kpis=kpis,
                            echo_module_df=echo_tables.module_table if echo_tables else None,
                            gradebook_module_df=gb_tables.module_assignment_metrics_df if gb_tables else None,
                            gradebook_summary_df=gb_tables.gradebook_summary_df if gb_tables else None,
                            model=model,
                            temperature=temperature,
                        )
                        st.markdown(text)
                    except Exception as e:
                        st.error(f"AI analysis failed: {e}")



