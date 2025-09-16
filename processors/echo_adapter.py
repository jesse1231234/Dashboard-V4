# processors/echo_adapter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

import numpy as np
import pandas as pd


@dataclass
class EchoTables:
    """Outputs consumed by the Streamlit app."""
    echo_summary: pd.DataFrame            # per-media summary (+ optional overall columns)
    module_table: pd.DataFrame            # per-module aggregation (ordered by Canvas)
    student_table: pd.DataFrame           # de-identified per-student engagement


# Column name candidates (case-insensitive, fuzzy 'contains' fallback)
CANDIDATES = {
    "media":     ["media name", "media title", "video title", "title", "name"],
    "duration":  ["duration", "video duration", "media duration", "length"],
    "viewtime":  ["total view time", "total viewtime", "total watch time", "view time"],
    "avgview":   ["average view time", "avg view time", "avg watch time", "average watch time"],
    "user":      ["user email", "user name", "email", "user", "viewer", "username"],
}


# ---------- helpers ----------

def _find_col(df: pd.DataFrame, want: Iterable[str], required: bool = True) -> Optional[str]:
    """
    Return a matching column name (case-insensitive) using exact-lower match,
    then 'contains' fallback. Raise if required and not found.
    """
    low = {c.lower(): c for c in df.columns}
    for w in want:
        if w in low:
            return low[w]
    for k, v in low.items():
        if any(w in k for w in want):
            return v
    if required:
        raise KeyError(f"Missing required column; need one of: {list(want)}")
    return None


def _to_seconds(x) -> float:
    """Parse durations like 01:23:45, 12:34, or numeric seconds into float seconds."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return np.nan
    # numeric-as-string
    try:
        return float(s)
    except Exception:
        pass
    # hh:mm[:ss]
    parts = s.split(":")
    try:
        parts = [float(p) for p in parts]
    except Exception:
        return np.nan
    if len(parts) == 3:
        h, m, sec = parts
        return h * 3600 + m * 60 + sec
    if len(parts) == 2:
        m, sec = parts
        return m * 60 + sec
    return np.nan


def _norm_text(text: str) -> str:
    """Normalize titles for deterministic joins (lowercase, strip punctuation/extra spaces)."""
    s = "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in str(text))
    return " ".join(s.split())


def _norm_series(s: pd.Series) -> pd.Series:
    return s.fillna("").map(_norm_text)


# ---------- main builder ----------

def build_echo_tables(echo_csv_file, canvas_order_df: pd.DataFrame) -> EchoTables:
    """
    Read the Echo CSV and return DataFrames for the dashboard.

    Notes on units:
      - All percentage-like outputs here are **fractions 0..1** (NOT 0..100).
        The Streamlit charts convert to % for display (multiply by 100 on plot).
    """
    df = pd.read_csv(echo_csv_file)

    media_col = _find_col(df, CANDIDATES["media"], required=True)
    dur_col   = _find_col(df, CANDIDATES["duration"], required=True)
    view_col  = _find_col(df, CANDIDATES["viewtime"], required=True)
    avgv_col  = _find_col(df, CANDIDATES["avgview"], required=False)
    uid_col   = _find_col(df, CANDIDATES["user"],   required=False)

    # Normalize time columns to seconds
    df[dur_col]  = df[dur_col].map(_to_seconds)
    df[view_col] = df[view_col].map(_to_seconds)
    if avgv_col:
        df[avgv_col] = df[avgv_col].map(_to_seconds)

    # Row-level true view fraction (0..1)
    df["__true_view_frac"] = np.where(df[dur_col] > 0, df[view_col] / df[dur_col], np.nan)

    # ---------- per-media summary ----------
    # "# of Unique Viewers": prefer distinct uid if present; fallback to non-null viewtimes count
    if uid_col:
        uniq_viewers = df.groupby(df[media_col].astype(str))[uid_col].nunique(dropna=True)
    else:
        uniq_viewers = df.groupby(df[media_col].astype(str))[view_col].apply(lambda s: s.notna().sum())

    g = df.groupby(df[media_col].astype(str))
    echo_summary = pd.DataFrame({
        "Media Title": g.size().index,
        "Video Duration": g[dur_col].first().values,   # first duration per media (assumes fixed per media)
        "# of Unique Viewers": uniq_viewers.reindex(g.size().index).fillna(0).astype(int).values,
        "Average View %": g["__true_view_frac"].mean().values,  # fraction 0..1
    })

    # Placeholders populated later if needed
    echo_summary["% of Students Viewing"] = np.nan  # fraction 0..1
    echo_summary["% of Video Viewed Overall"] = np.nan  # fraction 0..1

    # ---------- module aggregation ordered by Canvas ----------
    # Expect canvas_order_df has: module, module_position, item_title_raw
    title_col = None
    if "item_title_raw" in canvas_order_df.columns:
        title_col = "item_title_raw"
    elif "video_title_raw" in canvas_order_df.columns:
        title_col = "video_title_raw"

    if title_col and "module" in canvas_order_df.columns:
        order = (
            canvas_order_df[["module", "module_position", title_col]]
            .dropna(subset=["module", title_col])
            .rename(columns={title_col: "Media Title"})
        )
        order["_key"] = _norm_series(order["Media Title"])
        es = echo_summary.copy()
        es["_key"] = _norm_series(es["Media Title"])
        merged = order.merge(es, on="_key", how="left")

        module_table = (
            merged.groupby(["module", "module_position"], as_index=False)
            .agg({
                "Average View %": "mean",             # fraction 0..1
                "# of Unique Viewers": "sum"
            })
            .rename(columns={
                "# of Unique Viewers": "# of Students Viewing",
                "module": "Module"
            })
            .sort_values(["module_position"])
            .drop(columns=["module_position"])
        )

        # Secondary series (overall) left as NaN; can be populated if you compute it elsewhere
        module_table["Overall View %"] = np.nan  # fraction 0..1

        # Optional "# of Students" column if you later merge in student counts per module
        if "# of Students" not in module_table.columns:
            module_table["# of Students"] = np.nan
    else:
        module_table = pd.DataFrame(columns=[
            "Module", "Average View %", "# of Students Viewing", "Overall View %", "# of Students"
        ])

    # ---------- de-identified student summary ----------
    if uid_col:
        # per-student average when watching
        student = (
            df.assign(_frac=df["__true_view_frac"])
              .groupby(df[uid_col].fillna("unknown"))
              .agg(**{"Average View % When Watched": ("_frac", "mean")})
              .reset_index(drop=False)
              .rename(columns={uid_col: "Student"})
        )
        # % of total video watched across all media = sum(view seconds) / sum(all durations)
        total_seconds = df[dur_col].dropna().astype(float).sum()
        per_user_seconds = df.groupby(uid_col)[view_col].sum(min_count=1)
        student["View % of Total Video"] = (
            per_user_seconds.reindex(student["Student"]).to_numpy() / total_seconds
            if total_seconds else np.nan
        )
        # De-identify students (S0001, S0002, ...)
        student["Student"] = [f"S{ix+1:04d}" for ix in range(len(student))]

        # Ensure consistent column order; add Final Grade placeholder (filled by gradebook side)
        student_table = student[["Student", "Average View % When Watched", "View % of Total Video"]].copy()
        student_table["Final Grade"] = np.nan
        # Keep fractions 0..1 for the two percentage columns
    else:
        student_table = pd.DataFrame(columns=[
            "Student", "Final Grade", "Average View % When Watched", "View % of Total Video"
        ])

    # Clean temp column
    if "__true_view_frac" in df.columns:
        del df["__true_view_frac"]

    return EchoTables(
        echo_summary=echo_summary,
        module_table=module_table,
        student_table=student_table,
    )
