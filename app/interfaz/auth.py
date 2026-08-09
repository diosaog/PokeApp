from __future__ import annotations

from html import escape
import os

import streamlit as st

from app.interfaz.bootstrap import bootstrap_latest_save_for_user
from app.interfaz.media import image_data_uri
from storage import init_storage, settings_get
from utils import USERS, users_with_retired_last


def _cache_data(ttl: int = 60):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


def _trainer_image_uri(user: str) -> str:
    try:
        from app.entrenadores.profile import find_trainer_image

        path = find_trainer_image(user)
        if not path:
            return ""
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = None
        return image_data_uri(path, mtime, min_bytes=256)
    except Exception:
        return ""


def _render_login_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"],
        div[data-testid="collapsedControl"] {
          display: none !important;
        }
        .main .block-container {
          max-width: 500px;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding-top: 32px;
          padding-bottom: 3rem;
        }
        .stApp::after {
          display: none !important;
          content: "" !important;
        }
        .auth-hero {
          position: relative;
          min-height: 0;
          margin-bottom: 18px;
          padding: 0;
          overflow: hidden;
          border: 0;
          border-radius: 0;
          background: transparent;
          box-shadow: none;
          text-align: center;
        }
        .auth-hero::before {
          content: "";
          position: absolute;
          left: 50%;
          top: -92px;
          width: 260px;
          height: 260px;
          transform: translateX(-50%);
          border-radius: 50%;
          border: 30px solid rgba(255,255,255,0.025);
          box-shadow:
            inset 0 0 0 24px rgba(0,0,0,0.18),
            inset 0 0 0 26px rgba(255,255,255,0.025);
          pointer-events: none;
        }
        .auth-kicker {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 7px 11px;
          border: 1px solid var(--border-soft);
          border-radius: 999px;
          background: rgba(77,141,255,0.09);
          color: var(--text-secondary);
          font-family: var(--font-ui);
          font-size: 12px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .auth-title {
          max-width: 460px;
          margin: 14px auto 0;
          color: var(--text-primary);
          font-family: var(--font-ui);
          font-size: 34px;
          font-weight: 900;
          line-height: 1.06;
          text-transform: none;
          letter-spacing: 0;
        }
        .auth-trainer-card {
          margin: 14px 0 16px;
          padding: 18px;
          display: grid;
          grid-template-columns: 104px minmax(0, 1fr);
          gap: 16px;
          align-items: center;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-large);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)),
            var(--surface-1);
          box-shadow: var(--shadow-card);
        }
        .auth-avatar {
          width: 104px;
          height: 104px;
          display: grid;
          place-items: center;
          overflow: hidden;
          border: 1px solid var(--border-normal);
          border-radius: var(--radius-card);
          background:
            radial-gradient(circle at 50% 42%, rgba(77,141,255,0.18), transparent 58%),
            var(--surface-2);
        }
        .auth-avatar img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }
        .auth-pokeball {
          width: 46px;
          height: 46px;
          border-radius: 50%;
          position: relative;
          background: linear-gradient(180deg, #e95151 0 48%, #131820 48% 52%, #f1f5f8 52% 100%);
          border: 3px solid #131820;
          box-shadow: inset 0 0 0 2px rgba(255,255,255,0.12);
        }
        .auth-pokeball::after {
          content: "";
          position: absolute;
          left: 50%;
          top: 50%;
          width: 13px;
          height: 13px;
          transform: translate(-50%, -50%);
          border-radius: 50%;
          background: #f1f5f8;
          border: 3px solid #131820;
        }
        .auth-trainer-name {
          color: var(--text-primary);
          font-family: var(--font-ui);
          font-size: 18px;
          font-weight: 900;
          text-transform: none;
          line-height: 1.25;
          letter-spacing: 0;
        }
        .auth-trainer-role {
          margin-top: 4px;
          color: var(--text-secondary);
          font-size: 13px;
          font-weight: 700;
        }
        .main .stSelectbox,
        .main div[data-testid="stForm"] {
          padding: 16px;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius-large);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.012)),
            var(--surface-1);
          box-shadow: var(--shadow-card);
        }
        .main .stSelectbox {
          margin-bottom: 12px;
        }
        .main div[data-testid="stForm"] {
          margin-top: 0;
        }
        .main .stForm label,
        .main .stSelectbox label {
          color: var(--text-secondary) !important;
          font-size: 12px !important;
          font-weight: 800 !important;
          text-transform: uppercase !important;
        }
        @media (max-width: 900px) {
          .auth-title { font-size: 24px; }
          .main .block-container {
            max-width: 100%;
            padding: 24px 16px 44px;
          }
          .auth-trainer-card {
            grid-template-columns: 86px minmax(0, 1fr);
          }
          .auth-avatar {
            width: 86px;
            height: 86px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _trainer_card(user: str) -> str:
    image_uri = _trainer_image_uri(user)
    avatar = (
        f"<img src='{image_uri}' alt='Retrato de {escape(user)}'/>"
        if image_uri
        else "<div class='auth-pokeball'></div>"
    )
    return (
        "<div class='auth-trainer-card'>"
        f"<div class='auth-avatar'>{avatar}</div>"
        "<div>"
        f"<div class='auth-trainer-name'>{escape(user)}</div>"
        "<div class='auth-trainer-role'>Entrenador</div>"
        "</div>"
        "</div>"
    )


def _stored_pin_for(user: str) -> str | None:
    try:
        value = settings_get(f"pin:{user}")
        pin = str(value or "").strip()
        if len(pin) == 4 and pin.isdigit():
            return pin
    except Exception:
        return None
    return None


def _password_ok(user: str, password: str, users: dict[str, str]) -> bool:
    stored_pin = _stored_pin_for(user)
    password_in = str(password or "").strip()
    if stored_pin:
        return password_in == stored_pin
    code = users.get(user)
    return (not code) or (bool(password_in) and password_in.lower() == str(code).lower())


def _authenticate(user: str, password: str, users: dict[str, str]) -> bool:
    if not _password_ok(user, password, users):
        return False
    st.session_state.auth_ok = True
    st.session_state.user = user
    try:
        bootstrap_latest_save_for_user(user)
    except Exception:
        pass
    return True


def login_gate() -> None:
    init_storage()
    users = USERS
    if st.session_state.get("auth_ok"):
        if st.session_state.get("user") not in users:
            st.session_state.auth_ok = False
            st.session_state.user = None
            st.rerun()
        try:
            bootstrap_latest_save_for_user(st.session_state.get("user") or "")
        except Exception:
            pass
        return

    _render_login_css()
    user_options = users_with_retired_last(users)
    if not user_options:
        st.error("No hay entrenadores configurados.")
        st.stop()

    st.markdown(
        (
            "<div class='auth-hero'>"
            "<div class='auth-kicker'>PokeApp League</div>"
            "<div class='auth-title'>Centro de entrenadores</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    selected_default = st.session_state.get("login_user")
    selected_index = (
        user_options.index(selected_default)
        if selected_default in user_options
        else 0
    )
    user = st.selectbox(
        "Entrenador",
        user_options,
        index=selected_index,
        key="login_user",
    )
    st.markdown(_trainer_card(user), unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        password = st.text_input(
            "PIN",
            type="password",
            max_chars=8,
            placeholder="PIN",
        )
        submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if submitted:
        if _authenticate(user, password, users):
            st.success(f"Bienvenido, {user}")
            st.rerun()
        st.error("Usuario o codigo/PIN incorrecto")

    st.stop()
