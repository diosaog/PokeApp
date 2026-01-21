from __future__ import annotations

import streamlit as st

from storage import get_current_save_for_user, list_saves_by_user, load_save_bytes
from utils import ensure_user_dir, list_user_saves


def active_save_for(trainer: str) -> str | None:
    try:
        saves = list_user_saves(trainer)
        if not saves:
            return None
        p = saves[0]
        return str(p)
    except Exception:
        return None


def ensure_local_save_for(trainer: str) -> None:
    """Ensure there is a local save for the trainer using remote storage if needed."""
    if not trainer:
        return
    key = f"_ensure_local_save_for_{trainer}"
    if st.session_state.get(key):
        return
    try:
        if list_user_saves(trainer):
            st.session_state[key] = True
            return
        cur = get_current_save_for_user(trainer)
        if cur:
            fname = cur[1]
            data = load_save_bytes(fname)
            if data:
                folder = ensure_user_dir(trainer)
                dest = folder / fname
                dest.write_bytes(data)
                st.session_state[key] = True
                return
        remote = list_saves_by_user(trainer, limit=1)
        if remote:
            _, fname, *_ = remote[0]
            data = load_save_bytes(fname)
            if data:
                folder = ensure_user_dir(trainer)
                dest = folder / fname
                dest.write_bytes(data)
    except Exception:
        pass
    st.session_state[key] = True
