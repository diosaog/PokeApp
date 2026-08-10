from __future__ import annotations

from html import escape
import os

import streamlit as st

from app.interfaz.media import image_data_uri

_SECTION_META = {
    "Inicio": ("home", "Centro"),
    "Team Preview": ("swords", "Combates"),
    "Normativa": ("file_text", "Reglas"),
    "Liga y Tabla": ("trophy", "Clasificacion"),
    "Hall of Fame": ("crown", "Historico"),
    "Temporada": ("shield", "Admin"),
    "Previa Combate": ("swords", "Duelo"),
    "Entrenadores": ("users", "Equipos"),
    "Copa": ("medal", "Torneos"),
    "Juicios": ("gavel", "Sanciones"),
    "Tienda": ("shopping_bag", "Compras"),
    "Saves": ("database", "Archivos"),
}

_NAV_GROUPS = (
    ("Competicion", ("Inicio", "Liga y Tabla", "Team Preview", "Copa")),
    ("Entrenador", ("Entrenadores", "Tienda", "Saves")),
    ("Informacion", ("Normativa", "Hall of Fame")),
    ("Admin", ("Temporada", "Juicios")),
)

_MATERIAL_ICONS = {
    "home": ":material/home:",
    "trophy": ":material/emoji_events:",
    "swords": ":material/swords:",
    "medal": ":material/workspace_premium:",
    "users": ":material/groups:",
    "shopping_bag": ":material/shopping_bag:",
    "database": ":material/storage:",
    "file_text": ":material/menu_book:",
    "crown": ":material/military_tech:",
    "gavel": ":material/gavel:",
    "shield": ":material/tune:",
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


def _render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class='sidebar-brand'>
          <div class='sidebar-brand-mark' aria-hidden='true'>
            <span></span>
          </div>
          <div>
            <div class='sidebar-brand-name'>PokeApp</div>
            <div class='sidebar-brand-sub'>League</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _division_label(user: str) -> str:
    try:
        from app.interfaz.notifications import league_state_snapshot

        league = league_state_snapshot()
        if user in (league.get("division_a") or []):
            return "Division A"
        if user in (league.get("division_b") or []):
            return "Division B"
    except Exception:
        pass
    return "Liga"


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
    retired = is_trainer_retired(user)
    status = "Consulta" if retired else "Activo"
    context = f"{_division_label(user)} - {status}"

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
              <div class='profile-sub'>{escape(context)}</div>
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
            label="Notificaciones",
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

    with st.sidebar.expander("Cambiar PIN", expanded=False):
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
          margin: 16px 0 8px;
          padding: 0 4px;
          color: var(--text-muted, #6f7b8f);
          font-size: 11px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] {
          display: grid;
          gap: 4px;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
          position: relative;
          overflow: hidden;
          width: 100%;
          min-height: 42px;
          padding: 9px 10px 9px 12px;
          border: 1px solid transparent;
          border-radius: var(--radius-input, 10px);
          background: transparent;
          box-shadow: none;
          transition: transform .12s ease, background-color .12s ease, border-color .12s ease;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
          display: none;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
          border-color: rgba(77,141,255,0.3);
          background: var(--primary-soft, rgba(77,141,255,0.12));
          box-shadow: inset 3px 0 0 var(--primary, #4d8dff);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label p {
          margin: 0 !important;
          color: var(--text-secondary, #aab4c5) !important;
          font-family: var(--font-ui) !important;
          font-size: 13px !important;
          font-weight: 700 !important;
          line-height: 1.15;
          text-transform: none;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
          color: var(--text-primary, #f5f7fa) !important;
          font-weight: 800 !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
          display: none;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
          border-color: var(--border-soft, rgba(255,255,255,0.06));
          background: rgba(255,255,255,0.045);
          transform: translateY(-1px);
        }
        section[data-testid="stSidebar"] div.stButton > button {
          width: 100%;
          min-height: 42px;
          margin-bottom: 5px;
          justify-content: flex-start;
          text-align: left;
          gap: 10px;
          border: 1px solid var(--border-soft, rgba(255,255,255,0.06));
          border-radius: var(--radius-input, 10px);
          background: var(--surface-2, #172033);
          box-shadow: none;
        }
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
          border-color: rgba(77,141,255,0.3);
          background: var(--primary-soft, rgba(77,141,255,0.12));
        }
        section[data-testid="stSidebar"] div.stButton > button p {
          color: var(--text-primary, #f5f7fa) !important;
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
    for group_title, group_sections in _NAV_GROUPS:
        visible = [section for section in group_sections if section in nav_sections]
        if not visible:
            continue
        st.sidebar.markdown(
            f"<div class='sidebar-nav-title'>{escape(group_title)}</div>",
            unsafe_allow_html=True,
        )
        for section in group_sections:
            if section not in nav_sections:
                continue
            icon, _help = _SECTION_META.get(section, ("home", section))
            display = "Liga" if section == "Liga y Tabla" else section
            if st.sidebar.button(
                display,
                key=f"sidebar_nav_{section}",
                type="primary" if section == selected else "secondary",
                icon=_MATERIAL_ICONS.get(icon),
                use_container_width=True,
            ):
                st.session_state["selected_section"] = section
                st.session_state["selected_section_radio"] = section
                st.rerun()
    return str(st.session_state["selected_section"])


def render_sidebar(sections: list[str]) -> str:
    _render_sidebar_brand()
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
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()
    return section
