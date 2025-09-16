# processors/echo_adapter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, List, Tuple
import re

import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz


@dataclass
class EchoTables:
    echo_summary: pd.DataFrame            # per-media summary
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

# Cleaning patterns
_DURATION_TAIL_RE = re.compile(r"\s*\((?:\d{1,2}:)?\d{1,2}:\d{2}\)\s*$", re.I)
_NUM_ID_TAIL_RE   = re.compile(r"\s*-\s*\d{4,}\s*$")
_READ_ONLY_RE     = re.compile(r"\s*\(read only\)\s*$", re.I)

# Fuzzy matching knobs
FUZZY_SCORER   = fuzz.token_set_ratio
THRESHOLD      = 80     # accept >= this
FALLBACK_MIN   = 70     # if nothing passes threshold, allow >= this
TOP_K          = 6      # consider top K canvas candidates per echo


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


def _strip_noise_tail(title: str) -> str:
    """Strip common trailing Canvas/Echo noise: (hh:mm[:ss]), '(read only)', '- 12345'."""
    if not title:
        return ""
    s = str(title)
    s = _READ_ONLY_RE.sub("", s)
    s = _DURATION_TAIL_RE.sub("", s)
    s = _NUM_ID_TAIL_RE.sub("", s)
    return s.strip()


def _norm_text(text: str) -> str:
    """Normalize titles for deterministic matching (lowercase, de-punctuate, collapse spaces)."""
    s = _strip_noise_tail(text)
    s = "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return " ".join(s.split())


def _norm_series(s: pd.Series) -> pd.Series:
    return s.fillna("").map(_norm_text)


def _greedy_match(
    ekeys: List[str],
    ckeys: List[str],
    threshold: int,
    fallback_min: int,
    top_k: int,
) -> List[Tuple[int, int, int]]:
    """
    Build candidate matches for each echo key (top_k canvas choices),
    then greedily select highest scores ensuring each echo and each canvas row
    is used at most once.
    Returns list of (echo_idx, canvas_idx, score).
    """
    candidates: List[Tuple[int, int, int]] = []
    for i, ek in enumerate(ekeys):
        # top_k candidates (returns tuples (choice, score, idx))
        topn = process.extract(ek, ckeys, scorer=FUZZY_SCORER, limit=top_k)
        for _, sc, j in topn:
            if sc >= threshold:
                candidates.append((i, j, int(sc)))

    # If none pass threshold, take best single fallback per echo (>= fallback_min)
    if not candidates:
        for i, ek in enumerate(ekeys):
            best = process.extractOne(ek, ckeys, scorer=FUZZY_SCORER)
            if best and best[1] >= fallback_min:
                candidates.append((i, int(best[2]), int(best[1])))

    # Greedy selection: highest score first, enforce uniqueness
    candidates.sort(key=lambda t: t[2], reverse=True)
    used_e: set[int] = set()
    used_c: set[int] = set()
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

    Percent-like values are FRACTIONS in [0..1]; charts display them as 0..100%.
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
        # Prefer duration-stripped Canvas title if available (from services.canvas)
        canvas_title_col = None
        for col in ["video_title_raw", "item_title_raw", "item_title_normalized"]:
            if col in canvas_order_df.columns:
                canvas_title_col = col
                break

        order = (
            canvas_order_df[[module_col, "module_position", canvas_title_col]]
            .dropna(subset=[module_col, canvas_title_col])
            .rename(columns={canvas_title_col: "Canvas Title"})
            .copy()
        )

        # Build normalized keys
        order["_ckey"] = _norm_series(order["Canvas Title"])
        es = echo_summary.copy()
        es["_ekey"] = _norm_series(es["Media Title"])

        # 1) Exact key equality joins first (fast path)
        m1 = order.merge(
            es[["_ekey", "Media Title", "Video Duration", "# of Unique Viewers", "Average View %"]],
            left_on="_ckey", right_on="_ekey", how="left"
        )

        # 2) Greedy one-to-one fuzzy matching for any rows still unmatched
        unmatched_idx = m1.index[m1["Average View %"].isna()].tolist()
        if unmatched_idx:
            # Build unique lists aligned to row indices
            ckeys = m1.loc[unmatched_idx, "_ckey"].fillna("").astype(str).tolist()
            ekeys = es["_ekey"].fillna("").astype(str).tolist()

            # Map back to DataFrame indices
            pairs = _greedy_match(ekeys, ckeys, THRESHOLD, FALLBACK_MIN, TOP_K)
            if pairs:
                # Build a mapping from echo ek -> echo row, and canvas list position -> m1 index
                # ekeys[i] is the echo key at i; ckeys[j] is the canvas key for m1 row unmatched_idx[j]
                rows: List[dict] = []
                for i, j, sc in pairs:
                    m1_row_index = unmatched_idx[j]
                    ek = ekeys[i]
                    erow = es.loc[es["_ekey"] == ek].iloc[0]
                    rows.append({
                        "idx": m1_row_index,
                        "Media Title": erow["Media Title"],
                        "Video Duration": erow["Video Duration"],
                        "# of Unique Viewers": erow["# of Unique Viewers"],
                        "Average View %": erow["Average View %"],
                    })
                if rows:
                    m2 = pd.DataFrame(rows).set_index("idx")
                    fill_cols = ["Media Title", "Video Duration", "# of Unique Viewers", "Average View %"]
                    m1.loc[m2.index, fill_cols] = m2[fill_cols].values

        # Aggregate by module
        have = m1.dropna(subset=["Average View %"])
        if have.empty:
            module_table = pd.DataFrame(columns=[
                "Module", "Average View %", "# of Students Viewing", "Overall View %", "# of Students"
            ])
        else:
            module_table = (
                have.groupby([module_col, "module_position"], as_index=False)
                    .agg({
                        "Average View %": "mean",                       # average across medias in the module
                        "# of Unique Viewers": "sum"                    # sum counts
                    })
                    .rename(columns={"# of Unique Viewers": "# of Students Viewing",
                                     module_col: "Module"})
                    .sort_values(["module_position"])
                    .drop(columns=["module_position"])
            )
            module_table["Overall View %"] = np.nan
            if "# of Students" not in module_table.columns:
                module_table["# of Students"] = np.nan

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
