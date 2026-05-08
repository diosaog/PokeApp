from __future__ import annotations

import base64
import mimetypes
import os
import streamlit as st


def _cache_data(ttl: int = 30):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


@_cache_data(ttl=60)
def _img_uri(p: str, mtime: float | None = None) -> str:
    try:
        if not p:
            return ""
        mt = mimetypes.guess_type(p)[0] or "image/png"
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        uri = f"data:{mt};base64,{b64}"
        return uri
    except Exception:
        return ""


@_cache_data(ttl=30)
def _get_team_sprite_urls(user: str, mtime: float | None = None) -> list[str]:
    urls: list[str] = []
    try:
        if not user or user == "-":
            return urls
        from app.entrenadores.snapshot import get_trainer_snapshot
        from showdown_sprites import showdown_sprite_url

        snapshot = get_trainer_snapshot(user)
        mons = list(snapshot.get("team") or [])
        prefer_anim = False
        for m in mons[:6]:
            try:
                sp = m.get("species_name") or m.get("species") or "?"
                url = showdown_sprite_url(
                    species_name=str(sp),
                    form_index=m.get("form_index"),
                    form_name=m.get("form_name"),
                    is_shiny=bool(m.get("is_shiny")),
                    gender=m.get("gender"),
                    prefer_animated=prefer_anim,
                )
                urls.append(url)
            except Exception:
                continue
    except Exception:
        pass
    return urls


@_cache_data(ttl=30)
def _get_badges_count(user: str, mtime: float | None = None) -> int:
    try:
        if not user or user == "-":
            return 0
        from app.entrenadores.snapshot import get_trainer_snapshot

        snapshot = get_trainer_snapshot(user)
        return int(snapshot.get("badge_count") or 0)
    except Exception:
        return 0


def _render_sidebar_profile() -> None:
    usr = st.session_state.get("user") or ""
    if not usr or usr == "-":
        return
    from app.entrenadores.profile import find_trainer_image

    img = find_trainer_image(usr)
    mtime = None
    try:
        if img:
            mtime = os.path.getmtime(img)
    except Exception:
        mtime = None
    team_urls = _get_team_sprite_urls(usr, mtime)
    badges = max(0, min(8, _get_badges_count(usr, mtime)))
    dots = "".join([f"<span class='badge-dot{' badge-on' if i < badges else ''}'></span>" for i in range(8)])
    badges_html = f"<div class='badges-row'>{dots}</div>"
    if team_urls:
        team_html = "".join([f"<span class='mini-mon'><img src='{u}' alt='pkm'/></span>" for u in team_urls])
        bottom = badges_html + f"<div class='mini-team'>{team_html}</div>"
    else:
        bottom = badges_html + "<div class='mini-team'>" + ("<span class='mini-mon'><div class='pokeball-mini'></div></span>" * 6) + "</div>"

    html = f"""
    <div class='profile-card'>
      <div class='profile-head'>
        <div class='profile-avatar'>
          {f"<img src='{_img_uri(img, mtime)}' alt='trainer'/>" if img else "<div class='pokeball-mini'></div>"}
          <div class='glint'></div>
        </div>
        <div class='profile-meta'>
          <div class='profile-name'>{usr}</div>
          <div class='profile-sub'>Entrenador activo</div>
        </div>
      </div>
      {bottom}
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)


def _render_change_pin_form() -> None:
    usr = st.session_state.get("user") or ""
    if not usr or usr == "-":
        return
    from storage import settings_get, settings_set

    with st.sidebar.expander("Cambiar PIN (4 digitos)", expanded=False):
        def _get_pin(u: str) -> str | None:
            try:
                val = settings_get(f"pin:{u}")
                if val and len(str(val).strip()) == 4 and str(val).strip().isdigit():
                    return str(val).strip()
            except Exception:
                return None
            return None

        current_pin = _get_pin(usr)
        cur_in = st.text_input("PIN actual", type="password", max_chars=4, value="") if current_pin else None
        new_in = st.text_input("PIN nuevo (4 digitos)", type="password", max_chars=4, value="")
        if st.button("Guardar PIN", use_container_width=True):
            if current_pin:
                if not cur_in or cur_in.strip() != current_pin:
                    st.error("PIN actual incorrecto.")
                    return
            if not new_in or len(new_in.strip()) != 4 or (not new_in.strip().isdigit()):
                st.error("El PIN debe tener 4 digitos.")
                return
            try:
                settings_set(f"pin:{usr}", new_in.strip())
                st.success("PIN actualizado.")
            except Exception as e:
                st.error(f"No se pudo guardar el PIN: {e}")


def render_sidebar(sections: list[str]) -> str:
    _render_sidebar_profile()
    _render_change_pin_form()
    st.sidebar.markdown("---")
    section = st.sidebar.selectbox("Seccion", sections, index=0)
    from app.interfaz.theme import apply_section_theme
    apply_section_theme(section)
    st.sidebar.markdown("---")
    return section
