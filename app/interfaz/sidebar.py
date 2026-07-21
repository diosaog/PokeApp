from __future__ import annotations

import base64
from html import escape
import mimetypes
import os

import streamlit as st

_SECTION_META = {
    "Inicio": ("\U0001f3e0", "Centro"),
    "Team Preview": ("\u2694\ufe0f", "Combates"),
    "Normativa": ("\U0001f4dc", "Reglas"),
    "Liga y Tabla": ("\U0001f3c6", "Clasificacion"),
    "Temporada": ("\U0001f6e1\ufe0f", "Admin"),
    "Previa Combate": ("\u2694\ufe0f", "Duelo"),
    "Entrenadores": ("\U0001f392", "Equipos"),
    "Copa": ("\U0001f947", "Torneos"),
    "Juicios": ("\u2696\ufe0f", "Sanciones"),
    "Tienda": ("\U0001f6d2", "Compras"),
    "Saves": ("\U0001f4be", "Archivos"),
}


def _cache_data(ttl: int = 30):
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
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{media_type};base64,{encoded}"
    except Exception:
        return ""


@_cache_data(ttl=30)
def _get_team_sprite_urls(user: str, mtime: float | None = None) -> list[str]:
    _ = mtime
    urls: list[str] = []
    try:
        if not user or user == "-":
            return urls
        from app.entrenadores.snapshot import get_trainer_snapshot
        from showdown_sprites import showdown_sprite_url

        snapshot = get_trainer_snapshot(user)
        mons = list(snapshot.get("team") or [])
        for mon in mons[:6]:
            try:
                species = mon.get("species_name") or mon.get("species") or "?"
                urls.append(
                    showdown_sprite_url(
                        species_name=str(species),
                        form_index=mon.get("form_index"),
                        form_name=mon.get("form_name"),
                        is_shiny=bool(mon.get("is_shiny")),
                        gender=mon.get("gender"),
                        prefer_animated=False,
                    )
                )
            except Exception:
                continue
    except Exception:
        pass
    return urls


@_cache_data(ttl=30)
def _get_badges_count(user: str, mtime: float | None = None) -> int:
    _ = mtime
    try:
        if not user or user == "-":
            return 0
        from app.entrenadores.snapshot import get_trainer_snapshot

        snapshot = get_trainer_snapshot(user)
        return int(snapshot.get("badge_count") or 0)
    except Exception:
        return 0


def _render_sidebar_profile() -> None:
    user = str(st.session_state.get("user") or "")
    if not user or user == "-":
        return

    from app.entrenadores.profile import find_trainer_image
    from app.entrenadores.trainer_flags import is_trainer_retired

    image_path = find_trainer_image(user)
    try:
        mtime = os.path.getmtime(image_path) if image_path else None
    except Exception:
        mtime = None

    team_urls = _get_team_sprite_urls(user, mtime)
    badges = max(0, min(8, _get_badges_count(user, mtime)))
    badge_dots = "".join(
        f"<span class='badge-dot{' badge-on' if index < badges else ''}'></span>"
        for index in range(8)
    )
    badges_html = f"<div class='badges-row'>{badge_dots}</div>"
    if team_urls:
        team_html = "".join(
            f"<span class='mini-mon'><img src='{escape(url)}' alt='pkm'/></span>"
            for url in team_urls
        )
    else:
        team_html = "<span class='mini-mon'><div class='pokeball-mini'></div></span>" * 6
    portrait = _img_uri(str(image_path or ""), mtime)
    avatar = (
        f"<img src='{portrait}' alt='Retrato de {escape(user)}'/>"
        if portrait
        else "<div class='pokeball-mini'></div>"
    )
    status = "Modo consulta" if is_trainer_retired(user) else "Entrenador activo"

    st.sidebar.markdown(
        f"""
        <div class='profile-card'>
          <div class='profile-head'>
            <div class='profile-avatar'>
              {avatar}
              <div class='glint'></div>
            </div>
            <div class='profile-meta'>
              <div class='profile-name'>{escape(user)}</div>
              <div class='profile-sub'>{escape(status)}</div>
            </div>
          </div>
          {badges_html}
          <div class='mini-team'>{team_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_change_pin_form() -> None:
    user = str(st.session_state.get("user") or "")
    if not user or user == "-":
        return

    from storage import settings_get, settings_set

    def _get_pin(name: str) -> str | None:
        try:
            value = settings_get(f"pin:{name}")
            pin = str(value or "").strip()
            if len(pin) == 4 and pin.isdigit():
                return pin
        except Exception:
            return None
        return None

    with st.sidebar.expander("Cambiar PIN (4 digitos)", expanded=False):
        current_pin = _get_pin(user)
        current_input = (
            st.text_input("PIN actual", type="password", max_chars=4, value="")
            if current_pin
            else None
        )
        new_input = st.text_input(
            "PIN nuevo (4 digitos)",
            type="password",
            max_chars=4,
            value="",
        )
        if st.button("Guardar PIN", use_container_width=True):
            if current_pin and (not current_input or current_input.strip() != current_pin):
                st.error("PIN actual incorrecto.")
                return
            new_pin = str(new_input or "").strip()
            if len(new_pin) != 4 or not new_pin.isdigit():
                st.error("El PIN debe tener 4 digitos.")
                return
            try:
                settings_set(f"pin:{user}", new_pin)
                st.success("PIN actualizado.")
            except Exception as exc:
                st.error(f"No se pudo guardar el PIN: {exc}")


def _normalize_section(section: str | None) -> str:
    if section == "Previa Combate":
        return "Team Preview"
    return str(section or "Inicio")


def _normalized_sections(sections: list[str]) -> list[str]:
    out: list[str] = []
    for section in sections:
        normalized = _normalize_section(section)
        if normalized not in out:
            out.append(normalized)
    return out or ["Inicio"]


def _render_nav_css() -> None:
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] .sidebar-nav-title {
          margin: 0 0 8px;
          padding: 7px 9px;
          border: 1px solid rgba(216,223,232,0.14);
          background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] {
          display: grid;
          gap: 5px;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
          width: 100%;
          min-height: 46px;
          padding: 0.58rem 0.72rem;
          border: 1px solid rgba(216,223,232,0.34);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.07), transparent 58%),
            linear-gradient(180deg, #252a33 0%, #151a22 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 4px 10px rgba(0,0,0,0.22);
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
          border-color: var(--bw2-edge-strong);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.16), transparent 58%),
            linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label p {
          color: #fff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.18;
          text-transform: uppercase;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
          filter: brightness(1.06);
          transform: translateY(-1px);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
          margin-right: 8px;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) > div:first-child {
          color: #ffffff;
        }
        section[data-testid="stSidebar"] div.stButton > button {
          width: 100%;
          justify-content: flex-start;
          text-align: left;
          min-height: 46px;
          margin-bottom: 5px;
          padding-left: 0.85rem;
          border-color: rgba(216,223,232,0.34);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.07), transparent 58%),
            linear-gradient(180deg, #252a33 0%, #151a22 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 4px 10px rgba(0,0,0,0.22);
        }
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
          border-color: var(--bw2-edge-strong);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.16), transparent 58%),
            linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
        }
        section[data-testid="stSidebar"] div.stButton > button p {
          font-size: 10px;
          line-height: 1.15;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_section_nav(sections: list[str]) -> str:
    nav_sections = _normalized_sections(sections)
    selected = _normalize_section(st.session_state.get("selected_section") or nav_sections[0])
    if selected not in nav_sections:
        selected = nav_sections[0]
    st.session_state["selected_section"] = selected
    if _normalize_section(st.session_state.get("selected_section_radio")) not in nav_sections:
        st.session_state["selected_section_radio"] = selected

    _render_nav_css()
    st.sidebar.markdown("<div class='sidebar-nav-title'>Menu principal</div>", unsafe_allow_html=True)

    def _label(section: str) -> str:
        icon, help_text = _SECTION_META.get(section, ("\u25c8", section))
        return f"{icon} {section} - {help_text}"

    choice = st.sidebar.radio(
        "Menu principal",
        nav_sections,
        index=nav_sections.index(selected),
        format_func=_label,
        key="selected_section_radio",
        label_visibility="collapsed",
    )
    st.session_state["selected_section"] = _normalize_section(choice)
    return str(st.session_state["selected_section"])


def render_sidebar(sections: list[str]) -> str:
    _render_sidebar_profile()
    _render_change_pin_form()
    st.sidebar.markdown("---")
    section = _render_section_nav(sections)
    from app.interfaz.theme import apply_section_theme

    apply_section_theme(section)
    st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar sesion", use_container_width=True, key="logout_button"):
        st.session_state.auth_ok = False
        st.session_state.user = None
        st.session_state.selected_section = "Inicio"
        st.session_state.selected_section_radio = "Inicio"
        st.rerun()
    return section
