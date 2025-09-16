# services/canvas.py
from __future__ import annotations

from typing import Optional, List, Dict
import re

import httpx
import pandas as pd


class CanvasService:
    """
    Minimal Canvas API client for read-only analytics.

    Features used:
      - Modules & Module Items (to derive module ordering)
      - Enrollments (active StudentEnrollment count)

    Authentication: Personal Access Token via Authorization: Bearer <token>
    Base URL example: https://colostate.instructure.com
    """

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    # ---------------- Internal helpers ----------------

    def _get_all(self, url: str, params: Dict | None = None) -> List[Dict]:
        """
        Follow Canvas pagination via Link header, aggregating all pages.
        """
        out: List[Dict] = []
        next_url = url
        next_params = params or {}

        while next_url:
            r = self.client.get(next_url, params=next_params)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                out.extend(data)
            elif isinstance(data, dict):
                out.append(data)

            # Parse Link header for rel="next"
            next_url = None
            link = r.headers.get("Link")
            if link:
                for part in (p.strip() for p in link.split(",")):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>").strip()
                        break

            # only pass params on first request
            next_params = None

        return out

    # ---------------- Public API ----------------

    # Modules & Items

    def list_modules(self, course_id: int) -> List[Dict]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/modules"
        return self._get_all(url, params={"per_page": 100})

    def list_module_items(self, course_id: int, module_id: int) -> List[Dict]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/modules/{module_id}/items"
        return self._get_all(url, params={"per_page": 100})

    # --- title cleanup: strip trailing (mm:ss) or (h:mm:ss) often appended in Canvas ---
    _DURATION_TAIL_RE = re.compile(r"\s*\((?:\d{1,2}:)?\d{1,2}:\d{2}\)\s*$")

    @classmethod
    def _strip_duration_suffix(cls, title: str) -> str:
        if not title:
            return ""
        return cls._DURATION_TAIL_RE.sub("", str(title)).strip()

    def build_order_df(self, course_id: int) -> pd.DataFrame:
        """
        Return a DataFrame describing the course content order.

        Columns:
          - module (str)
          - module_position (int)
          - item_title_raw (str)             # original Canvas item title
          - video_title_raw (str)            # Canvas title with trailing (hh:mm[:ss]) removed
          - item_title_normalized (str)      # casefolded raw title
          - item_type (str)                  # 'Assignment','ExternalTool','Page', ...
          - item_position (int)
          - html_url (str|None)
          - external_url (str|None)
        """
        modules = self.list_modules(course_id)

        rows: List[Dict] = []
        for m in sorted(modules, key=lambda x: x.get("position", 0)):
            mod_id = m.get("id")
            items = self.list_module_items(course_id, mod_id)
            for it in sorted(items, key=lambda x: x.get("position", 0)):
                raw_title = (it.get("title") or "").strip()
                rows.append(
                    {
                        "module": m.get("name"),
                        "module_position": m.get("position"),
                        "item_title_raw": raw_title,
                        "video_title_raw": self._strip_duration_suffix(raw_title),
                        "item_title_normalized": raw_title.casefold(),
                        "item_type": it.get("type"),
                        "item_position": it.get("position"),
                        "html_url": it.get("html_url"),
                        "external_url": it.get("external_url"),
                    }
                )

        return pd.DataFrame(rows)

    # Enrollments (preferred student count)

    def get_student_count(self, course_id: int) -> Optional[int]:
        """
        Count unique user_id for active StudentEnrollment.
        Returns None if not permitted or empty.
        """
        url = f"{self.base_url}/api/v1/courses/{course_id}/enrollments"
        params = {"per_page": 100, "type[]": "StudentEnrollment", "state[]": "active"}
        try:
            enrollments = self._get_all(url, params=params)
        except httpx.HTTPStatusError:
            return None

        if not enrollments:
            return None

        user_ids = {e.get("user_id") for e in enrollments if e.get("user_id") is not None}
        return len(user_ids) if user_ids else None

    # ---------------- Cleanup ----------------

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        # Best-effort close without raising in destructor
        try:
            self.close()
        except Exception:
            pass
