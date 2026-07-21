from __future__ import annotations

from html import escape
import os

import streamlit as st

from app.interfaz.media import image_data_uri

_SECTION_META = {
    "Inicio": ("\U0001f3e0", "Centro"),
    "Team Preview": ("\u2694\ufe0f", "Combates"),
    "Normativa": ("\U0001f4dc", "Reglas"),
    "Liga y Tabla": ("\U0001f3c6", "Clasificacion"),
    "Hall of Fame": ("\U0001f3db\ufe0f", "Historico"),
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
    portrait = image_data_uri(str(image_path or ""), mtime, min_bytes=256)
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


def _render_sidebar_notifications() -> None:
    user = str(st.session_state.get("user") or "").strip()
    if not user or user == "-":
        return
    try:
        from app.interfaz.notifications import (
            collect_notifications,
            render_notifications_popover,
        )

        render_notifications_popover(
            collect_notifications(user=user),
            container=st.sidebar,
            label="\U0001f514 Notificaciones",
            use_container_width=True,
        )
    except Exception:
        pass


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
          padding: 9px 12px;
          border: 1px solid rgba(238,233,255,0.38);
          border-radius: 999px;
          background:
            linear-gradient(90deg, rgba(255,255,255,0.18), transparent 72%),
            linear-gradient(180deg, var(--accent), var(--accent-dark));
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.24), 0 10px 22px rgba(18,14,54,0.2);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] {
          display: grid;
          gap: 8px;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
          position: relative;
          overflow: hidden;
          width: 100%;
          min-height: 52px;
          padding: 0.64rem 0.95rem 0.64rem 1.14rem;
          border: 1px solid rgba(238,233,255,0.3);
          border-radius: 14px;
          background:
            linear-gradient(136deg, transparent 0 70%, rgba(255,117,221,0.18) 70% 82%, rgba(69,209,255,0.18) 82% 100%),
            linear-gradient(180deg, rgba(222,216,248,0.96), rgba(199,192,230,0.95));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.46), 0 9px 20px rgba(18,14,54,0.18);
          transition: transform .12s ease, filter .12s ease, border-color .12s ease;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
          content: "";
          position: absolute;
          left: 10px;
          top: 50%;
          width: 12px;
          height: 12px;
          transform: translateY(-50%);
          border-radius: 50%;
          background: #202436;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
          border-color: rgba(246,216,59,0.9);
          background:
            linear-gradient(136deg, transparent 0 68%, rgba(255,255,255,0.22) 68% 100%),
            linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.48), 0 0 0 3px rgba(246,216,59,0.16), 0 12px 24px rgba(18,14,54,0.24);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
          background:
            radial-gradient(circle at 50% 50%, #f8fbff 0 25%, transparent 26%),
            linear-gradient(#ef3f56 0 48%, #202436 48% 54%, #f8fbff 54% 100%);
          border: 1px solid #202436;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label p {
          margin-left: 20px !important;
          color: var(--champ-text) !important;
          font-family: var(--font-ui) !important;
          font-size: 12px !important;
          font-weight: 800 !important;
          line-height: 1.18;
          text-transform: uppercase;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
          filter: brightness(1.06);
          transform: translateY(-1px);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
          display: none;
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
          border-color: rgba(238,233,255,0.3);
          border-radius: 14px;
          background:
            linear-gradient(136deg, transparent 0 70%, rgba(255,117,221,0.18) 70% 82%, rgba(69,209,255,0.18) 82% 100%),
            linear-gradient(180deg, rgba(222,216,248,0.96), rgba(199,192,230,0.95));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.46), 0 9px 20px rgba(18,14,54,0.18);
        }
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
          border-color: rgba(246,216,59,0.9);
          background:
            linear-gradient(136deg, transparent 0 68%, rgba(255,255,255,0.22) 68% 100%),
            linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2));
        }
        section[data-testid="stSidebar"] div.stButton > button p {
          color: var(--champ-text) !important;
          font-size: 12px;
          font-weight: 800;
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
    _render_sidebar_notifications()
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
