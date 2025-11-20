# ai/analysis.py
from __future__ import annotations
from typing import Optional
import os
import pandas as pd
import streamlit as st
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

def _get_ai_client() -> OpenAI:
    """
    Create an OpenAI client for an Azure AI Foundry / Project endpoint.

    Expected secrets/env:
      - OPENAI_BASE_URL  e.g. "https://<something>.services.ai.azure.com/openai/v1"
      - OPENAI_API_KEY   the key from the Foundry 'Use model' / 'Connections' blade
    """
    base_url = (
        st.secrets.get("OPENAI_BASE_URL", None)
        or os.getenv("OPENAI_BASE_URL")
    )
    api_key = (
        st.secrets.get("OPENAI_API_KEY", None)
        or os.getenv("OPENAI_API_KEY")
    )

    if not base_url or not api_key:
        raise RuntimeError(
            "OpenAI config missing. "
            "Set OPENAI_BASE_URL and OPENAI_API_KEY in Streamlit secrets or env."
        )

    # Foundry guidance: use OpenAI client with base_url pointing at the
    # Azure AI / OpenAI endpoint that already includes '/openai/v1'. :contentReference[oaicite:1]{index=1}
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


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
    
    # build payload above as you already do...

        # Build the payload (kpis + dataframes) above as you are already doing...

    client = _get_ai_client()

        # Model ID to pass to the Foundry/OpenAI endpoint.
        # You can override via the `model` argument, but we also support a secret.
            model_name = (
            st.secrets.get("OPENAI_MODEL", None)
            or os.getenv("OPENAI_MODEL")
            or model  # fallback to the function arg default
        )

        try:
            resp = client.chat.completions.create(
                model=model_name,   # e.g. "gpt-4.1-mini", "grok-3", etc.
                temperature=temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
            )
        except Exception as e:
            # Nice clean error that surfaces the model name, but not internals
            raise RuntimeError(
                f"OpenAI/Foundry call failed for model '{model_name}': {e}"
            )

        return (resp.choices[0].message.content or "").strip()
