from __future__ import annotations

import streamlit as st

from storage import get_current_save_for_user, list_saves_by_user, load_save_bytes, set_current_save_for_user
from utils import USERS, ensure_user_dir, list_user_saves

_BOOTSTRAP_ALL_DONE = False


def bootstrap_latest_save_for_user(user: str) -> None:
    if not user:
        return
    flag = f"_bootstrapped_save_{user}"
    if st.session_state.get(flag):
        return
    try:
        cur = get_current_save_for_user(user)
        if cur:
            try:
                folder = ensure_user_dir(user)
                dest = folder / cur[1]
                if not dest.exists():
                    data = load_save_bytes(cur[1])
                    if data:
                        dest.write_bytes(data)
            except Exception:
                pass
            st.session_state[flag] = True
            return

        lst = list_saves_by_user(user, limit=1)
        if lst:
            last_id, fname, *_ = lst[0]
            set_current_save_for_user(user, last_id)
            try:
                folder = ensure_user_dir(user)
                dest = folder / fname
                data = load_save_bytes(fname)
                if data:
                    dest.write_bytes(data)
            except Exception:
                pass
    except Exception:
        pass
    st.session_state[flag] = True


def bootstrap_all_saves() -> None:
    global _BOOTSTRAP_ALL_DONE
    if _BOOTSTRAP_ALL_DONE:
        return
    try:
        users = list(USERS.keys())
    except Exception:
        return
    for user in users:
        if not user:
            continue
        try:
            if list_user_saves(user):
                continue
            cur = get_current_save_for_user(user)
            if cur:
                fname = cur[1]
                data = load_save_bytes(fname)
                if data:
                    folder = ensure_user_dir(user)
                    dest = folder / fname
                    if not dest.exists():
                        dest.write_bytes(data)
                continue
            lst = list_saves_by_user(user, limit=1)
            if lst:
                last_id, fname, *_ = lst[0]
                try:
                    set_current_save_for_user(user, last_id)
                except Exception:
                    pass
                data = load_save_bytes(fname)
                if data:
                    folder = ensure_user_dir(user)
                    dest = folder / fname
                    if not dest.exists():
                        dest.write_bytes(data)
        except Exception:
            pass
    _BOOTSTRAP_ALL_DONE = True
