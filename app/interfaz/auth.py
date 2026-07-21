from __future__ import annotations

import base64
from html import escape
import mimetypes
import os

import streamlit as st

from app.interfaz.bootstrap import bootstrap_latest_save_for_user
from storage import init_storage, settings_get
from utils import USERS, users_with_retired_last


def _cache_data(ttl: int = 60):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


@_cache_data(ttl=60)
def _img_uri(path: str, mtime: float | None = None) -> str:
    _ = mtime
    try:
        if not path or os.path.getsize(path) < 256:
            return ""
        media_type = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as fh:
            return f"data:{media_type};base64,{base64.b64encode(fh.read()).decode('ascii')}"
    except Exception:
        return ""


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
        return _img_uri(path, mtime)
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
          max-width: 1180px;
          padding-top: 5.2rem;
          padding-bottom: 3rem;
        }
        .stApp::after {
          content: "POKEAPP 2.0   LIGA PRIVADA";
        }
        .auth-hero {
          position: relative;
          min-height: 430px;
          padding: 24px;
          overflow: hidden;
          border: 1px solid rgba(216,223,232,0.24);
          background:
            linear-gradient(135deg, rgba(111,197,255,0.22), transparent 32%),
            linear-gradient(315deg, rgba(255,198,88,0.16), transparent 40%),
            linear-gradient(180deg, rgba(39,46,57,0.96), rgba(17,22,30,0.98));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 18px 42px rgba(0,0,0,0.34);
          clip-path: polygon(18px 0, 100% 0, 100% calc(100% - 18px), calc(100% - 18px) 100%, 0 100%, 0 18px);
        }
        .auth-hero::before {
          content: "";
          position: absolute;
          right: -82px;
          bottom: -98px;
          width: 300px;
          height: 300px;
          border-radius: 50%;
          border: 34px solid rgba(255,255,255,0.08);
          box-shadow:
            inset 0 0 0 28px rgba(0,0,0,0.16),
            inset 0 0 0 30px rgba(255,255,255,0.06);
        }
        .auth-kicker {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 7px 10px;
          border: 1px solid rgba(216,223,232,0.32);
          background: rgba(255,255,255,0.06);
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .auth-title {
          max-width: 720px;
          margin-top: 22px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 34px;
          line-height: 1.16;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .auth-subtitle {
          max-width: 720px;
          margin-top: 12px;
          color: var(--bw2-text-soft);
          font-size: 24px;
          line-height: 1.12;
        }
        .auth-status-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          margin-top: 28px;
          max-width: 760px;
        }
        .auth-status {
          min-height: 86px;
          padding: 11px;
          border: 1px solid rgba(216,223,232,0.18);
          background: rgba(9,13,19,0.44);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .auth-status-label {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .auth-status-value {
          margin-top: 11px;
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 12px;
          line-height: 1.22;
          letter-spacing: 0;
        }
        .auth-panel {
          padding: 18px;
          border: 1px solid rgba(216,223,232,0.24);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.06), transparent 42%),
            linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 18px 42px rgba(0,0,0,0.3);
          clip-path: polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px);
        }
        .auth-panel-title {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 15px;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .auth-panel-sub {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 19px;
          line-height: 1.1;
        }
        .auth-trainer-card {
          margin: 14px 0 12px;
          padding: 12px;
          display: grid;
          grid-template-columns: 96px minmax(0, 1fr);
          gap: 14px;
          align-items: center;
          border: 1px solid rgba(216,223,232,0.2);
          background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
        }
        .auth-avatar {
          width: 96px;
          height: 96px;
          display: grid;
          place-items: center;
          overflow: hidden;
          border: 1px solid rgba(216,223,232,0.32);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.06), transparent),
            #0e141c;
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
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 14px;
          text-transform: uppercase;
          line-height: 1.25;
          letter-spacing: 0;
        }
        .auth-trainer-meta {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-size: 19px;
          line-height: 1.08;
        }
        .auth-footnote {
          margin-top: 12px;
          color: var(--bw2-text-dim);
          font-size: 17px;
          line-height: 1.1;
        }
        @media (max-width: 900px) {
          .auth-title { font-size: 24px; }
          .auth-status-grid { grid-template-columns: 1fr; }
          .auth-hero { min-height: 0; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_card(label: str, value: str) -> str:
    return (
        "<div class='auth-status'>"
        f"<div class='auth-status-label'>{escape(label)}</div>"
        f"<div class='auth-status-value'>{escape(value)}</div>"
        "</div>"
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
        "<div class='auth-trainer-meta'>Acceso privado de entrenador</div>"
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

    hero, panel = st.columns([1.12, 0.88], gap="large")
    with hero:
        st.markdown(
            (
                "<div class='auth-hero'>"
                "<div class='auth-kicker'>PokeApp 2.0</div>"
                "<div class='auth-title'>Liga privada de entrenadores</div>"
                "<div class='auth-subtitle'>"
                "Entra con tu entrenador para revisar equipo, jornada, tienda y combates."
                "</div>"
                "<div class='auth-status-grid'>"
                + _status_card("Liga", "Temporada activa")
                + _status_card("Acceso", "PIN privado")
                + _status_card("Modo", "Competitivo")
                + "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with panel:
        st.markdown(
            """
            <div class='auth-panel'>
              <div class='auth-panel-title'>Acceso entrenador</div>
              <div class='auth-panel-sub'>Selecciona perfil y confirma tu PIN.</div>
            </div>
            """,
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
                "PIN / Codigo de acceso",
                type="password",
                max_chars=8,
                placeholder="PIN",
            )
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if _authenticate(user, password, users):
                st.success(f"Bienvenido, {user}")
                st.rerun()
            st.error("Usuario o codigo/PIN incorrecto")

        st.markdown(
            "<div class='auth-footnote'>Los entrenadores retirados pueden entrar en modo consulta.</div>",
            unsafe_allow_html=True,
        )

    st.stop()
