# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List
from pathlib import Path

import streamlit as st

from utils import USERS, list_user_saves, DEFAULT_DLL_HINT
from showdown_sprites import showdown_sprite_url
from conex_pkhex import PKHeXRuntime, extract_team, get_bridge_path
from storage import init_storage


def apply_css() -> None:
    css = """
    <style>
    :root {
      --accent: #ef5350; /* rojo Pokemon */
      --accent-hover: #d32f2f;
      --text-1: #e6edf3;
      --text-2: #c9d1d9;
    }
    .main { position: relative; }
    .main:before {
      content: "";
      position: fixed; inset: 0; z-index: -1; pointer-events: none;
      background:
        radial-gradient(circle at 18% 22%, rgba(255,255,255,0.06) 0 64px, transparent 65px),
        radial-gradient(circle at 18% 22%, rgba(239,83,80,0.10) 0 36px, transparent 37px),
        linear-gradient(0deg, rgba(239,83,80,0.08) 0 12px, transparent 13px) 18% 22%/128px 128px no-repeat,
        radial-gradient(circle at 80% 78%, rgba(255,255,255,0.06) 0 74px, transparent 75px),
        radial-gradient(circle at 80% 78%, rgba(239,83,80,0.10) 0 42px, transparent 43px),
        linear-gradient(0deg, rgba(239,83,80,0.08) 0 12px, transparent 13px) 80% 78%/148px 148px no-repeat,
        radial-gradient(circle at 20% 15%, rgba(255,255,255,0.045) 0 25px, transparent 26px) 0 0/120px 120px,
        radial-gradient(circle at 80% 85%, rgba(255,255,255,0.045) 0 25px, transparent 26px) 0 0/140px 140px,
        /* Pokeball watermark bottom-right (usa color variable) */
        radial-gradient(circle at calc(100% - 180px) calc(100% - 180px), color-mix(in srgb, var(--ball-color, #ffffff) 80%, transparent) 0 10px, transparent 11px) 100% 100%/360px 360px no-repeat,
        linear-gradient(0deg, color-mix(in srgb, var(--ball-color, #ffffff) 35%, transparent) 0 50%, rgba(10,13,18,0.8) 50% 100%) calc(100% - 180px) calc(100% - 180px)/360px 360px no-repeat,
        radial-gradient(circle at calc(100% - 180px) calc(100% - 220px), color-mix(in srgb, var(--ball-color, #ffffff) 45%, transparent) 0 140px, transparent 141px) 100% 100%/360px 360px no-repeat,
        linear-gradient(180deg, #0a0d12 0%, #0a0d12 60%, #090c10 100%);
    }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; border-radius: 18px; animation: fadeInUp .35s ease-out both; }
    @keyframes fadeInUp { from { opacity:0; transform: translate3d(0,8px,0);} to { opacity:1; transform: translate3d(0,0,0);} }
    h1,h2,h3,h4,h5,h6 { color: var(--text-1); }
    p,span,div,label { color: var(--text-2); }
    section[data-testid="stSidebar"] { background: rgba(16,19,26,0.9); backdrop-filter: blur(6px); border-right: 1px solid rgba(255,255,255,0.06); }
    hr { border-top: 1px solid rgba(255,255,255,0.08); }
    .stButton>button, .stDownloadButton>button { border-radius: 16px; padding: 0.6rem 1rem; min-height: 40px; background: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 80%, #7f1d1d)); border: 1px solid rgba(255,255,255,0.12); color: #fff; box-shadow: 0 6px 18px rgba(239,83,80,.18); }
    .stButton>button:focus-visible { outline: 2px solid #90caf9; outline-offset: 2px; }

    /* Slots de equipo/PC (sin animaciones) */
    .slot { background: rgba(255,255,255,0.02); border: 2px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 10px 10px 8px; text-align:center; margin: 6px 0 16px; box-shadow: inset 0 0 0 2px rgba(255,255,255,0.03); }
    .slot:hover { box-shadow: inset 0 0 0 2px rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.25); }
    .slot .title { font-weight: 600; color: #e6edf3; margin-top: 6px; }
    .slot .sub { color: #9aa3ab; font-size: 0.82rem; }
    .slot { cursor: default; }
    .slot-empty { border: 2px dashed rgba(255,255,255,0.20); background: transparent; height: 120px; display:flex; align-items:center; justify-content:center; color:#8a919a; border-radius:16px; }

    /* Tarjeta Pokedex */
    .pokedex-card { border-radius: 16px; background: linear-gradient(180deg, rgba(42,117,187,0.12), rgba(10,13,18,0.6)); padding: 12px 14px; box-shadow: 0 6px 16px rgba(0,0,0,0.25), inset 0 0 0 3px rgba(255,255,255,0.05); }
    .pokedex-card .title { font-family: "Press Start 2P", monospace; font-size: 0.9rem; color: #e6edf3; }
    .pokedex-card .meta  { color: #9aa3ab; font-size: 0.85rem; }

    /* Separador Pokeball */
    .poke-sep { position: relative; height: 1px; background: rgba(255,255,255,0.12); margin: 18px 0; }
    .poke-sep::after { content:""; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:28px; height:28px; border-radius:50%;
      background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.85) 0 3px, transparent 4px), linear-gradient(0deg, rgba(255,255,255,0.9) 0 50%, rgba(10,13,18,0.9) 50% 100%);
      box-shadow: 0 0 0 2px rgba(255,255,255,0.12), 0 2px 8px rgba(0,0,0,0.25);
    }
    \n    .status-badge { display:inline-block; padding:2px 10px; border-radius:999px; font-weight:700; font-size:0.8rem; margin-left:8px; }\n    .status-ok { background:#1b5e20; color:#e8f5e9; border:1px solid rgba(255,255,255,0.15);}\n    .status-warn { background:#7f1d1d; color:#ffebee; border:1px solid rgba(255,255,255,0.15);}\n
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    # Estado base (sin sonidos/animaciones opcionales)

    # CSS extra: tarjeta de perfil, medallas y pokeball mini
    st.markdown(
        """
        <style>
        .profile-card { border-radius: 16px; padding: 12px; background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)); border: 1px solid rgba(255,255,255,0.08); box-shadow: inset 0 0 0 2px rgba(255,255,255,0.03); }
        .profile-head { display:flex; align-items:center; gap:12px; }
        .profile-avatar { width:64px; height:64px; border-radius:50%; overflow:hidden; flex:0 0 auto; box-shadow: 0 4px 10px rgba(0,0,0,0.35), 0 0 0 3px rgba(255,255,255,0.06); position:relative; }
        .profile-avatar img { width:100%; height:100%; object-fit:cover; display:block; filter: saturate(1.08); }
        .glint { position:absolute; inset:0; pointer-events:none; background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.55) 12%, transparent 24%); transform: translateX(-120%); animation: glint 5s linear infinite; }
        @keyframes glint { 0% { transform: translateX(-120%);} 100% { transform: translateX(120%);} }
        .profile-meta { line-height:1.2; }
        .profile-name { font-weight:700; color:#e6edf3; }
        .profile-sub { color:#9aa3ab; font-size: 0.85rem; }
        .badges-row { display:flex; gap:6px; align-items:center; margin-top:10px; flex-wrap:wrap; }
        .badge-ico { width:20px; height:20px; border-radius:4px; background:rgba(255,255,255,0.06); display:inline-flex; align-items:center; justify-content:center; overflow:hidden; box-shadow: 0 1px 0 rgba(0,0,0,0.25); }
        .badge-ico img { width:100%; height:100%; object-fit:contain; filter: drop-shadow(0 0 2px rgba(0,0,0,0.35)); }
        .badge-off img { filter: grayscale(1) opacity(0.35) drop-shadow(0 0 0 rgba(0,0,0,0)); }
        .badge-dot { width:12px; height:12px; border-radius:50%; display:inline-block; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.35); background: rgba(255,255,255,0.12); }
        .badge-on { background: color-mix(in srgb, var(--accent, #ef5350) 75%, #ffffff); }
        .pokeball-mini { width:16px; height:16px; border-radius:50%; position:relative; display:inline-block; background: linear-gradient(180deg, #fff 0 49%, #e11 51% 100%); border:2px solid #111; box-shadow: inset 0 0 0 2px #111; animation: spin 4s linear infinite; }
        .pokeball-mini::after { content:""; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:6px; height:6px; border-radius:50%; background:#fff; border:2px solid #111; box-shadow: 0 0 0 1px rgba(0,0,0,0.35); }
        @keyframes spin { 0% { transform: rotate(0deg);} 100% { transform: rotate(360deg);} }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # CSS mini team row
    st.markdown(
        """
        <style>
        .mini-team { display:flex; gap:6px; align-items:center; margin-top:10px; flex-wrap:wrap; }
        .mini-mon { width:28px; height:28px; border-radius:6px; background:rgba(255,255,255,0.06); display:inline-flex; align-items:center; justify-content:center; overflow:hidden; box-shadow: 0 1px 0 rgba(0,0,0,0.25); }
        .mini-mon img { width:100%; height:100%; object-fit:contain; image-rendering: -webkit-optimize-contrast; filter: drop-shadow(0 0 2px rgba(0,0,0,0.35)); }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Filtro global: mostrar texto sin acentos y limpia mojibake comun
    try:
        import unicodedata

        def _strip_accents(s: str) -> str:
            try:
                t = str(s)
                # Fix mojibake (UTF-8 visto como latin1)
                repl = {
                    '\u00c3\u00a1': 'a', '\u00c3\u00a9': 'e', '\u00c3\u00ad': 'i', '\u00c3\u00b3': 'o', '\u00c3\u00ba': 'u',
                    '\u00c3\u00b1': 'n', '\u00c3\u0081': 'A', '\u00c3\u0089': 'E', '\u00c3\u008d': 'I', '\u00c3\u0093': 'O', '\u00c3\u009a': 'U', '\u00c3\u0091': 'N',
                    'Pok\u00c3\u00a9mon': 'Pokemon',
                }
                for a, b in repl.items():
                    t = t.replace(a, b)
                # Quitar diacriticos restantes
                t = unicodedata.normalize('NFD', t)
                t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
                # Normalizar comillas y guiones
                sym = {
                    '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2014': '-', '\u2013': '-', '\u2022': '-', '\u2026': '...',
                    '\u00ba': 'o', '\u00aa': 'a', '\u00bf': '?', '\u00a1': '!', '\u00a9': '(c)'
                }
                for a, b in sym.items():
                    t = t.replace(a, b)
                return t
            except Exception:
                return str(s)

        def _install_ascii_ui():
            if getattr(st, "_ascii_ui", False):
                return

            def _wrap_label(orig):
                def _f(*args, **kwargs):
                    if args and isinstance(args[0], str):
                        args = list(args)
                        args[0] = _strip_accents(args[0])
                    if 'help' in kwargs and isinstance(kwargs['help'], str):
                        kwargs['help'] = _strip_accents(kwargs['help'])
                    return orig(*args, **kwargs)
                return _f

            def _wrap_selectlike(orig):
                def _f(*args, **kwargs):
                    if args and isinstance(args[0], str):
                        args = list(args)
                        args[0] = _strip_accents(args[0])
                    if kwargs.get('format_func') is None:
                        kwargs['format_func'] = _strip_accents
                    return orig(*args, **kwargs)
                return _f

            def _wrap_write(orig):
                def _f(*args, **kwargs):
                    if args and isinstance(args[0], str):
                        args = list(args)
                        args[0] = _strip_accents(args[0])
                    if 'help' in kwargs and isinstance(kwargs['help'], str):
                        kwargs['help'] = _strip_accents(kwargs['help'])
                    return orig(*args, **kwargs)
                return _f

            def _wrap_dataframe(orig):
                def _f(data, *args, **kwargs):
                    try:
                        if isinstance(data, list) and data and isinstance(data[0], dict):
                            data = [{_strip_accents(k): (_strip_accents(v) if isinstance(v, str) else v) for k, v in row.items()} for row in data]
                        elif isinstance(data, dict):
                            data = {_strip_accents(k): (_strip_accents(v) if isinstance(v, str) else v) for k, v in data.items()}
                    except Exception:
                        pass
                    return orig(data, *args, **kwargs)
                return _f

            try:
                from streamlit.delta_generator import DeltaGenerator as _DG  # type: ignore
            except Exception:
                _DG = None  # type: ignore

            _label_funcs = [
                'header', 'subheader', 'title', 'markdown', 'caption', 'text',
                'success', 'error', 'warning', 'info', 'toast', 'button',
                'download_button', 'text_input', 'file_uploader', 'number_input',
                'toggle', 'checkbox', 'text_area', 'code', 'json', 'table', 'data_editor'
            ]
            _selectlike = ['selectbox', 'radio', 'multiselect', 'select_slider']

            if hasattr(st, 'write'):
                st.write = _wrap_write(st.write)
            for _n in _label_funcs:
                if hasattr(st, _n):
                    setattr(st, _n, _wrap_label(getattr(st, _n)))
            for _n in _selectlike:
                if hasattr(st, _n):
                    setattr(st, _n, _wrap_selectlike(getattr(st, _n)))
            if hasattr(st, 'dataframe'):
                st.dataframe = _wrap_dataframe(st.dataframe)

            if _DG is not None:
                if hasattr(_DG, 'write'):
                    setattr(_DG, 'write', _wrap_write(getattr(_DG, 'write')))
                for _n in _label_funcs:
                    if hasattr(_DG, _n):
                        setattr(_DG, _n, _wrap_label(getattr(_DG, _n)))
                for _n in _selectlike:
                    if hasattr(_DG, _n):
                        setattr(_DG, _n, _wrap_selectlike(getattr(_DG, _n)))
                if hasattr(_DG, 'dataframe'):
                    setattr(_DG, 'dataframe', _wrap_dataframe(getattr(_DG, 'dataframe')))

            st._ascii_ui = True
            st._ascii_ui_strip = _strip_accents

        _install_ascii_ui()
    except Exception:
        pass

# (se removieron sonidos/animaciones opcionales)


def render_poke_separator() -> None:
    st.markdown("<div class='poke-sep'></div>", unsafe_allow_html=True)


# --- Sidebar profile helpers ---
def _find_trainer_image_local(trainer: str) -> str:
    try:
        pdir = Path('assets') / 'trainers'
        if not pdir.exists():
            return ''
        bases = [trainer, trainer.lower(), trainer.capitalize(), trainer.replace(' ', '_'), trainer.replace(' ', '-')]
        exts = ['.png','.jpg','.jpeg','.webp']
        for b in bases:
            for e in exts:
                f = pdir / f"{b}{e}"
                if f.exists():
                    return str(f)
    except Exception:
        return ''
    return ''


def _get_team_sprite_urls(user: str) -> list[str]:
    urls: list[str] = []
    try:
        if not user or user == '-':
            return urls
        # Asegurar bridge cargado (intento rápido)
        if not get_bridge_path():
            try:
                import entrenadores as _ent
                if hasattr(_ent, '_try_auto_load_bridge'):
                    _ent._try_auto_load_bridge()
            except Exception:
                pass
        if not get_bridge_path():
            # último intento con pista por defecto o ruta ya guardada
            try:
                hint = st.session_state.get('pkhex_dll_path') or DEFAULT_DLL_HINT
                if hint:
                    PKHeXRuntime.load(hint)
            except Exception:
                return urls
        saves = list_user_saves(user)
        if not saves:
            return urls
        sav_path = str(saves[0])
        sav_json = PKHeXRuntime.open_sav(sav_path)
        mons = extract_team(sav_json, save_path=sav_path) or []
        prefer_anim = False  # sin animaciones en la tarjeta
        for m in mons[:6]:
            try:
                sp = m.get('species_name') or m.get('species') or '?'
                url = showdown_sprite_url(
                    species_name=str(sp),
                    form_index=m.get('form_index'),
                    form_name=m.get('form_name'),
                    is_shiny=bool(m.get('is_shiny')),
                    gender=m.get('gender'),
                    prefer_animated=prefer_anim,
                )
                urls.append(url)
            except Exception:
                continue
    except Exception:
        pass
    return urls


def _get_badges_count(user: str) -> int:
    try:
        if not user or user == '-':
            return 0
        if not get_bridge_path():
            try:
                import entrenadores as _ent
                if hasattr(_ent, '_try_auto_load_bridge'):
                    _ent._try_auto_load_bridge()
            except Exception:
                pass
        saves = list_user_saves(user)
        if not saves:
            return 0
        sav_path = str(saves[0])
        sav_json = PKHeXRuntime.open_sav(sav_path)
        return int(coins_from_badges(sav_json))
    except Exception:
        return 0


def _render_sidebar_profile() -> None:
    usr = st.session_state.get('user') or ''
    if not usr or usr == '-':
        return
    img = _find_trainer_image_local(usr)
    def _img_uri(p: str) -> str:
        try:
            if not p:
                return ''
            import base64, mimetypes
            mt = mimetypes.guess_type(p)[0] or 'image/png'
            with open(p, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            return f"data:{mt};base64,{b64}"
        except Exception:
            return ''
    team_urls = _get_team_sprite_urls(usr)
    badges = max(0, min(8, _get_badges_count(usr)))
    # medallas: 8 puntos, activas segun conteo
    dots = ''.join([f"<span class='badge-dot{' badge-on' if i < badges else ''}'></span>" for i in range(8)])
    badges_html = f"<div class='badges-row'>{dots}</div>"
    if team_urls:
        team_html = ''.join([f"<span class='mini-mon'><img src='{u}' alt='pkm'/></span>" for u in team_urls])
        bottom = badges_html + f"<div class='mini-team'>{team_html}</div>"
    else:
        # Placeholders: 6 pokeballs mini
        bottom = badges_html + "<div class='mini-team'>" + ("<span class='mini-mon'><div class='pokeball-mini'></div></span>"*6) + "</div>"
    html = f"""
    <div class='profile-card'>
      <div class='profile-head'>
        <div class='profile-avatar'>
          {f"<img src='{_img_uri(img)}' alt='trainer'/>" if img else "<div class='pokeball-mini'></div>"}
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


# --- Auth / layout ---
def login_gate() -> None:
    init_storage()
    if st.session_state.get("auth_ok"):
        return
    st.header("Inicio de sesion")
    col1, col2 = st.columns(2)
    with col1:
        user = st.selectbox("Usuario", list(USERS.keys()), index=0)
    with col2:
        pwd = st.text_input("Codigo de acceso", type="password")
    ok = st.button("Entrar", type="primary")
    if ok:
        # Validacion simple: si hay codigo definido para el usuario, debe coincidir
        code = USERS.get(user)
        if not code or (pwd and str(pwd).strip().lower() == str(code).lower()):
            st.session_state.auth_ok = True
            st.session_state.user = user
            st.success(f"Bienvenido, {user}")
            st.rerun()
        else:
            st.error("Usuario o codigo incorrecto")
    st.stop()


def render_sidebar(sections: List[str]) -> str:
    usr = st.session_state.get('user') or '-'
    _render_sidebar_profile()
    st.sidebar.markdown("---")
    section = st.sidebar.selectbox("Seccion", sections, index=0)
    _apply_section_theme(section)
    st.sidebar.markdown("---")
    return section

def _apply_section_theme(section: str) -> None:
    # Cambia el color del watermark de Pokeball segun la seccion
    palette = {
        'Inicio': '#ef5350',
        'Entrenadores': '#ef5350',
        'Liga y Tabla': '#f59e0b',
        'Copa': '#8b5cf6',
        'Tienda': '#2a75bb',
        'Saves': '#10b981',
    }
    color = palette.get(section, '#ef5350')
    st.markdown(f"<style>:root{{ --ball-color: {color}; }}</style>", unsafe_allow_html=True)


# --- Badges scan helper ---
def coins_from_badges(sav_json: dict) -> int:
    """Heuristica simple: intenta contar hasta 8 medallas buscando claves 'badge'."""
    def scan(o) -> int:
        tot = 0
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if "badge" in kl:
                    try:
                        if bool(v):
                            tot += 1
                    except Exception:
                        pass
                tot += scan(v)
        elif isinstance(o, (list, tuple)):
            for it in o:
                tot += scan(it)
        return tot
    return min(scan(sav_json), 8)


# --- Pages wrappers ---
def page_inicio() -> None:
    user = st.session_state.get("user") or "-"
    st.header(f"Bienvenido, {user}")
    render_poke_separator()
    st.subheader("Guia rapida")
    st.markdown(
        "1. Ve a 'Saves' y sube tu archivo .sav.\n"
        "2. Configura el lector en 'Entrenadores' si es necesario.\n"
        "3. En 'Entrenadores' puedes ver equipo, cajas y detalles.\n"
        "4. En 'Tienda' compra comodines/objetos.\n"
        "5. 'Liga y Tabla' y 'Copa' muestran clasificaciones y emparejamientos."
    )


def page_entrenadores() -> None:
    """Puente a la vista de entrenadores con diseno vigente."""
    try:
        import entrenadores as _ent
        if hasattr(_ent, "page_entrenadores"):
            _ent.page_entrenadores()
        else:
            if hasattr(_ent, "page_entrenadores_setup"):
                _ent.page_entrenadores_setup()
            if hasattr(_ent, "page_entrenadores_view"):
                _ent.page_entrenadores_view()
    except Exception as e:
        st.error(f"No se pudo cargar la vista de entrenadores: {e}")


def page_tabla() -> None:
    try:
        import liga_tabla as _lt
        _lt.page_tabla()
    except Exception as e:
        st.error(f"No se pudo cargar la tabla: {e}")


def page_copa() -> None:
    try:
        import copa as _swiss
        import copa2 as _elim
        st.subheader("Copa")
        fmt = st.radio("Formato", ["Copa", "Torneo"], horizontal=True)
        st.markdown("---")
        if fmt == "Torneo":
            _elim.page_copa()
        else:
            _swiss.page_copa()
    except Exception as e:
        st.error(f"No se pudo cargar la copa: {e}")
