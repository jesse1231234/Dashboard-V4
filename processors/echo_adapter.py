# processors/echo_adapter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, List, Tuple

import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz


@dataclass
class EchoTables:
    echo_summary: pd.DataFrame            # per-media summary (by media title)
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

# Fuzzy matching params (tune if needed)
FUZZY_SCORER = fuzz.token_set_ratio
THRESHOLD = 82            # accept pairs scoring >= THRESHOLD
FALLBACK_MIN = 70         # if nothing meets THRESHOLD, allow a best-effort fallback >= this
WINNER_MARGIN = 0         # with greedy matching + uniqueness, we can set margin to 0


# ---------- helpers ----------

def _find_col(df: pd.DataFrame, want: Iterable[str], required: bool = True) -> Optional[str]:
    """Return a matching column name (case-insensitive)."""
    low = {c.lower(): c for c in df.columns}
    for w in want:
        if w in low:
            return low[w]
    for k, v in low.items():
        if any(w in k for w in want):
            return v
    if required:
        raise KeyError(f"Missing required column; need one of: {list(want)}\nAvailable: {list(df.columns)}")
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
    try:
        return float(s)  # numeric-as-string
    except Exception:
        pass
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
    """
    Normalize titles for matching:
    - casefold
    - keep alphanumerics and whitespace (no token deletion — avoid over-normalizing)
    - collapse whitespace
    """
    s = "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in str(text))
    return " ".join(s.split())


def _norm_series(s: pd.Series) -> pd.Series:
    return s.fillna("").map(_norm_text)


def _greedy_bipartite_from_scores(
    scores: np.ndarray, echos: List[str], canvases: List[str], threshold: int, fallback_min: int
) -> List[Tuple[int, int, int]]:
    """
    Given an NxM score matrix, select a set of (echo_i, canvas_j) pairs:
      - sort all candidates by score desc
      - greedily pick if echo_i and canvas_j are both unused
      - only accept scores >= threshold; if none accepted at all, allow >= fallback_min
    Returns: list of (i, j, score)
    """
    n, m = scores.shape
    candidates = []
    for i in range(n):
        for j in range(m):
            sc = int(scores[i, j])
            if sc >= threshold:
                candidates.append((i, j, sc))

    # If nothing meets threshold, allow a best match per echo >= fallback_min (if available)
    if not candidates:
        for i in range(n):
            jbest = int(np.argmax(scores[i])) if m else -1
            if jbest >= 0:
                sc = int(scores[i, jbest])
                if sc >= fallback_min:
                    candidates.append((i, jbest, sc))

    candidates.sort(key=lambda t: t[2], reverse=True)  # high score first
    used_e = set()
    used_c = set()
    chosen: List[Tuple[int, int, int]] = []
    for i, j, sc in candidates:
        if i in used_e or j in used_c:
            continue
        chosen.append((i, j, sc))
        used_e.add(i)
        used_c.add(j)
    return chosen


# ---------- main builder ----------

def build_echo_tables(echo_csv_file, canvas_order_df: pd.DataFrame) -> EchoTables:
    """
    Read the Echo CSV and return DataFrames for the dashboard.

    All percentage-like outputs here are **fractions 0..1** (NOT 0..100).
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

    # ---------- per-media summary (by title) ----------
    # Unique viewers: prefer distinct uid if present; fallback to non-null viewtimes count
    if uid_col:
        uniq_viewers = df.groupby(df[media_col].astype(str))[uid_col].nunique(dropna=True)
    else:
        uniq_viewers = df.groupby(df[media_col].astype(str))[view_col].apply(lambda s: s.notna().sum())

    g = df.groupby(df[media_col].astype(str))
    echo_summary = pd.DataFrame({
        "Media Title": g.size().index,
        "Video Duration": g[dur_col].first().values,                 # assume fixed per media
        "# of Unique Viewers": uniq_viewers.reindex(g.size().index).fillna(0).astype(int).values,
        "Average View %": g["__true_view_frac"].mean().values,       # fraction 0..1
    })
    echo_summary["% of Students Viewing"] = np.nan                   # fraction 0..1 (optional downstream)
    echo_summary["% of Video Viewed Overall"] = np.nan               # fraction 0..1 (optional downstream)

    # ---------- Canvas side (module items) ----------
    module_col = "module"
    if canvas_order_df is None or canvas_order_df.empty or module_col not in canvas_order_df.columns:
        module_table = pd.DataFrame(columns=[
            "Module", "Average View %", "# of Students Viewing", "Overall View %", "# of Students"
        ])
    else:
        order = (
            canvas_order_df[[module_col, "module_position", "item_title_raw"]]
            .dropna(subset=[module_col, "item_title_raw"])
            .rename(columns={"item_title_raw": "Canvas Title"})
        ).copy()

        # Normalize titles for matching
        order["_ckey"] = _norm_series(order["Canvas Title"])
        es = echo_summary.copy()
        es["_ekey"] = _norm_series(es["Media Title"])

        # Build similarity matrix between all echo titles and all canvas titles
        ekeys = es["_ekey"].tolist()
        ckeys = order["_ckey"].tolist()
        if not ekeys or not ckeys:
            module_table = pd.DataFrame(columns=[
                "Module", "Average View %", "# of Students Viewing", "Overall View %", "# of Students"
            ])
        else:
            scores = process.cdist(ekeys, ckeys, scorer=FUZZY_SCORER)
            pairs = _greedy_bipartite_from_scores(scores, ekeys, ckeys, THRESHOLD, FALLBACK_MIN)

            # Materialize chosen matches
            if pairs:
                rows = []
                for i, j, sc in pairs:
                    rows.append({
                        "Media Title": es.iloc[i]["Media Title"],
                        "Canvas Title": order.iloc[j]["Canvas Title"],
                        "Module": order.iloc[j][module_col],
                        "module_position": order.iloc[j]["module_position"],
                        "score": sc,
                    })
                match_df = pd.DataFrame(rows)

                m = match_df.merge(
                    echo_summary[["Media Title", "Average View %", "# of Unique Viewers"]],
                    on="Media Title", how="left"
                )
                module_table = (
                    m.groupby(["Module", "module_position"], as_index=False)
                     .agg({
                         "Average View %": "mean",                       # average across medias in the module
                         "# of Unique Viewers": "sum"                    # sum counts
                     })
                     .rename(columns={"# of Unique Viewers": "# of Students Viewing"})
                     .sort_values(["module_position"])
                     .drop(columns=["module_position"])
                )
                module_table["Overall View %"] = np.nan
                if "# of Students" not in module_table.columns:
                    module_table["# of Students"] = np.nan
            else:
                module_table = pd.DataFrame(columns=[
                    "Module", "Average View %", "# of Students Viewing", "Overall View %", "# of Students"
                ])

    # ---------- de-identified student summary ----------
    if uid_col:
        student = (
            df.assign(_frac=df["__true_view_frac"])
              .groupby(df[uid_col].fillna("unknown"))
              .agg(**{"Average View % When Watched": ("_frac", "mean")})
              .reset_index(drop=False)
              .rename(columns={uid_col: "Student"})
        )
        total_seconds = df[dur_col].dropna().astype(float).sum()
        per_user_seconds = df.groupby(uid_col)[view_col].sum(min_count=1)
        student["View % of Total Video"] = (
            per_user_seconds.reindex(student["Student"]).to_numpy() / total_seconds
            if total_seconds else np.nan
        )
        # De-identify Student IDs
        student["Student"] = [f"S{ix+1:04d}" for ix in range(len(student))]
        student_table = student[["Student", "Average View % When Watched", "View % of Total Video"]]
        student_table["Final Grade"] = np.nan
    else:
        student_table = pd.DataFrame(columns=[
            "Student", "Final Grade", "Average View % When Watched", "View % of Total Video"
        ])

    # Cleanup temp
    if "__true_view_frac" in df.columns:
        del df["__true_view_frac"]

    return EchoTables(
        echo_summary=echo_summary,
        module_table=module_table,
        student_table=student_table,
    )
