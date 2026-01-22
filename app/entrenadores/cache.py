from __future__ import annotations

from typing import List, Tuple

from conex_pkhex import extract_box, extract_team, get_box_meta_quick, has_pc_data, open_sav_cached

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


if st is not None:
    @st.cache_data(ttl=120, show_spinner=False)
    def cached_team(save_path: str, mtime: float) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_team(sav_json) or []
        except Exception:
            return []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_box(save_path: str, mtime: float, box_index: int) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_box(sav_json, box_index) or []
        except Exception:
            return []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_box_meta_quick(save_path: str, mtime: float, max_probe: int = 3) -> Tuple[int, List[str]]:
        try:
            sav_json = open_sav_cached(save_path)
            return get_box_meta_quick(sav_json, max_probe=max_probe)
        except Exception:
            return 0, []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_has_pc_data(save_path: str, mtime: float) -> bool:
        try:
            sav_json = open_sav_cached(save_path)
            return has_pc_data(sav_json)
        except Exception:
            return False
else:
    def cached_team(save_path: str, mtime: float) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_team(sav_json) or []
        except Exception:
            return []

    def cached_box(save_path: str, mtime: float, box_index: int) -> List[dict]:
        try:
            sav_json = open_sav_cached(save_path)
            return extract_box(sav_json, box_index) or []
        except Exception:
            return []

    def cached_box_meta_quick(save_path: str, mtime: float, max_probe: int = 3) -> Tuple[int, List[str]]:
        try:
            sav_json = open_sav_cached(save_path)
            return get_box_meta_quick(sav_json, max_probe=max_probe)
        except Exception:
            return 0, []

    def cached_has_pc_data(save_path: str, mtime: float) -> bool:
        try:
            sav_json = open_sav_cached(save_path)
            return has_pc_data(sav_json)
        except Exception:
            return False


def preload_entrenadores_cache(save_path: str, mtime: float, box_count: int) -> None:
    """Warm key caches once per save+mtime to speed up later interactions."""
    try:
        import streamlit as st  # type: ignore
    except Exception:
        st = None  # type: ignore

    if st is not None:
        done = st.session_state.setdefault("_preload_done", set())
        key = (save_path, mtime)
        if key in done:
            return
        done.add(key)

    try:
        cached_team(save_path, mtime)
    except Exception:
        pass
    try:
        cached_box_meta_quick(save_path, mtime)
    except Exception:
        pass
    try:
        cached_has_pc_data(save_path, mtime)
    except Exception:
        pass
    try:
        total = int(box_count) if box_count else 0
    except Exception:
        total = 0
    if total < 0:
        total = 0
    if total > 18:
        total = 18
    for i in range(total):
        try:
            cached_box(save_path, mtime, i)
        except Exception:
            continue
