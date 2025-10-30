# ai/analysis.py
from __future__ import annotations
from typing import Optional
import os
import pandas as pd
from openai import OpenAI

SYSTEM_PROMPT = """You are an academic learning analytics assistant.
Write a concise, plain-English analysis for instructors teaching online asychronous courses.
Rules:
- Be specific: cite modules and metrics with percentages/counts.
- Call out trends and outliers.
- Focus on descriptions of the data.
- Do not make teaching recommendations. Only report on the data.
- Keep it under ~500 words unless asked for more.
"""

def _df_to_markdown(df: Optional[pd.DataFrame], max_rows: int = 30) -> str:
    if df is None or df.empty:
        return "(empty)"
    df2 = df.copy().head(max_rows)
    # round percentage-like columns if any are numeric fractions
    for c in df2.columns:
        if df2[c].dtype.kind in "fc":
            # if it looks like a fraction, render as %
            if df2[c].between(0, 1, inclusive="both").mean() > 0.6:
                df2[c] = (df2[c] * 100).round(1).astype(str) + "%"
    return df2.to_markdown(index=False)

def generate_analysis(
    kpis: dict,
    echo_module_df: Optional[pd.DataFrame],
    gradebook_module_df: Optional[pd.DataFrame],
    gradebook_summary_df: Optional[pd.DataFrame],
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
) -> str:
    # Build a compact, de-identified payload
    kpi_lines = []
    for k, v in (kpis or {}).items():
        if v is None: continue
        if isinstance(v, float) and 0 <= v <= 1:
            kpi_lines.append(f"- {k}: {v*100:.1f}%")
        else:
            kpi_lines.append(f"- {k}: {v}")

    payload = f"""
Data for analysis (de-identified):

# KPIs
{os.linesep.join(kpi_lines) if kpi_lines else "(none)"}

# Echo Module Metrics (per-module)
{_df_to_markdown(echo_module_df)}

# Gradebook Summary Rows
{_df_to_markdown(gradebook_summary_df)}

# Gradebook Module Metrics (per-module)
{_df_to_markdown(gradebook_module_df)}

Instructions:
- Be specific: cite modules and metrics with percentages/counts.
- Call out trends and outliers.
- Focus on descriptions of the data.
- identify general trends and data points worthy of further investigation.
- No need to list each section of the course individually. Simply call out aspects of the data that seem important for further investigation.
"""
    client = OpenAI()  # uses OPENAI_API_KEY from env or st.secrets (see app.py)
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": payload},
        ],
    )
    return resp.choices[0].message.content.strip()
