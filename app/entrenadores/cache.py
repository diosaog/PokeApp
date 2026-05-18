from __future__ import annotations

from typing import List, Tuple

from app.entrenadores.constants import DEAD_BOX_INDEX, TOTAL_BOXES
from app.entrenadores.badges import count_badges
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
            return extract_box(sav_json, box_index, save_path=save_path) or []
        except Exception:
            return []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_box_meta_quick(save_path: str, mtime: float, max_probe: int = 3) -> Tuple[int, List[str]]:
        try:
            sav_json = open_sav_cached(save_path)
            return get_box_meta_quick(sav_json, save_path=save_path, max_probe=max_probe)
        except Exception:
            return 0, []

    @st.cache_data(ttl=120, show_spinner=False)
    def cached_has_pc_data(save_path: str, mtime: float) -> bool:
        try:
            sav_json = open_sav_cached(save_path)
            return has_pc_data(sav_json, save_path=save_path)
        except Exception:
            return False

    @st.cache_data(ttl=180, show_spinner=False)
    def cached_badge_count(save_path: str, mtime: float) -> int:
        try:
            sav_json = open_sav_cached(save_path)
            return int(count_badges(sav_json))
        except Exception:
            return 0

    @st.cache_data(ttl=180, show_spinner=False)
    def cached_dead_count(save_path: str, mtime: float, box_index: int = DEAD_BOX_INDEX) -> int:
        try:
            return len(cached_box(save_path, mtime, int(box_index)) or [])
        except Exception:
            return 0
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
            return extract_box(sav_json, box_index, save_path=save_path) or []
        except Exception:
            return []

    def cached_box_meta_quick(save_path: str, mtime: float, max_probe: int = 3) -> Tuple[int, List[str]]:
        try:
            sav_json = open_sav_cached(save_path)
            return get_box_meta_quick(sav_json, save_path=save_path, max_probe=max_probe)
        except Exception:
            return 0, []

    def cached_has_pc_data(save_path: str, mtime: float) -> bool:
        try:
            sav_json = open_sav_cached(save_path)
            return has_pc_data(sav_json, save_path=save_path)
        except Exception:
            return False

    def cached_badge_count(save_path: str, mtime: float) -> int:
        try:
            sav_json = open_sav_cached(save_path)
            return int(count_badges(sav_json))
        except Exception:
            return 0

    def cached_dead_count(save_path: str, mtime: float, box_index: int = DEAD_BOX_INDEX) -> int:
        try:
            return len(cached_box(save_path, mtime, int(box_index)) or [])
        except Exception:
            return 0


def preload_entrenadores_cache(save_path: str, mtime: float, box_count: int) -> None:
    """Warm key caches once per save+mtime to speed up later interactions.

    We intentionally preload only the most relevant data to avoid slow first render:
    - Team
    - Box 1
    - Box 2
    - Box 8 (muertos)
    """
    try:
        import streamlit as st  # type: ignore
    except Exception:
        st = None  # type: ignore

    if st is not None:
        done = st.session_state.setdefault("_preload_done_entrenadores", set())
        key = (save_path, mtime)
        if isinstance(done, set) and key in done:
            return
        if isinstance(done, set):
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
        cached_badge_count(save_path, mtime)
    except Exception:
        pass
    try:
        total = int(box_count) if box_count else 0
    except Exception:
        total = 0
    if total < 0:
        total = 0
    if total > TOTAL_BOXES:
        total = TOTAL_BOXES

    targets: list[int] = []
    for idx in (0, 1, DEAD_BOX_INDEX):
        if total <= 0:
            continue
        if 0 <= idx < total and idx not in targets:
            targets.append(idx)

    # Fallback if total is unknown: try the key boxes directly and ignore failures.
    if not targets:
        targets = [0, 1, DEAD_BOX_INDEX]

    for i in targets:
        try:
            cached_box(save_path, mtime, i)
        except Exception:
            continue
