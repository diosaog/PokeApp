from __future__ import annotations

import streamlit as st

from app.interfaz.bootstrap import bootstrap_latest_save_for_user
from storage import init_storage, settings_get
from utils import USERS


def login_gate() -> None:
    init_storage()
    if st.session_state.get("auth_ok"):
        try:
            bootstrap_latest_save_for_user(st.session_state.get("user") or "")
        except Exception:
            pass
        return

    st.header("Inicio de sesion")
    col1, col2 = st.columns(2)
    with col1:
        user = st.selectbox("Usuario", list(USERS.keys()), index=0)
    with col2:
        pwd = st.text_input("PIN / Codigo de acceso", type="password", max_chars=8)
    ok = st.button("Entrar", type="primary")
    if ok:
        pin_key = f"pin:{user}"
        stored_pin = None
        try:
            val = settings_get(pin_key)
            if val and len(str(val).strip()) == 4 and str(val).strip().isdigit():
                stored_pin = str(val).strip()
        except Exception:
            stored_pin = None

        code = USERS.get(user)
        pwd_in = (pwd or "").strip()
        if stored_pin:
            ok_pin = pwd_in == stored_pin
        else:
            ok_pin = (not code) or (pwd_in and pwd_in.lower() == str(code).lower())

        if ok_pin:
            st.session_state.auth_ok = True
            st.session_state.user = user
            try:
                bootstrap_latest_save_for_user(user)
            except Exception:
                pass
            st.success(f"Bienvenido, {user}")
            st.rerun()
        else:
            st.error("Usuario o codigo/PIN incorrecto")
    st.stop()
