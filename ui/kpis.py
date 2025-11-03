# ui/kpis.py
from __future__ import annotations

from typing import Optional, Dict

import numpy as np
import pandas as pd


# We support full letter set; courses that don't use +/- will still median correctly.
LETTER_ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"]
LETTER_RANK = {g: i for i, g in enumerate(LETTER_ORDER)}
RANK_TO_LETTER = {i: g for g, i in LETTER_RANK.items()}


def median_letter(series: pd.Series) -> str:
    """
    Compute median letter grade using fixed ordering A+..F.
    Unknown values are ignored. Returns "—" if nothing usable.
    """
    if series is None:
        return "—"
    s = series.astype(str).str.strip().str.upper()
    s = s[s.isin(LETTER_ORDER)]
    if s.empty:
        return "—"
    ranks = s.map(LETTER_RANK)
    med_rank = int(np.median(ranks))
    return RANK_TO_LETTER.get(med_rank, "—")


def _first_numeric_mean(df: pd.DataFrame, cols: list[str]) -> Optional[float]:
    """Return mean of the first available numeric column (0..100 expected), else None."""
    for col in cols:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().any():
                return float(vals.mean())
    return None


def compute_kpis(
    echo_tables,              # processors.echo_adapter.EchoTables
    gb_tables,                # processors.grades_adapter.GradebookTables
    students_from_canvas: Optional[int] = None,
) -> Dict[str, Optional[float | int | str]]:
    """
    Returns a dict with:
      - "# Students" (int)
      - "Median Letter Grade" (str)
      - "Average Echo360 engagement" (0..100)
      - "# of Fs" (int)
      - "Avg Assignment Grade (class)" (fraction 0..1)
    """
    # ---------- # Students ----------
    if students_from_canvas is not None:
        n_students = int(students_from_canvas)
    else:
        n_students = int(len(gb_tables.gradebook_df.index)) if gb_tables.gradebook_df is not None else 0

    # ---------- Median Letter Grade ----------
    med_letter = (
        median_letter(gb_tables.gradebook_df.get("Final Grade"))
        if gb_tables.gradebook_df is not None and "Final Grade" in gb_tables.gradebook_df.columns
        else "—"
    )

    # ---------- Average Echo360 engagement (percent 0..100) ----------
    avg_echo_pct: Optional[float] = None
    if echo_tables is not None and echo_tables.echo_summary is not None and not echo_tables.echo_summary.empty:
        # Echo adapter provides "Average View %" as FRACTION 0..1; convert to percent.
        vals = pd.to_numeric(echo_tables.echo_summary.get("Average View %"), errors="coerce")
        if vals.notna().any():
            avg_echo_pct = float(vals.mean() * 100.0)

    # ---------- # of Fs ----------
    num_fs = 0
    if gb_tables.gradebook_df is not None and not gb_tables.gradebook_df.empty:
        if "Final Grade" in gb_tables.gradebook_df.columns:
            num_fs = int((gb_tables.gradebook_df["Final Grade"].astype(str).str.upper() == "F").sum())
        else:
            # Fallback: infer via numeric score < 60 if letter column is missing
            numeric = _first_numeric_mean(gb_tables.gradebook_df, ["Final Score", "Current Score", "Unposted Final Score"])
            # If we only have the mean, we can't count Fs reliably; leave as 0.
            num_fs = 0

    # ---------- Avg Assignment Grade (class) (fraction 0..1) ----------
    avg_assignment_frac: Optional[float] = None
    gsum = gb_tables.gradebook_summary_df
    if gsum is not None and not gsum.empty and "Average Excluding Zeros" in gsum.index:
        row = pd.to_numeric(gsum.loc["Average Excluding Zeros"], errors="coerce")
        if row.notna().any():
            avg_assignment_frac = float(row.mean())  # keep as fraction (0..1). UI multiplies by 100.

    return {
        "# Students": n_students,
        "Average Grade": avg_grade,  # 0..100 or None
        "Median Letter Grade": med_letter,
        "Average Echo360 engagement": avg_echo_pct,  # 0..100 or None
        "# of Fs": num_fs,
        "Avg Assignment Grade (class)": avg_assignment_frac,  # fraction 0..1 or None
    }





