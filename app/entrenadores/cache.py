from __future__ import annotations

from typing import List

from conex_pkhex import extract_box, extract_team, open_sav_cached

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


if st is not None:
    @st.cache_data(ttl=120, show_spinner=False)
    def cached_team(save_path: str, mtime: float) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_team(sav_json, save_path=save_path) or []
        except Exception:
            return []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_box(save_path: str, mtime: float, box_index: int) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_box(sav_json, box_index, save_path=save_path) or []
        except Exception:
            return []
else:
    def cached_team(save_path: str, mtime: float) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_team(sav_json, save_path=save_path) or []
        except Exception:
            return []

    def cached_box(save_path: str, mtime: float, box_index: int) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_box(sav_json, box_index, save_path=save_path) or []
        except Exception:
            return []
