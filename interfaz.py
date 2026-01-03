# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List
from pathlib import Path

import streamlit as st

from utils import USERS, list_user_saves, DEFAULT_DLL_HINT
from showdown_sprites import showdown_sprite_url
from conex_pkhex import PKHeXRuntime, extract_team, get_bridge_path, open_sav_cached
try:
    # Reutilizar lógica de medallas de Entrenadores
    from entrenadores import _count_badges  # type: ignore
except Exception:
    _count_badges = None  # type: ignore
from storage import init_storage, settings_get, settings_set


def apply_css() -> None:
    css = """
    <style>
    :root {
      --accent: #e65050; /* rojo Pokeball suavizado */
      --accent-hover: #c73a3a;
      --text-1: #e6edf3;
      --text-2: #c9d1d9;
      --divider: rgba(255,255,255,0.14);
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
    hr { border: none; height: 2px; background: linear-gradient(90deg, transparent 0 10%, var(--divider) 10% 90%, transparent 90% 100%); position: relative; }
    hr::after { content:""; position:absolute; top:-7px; left:50%; transform:translateX(-50%); width:20px; height:20px; border-radius:50%;
      background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.9) 0 3px, transparent 4px),
                  linear-gradient(180deg, #ff1d1d 0 50%, #f9f9f9 50% 100%);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.25);
      border: 2px solid #111;
    }
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
      background:
        radial-gradient(circle at 50% 50%, rgba(255,255,255,0.9) 0 3px, transparent 4px),
        linear-gradient(180deg, #ff1d1d 0 50%, #f7f7f7 50% 100%);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.4), 0 2px 8px rgba(0,0,0,0.35);
      border: 2px solid #0b0d12;
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
        .pokeball-mini { width:16px; height:16px; border-radius:50%; position:relative; display:inline-block; background: linear-gradient(180deg, #ff1d1d 0 49%, #f7f7f7 51% 100%); border:2px solid #111; box-shadow: inset 0 0 0 2px #111; animation: spin 4s linear infinite; }
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
    """Busca retrato local reusando la lógica robusta de Entrenadores si está disponible."""
    try:
        # Reutilizar helper más completo si existe
        try:
            import entrenadores as _ent  # type: ignore
            if hasattr(_ent, "_find_trainer_image"):
                img = _ent._find_trainer_image(trainer)  # type: ignore
                if img:
                    return str(img)
        except Exception:
            pass

        pdir = Path('assets') / 'trainers'
        if not pdir.exists():
            return ''
        bases = [
            trainer,
            trainer.lower(),
            trainer.capitalize(),
            trainer.replace(' ', '_'),
            trainer.replace(' ', '-'),
        ]
        exts = ['.png', '.jpg', '.jpeg', '.webp']
        low = {f.name.lower(): str(f) for f in pdir.glob("*") if f.suffix.lower() in exts}
        for b in bases:
            for e in exts:
                cand = f"{b}{e}"
                p = pdir / cand
                if p.exists():
                    return str(p)
                if cand.lower() in low:
                    return low[cand.lower()]
    except Exception:
        return ''
    return ''


def _get_team_sprite_urls(user: str) -> list[str]:
    urls: list[str] = []
    try:
        if not user or user == '-':
            return urls
        # Cache por usuario+mtime para evitar abrir el save en cada rerun
        saves = list_user_saves(user)
        sav_path = None
        mtime = None
        try:
            if saves:
                import os
                sav_path = str(saves[0])
                mtime = os.path.getmtime(sav_path)
                cache = st.session_state.setdefault("_team_sprite_cache", {})
                key = (user, mtime)
                if key in cache:
                    return cache[key]
        except Exception:
            sav_path = str(saves[0]) if saves else None
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
        if not sav_path:
            saves = list_user_saves(user)
            if not saves:
                return urls
            sav_path = str(saves[0])
        sav_json = open_sav_cached(sav_path)
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
        try:
            if mtime is not None:
                st.session_state.setdefault("_team_sprite_cache", {})[(user, mtime)] = urls
        except Exception:
            pass
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
        sav_json = open_sav_cached(sav_path)
        if _count_badges:
            return int(_count_badges(sav_json))
        # coins_from_badges devuelve monedas (2 por medalla); convertimos a medallas
        return int(coins_from_badges(sav_json) // 2)
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


def _render_change_pin_form() -> None:
    usr = st.session_state.get('user') or ''
    if not usr or usr == '-':
        return
    with st.sidebar.expander("Cambiar PIN (4 dígitos)", expanded=False):
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
        new_in = st.text_input("PIN nuevo (4 dígitos)", type="password", max_chars=4, value="")
        if st.button("Guardar PIN", use_container_width=True):
            if current_pin:
                if not cur_in or cur_in.strip() != current_pin:
                    st.error("PIN actual incorrecto.")
                    return
            if not new_in or len(new_in.strip()) != 4 or (not new_in.strip().isdigit()):
                st.error("El PIN debe tener exactamente 4 dígitos.")
                return
            try:
                settings_set(f"pin:{usr}", new_in.strip())
                st.success("PIN actualizado.")
            except Exception as e:
                st.error(f"No se pudo guardar el PIN: {e}")


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
        pwd = st.text_input("PIN / Codigo de acceso", type="password", max_chars=8)
    ok = st.button("Entrar", type="primary")
    if ok:
        # Validacion: primero PIN persistido; si no existe, usa codigo base de USERS
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
        ok_pin = False
        if stored_pin:
            ok_pin = (pwd_in == stored_pin)
        else:
            ok_pin = (not code) or (pwd_in and pwd_in.lower() == str(code).lower())

        if ok_pin:
            st.session_state.auth_ok = True
            st.session_state.user = user
            st.success(f"Bienvenido, {user}")
            st.rerun()
        else:
            st.error("Usuario o codigo/PIN incorrecto")
    st.stop()


def render_sidebar(sections: List[str]) -> str:
    usr = st.session_state.get('user') or '-'
    _render_sidebar_profile()
    _render_change_pin_form()
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
    """Cuenta medallas (máx 8) y devuelve las monedas: 3 por cada una."""
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
    badges = min(scan(sav_json), 8)
    return badges * 3


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
    normativa_md = """
📜 **Normativa ChampionsLocke**

🔒 **1. Normas Nuzlocke**
- Un Pokémon debilitado se considera muerto y va a la caja de “muertos”; no puede usarse ni subir de nivel.
- Solo se captura el primer encuentro de cada ruta/área; si se pierde, huye o termina el combate, se pierde la captura.
- Mote obligatorio.
- Cláusulas: Duplicados (se fuerza otro encuentro si es línea ya capturada); Legendarios principales no permitidos (se fuerza otro encuentro); Shiny siempre capturable (no consume captura de ruta; si es duplicado eliges cuál conservar).

🧬 **2. Restricciones de equipo**
- Máx. 1 pseudo-legendario.
- Máx. 1 legendario menor/singular (≤600 BST).
- No repetir fase evolutiva; si obtienes un duplicado, liberas el último (salvo que el previo de esa fase esté muerto).

🧭 **3. Estructura por tramos**
- 4 tramos + Liga Pokémon final. Cada tramo acaba tras ciertos gimnasios; al cerrarlo se juega una liga entre jugadores.

⚔️ **4. Combates entre jugadores**
- Liga: 1 vs 1, Bo1. Límite de nivel = último combate oficial del tramo.
- Copa: tras la Liga Pokémon; eliminatoria, Bo3; cuadro definido antes.

📈 **5. Level Caps**
- Gimnasios: Roco 17 · Gardenia 26 · Fantina 31 · Brega 38 · Mananti 44 · Aceron 49 · Inverna 53 · Lectro 60.
- Liga Pokémon: Alecran 64 · Gaia 66 · Fausto 68 · Delos 71 · Cintia 74.
- Nadie puede pasar el cap del siguiente combate; si se pasa, va a caja. Caramelos raros solo para ajustar (se permite resetear si se sube de más y se había guardado).

🧩 **6. Divisiones (Liga A/B)**
- Divisiones A y B (5 y 5 jugadores); solo se enfrentan dentro.
- Ascensos/descensos al cerrar jornada: bajan 3 últimos de A, suben 3 primeros de B.
- Primera asignación: por muertos; empate se resuelve con combate.
- Puntos por jornada: 1º 9 · 2º 8 · 3º 7 · 4º 6 · 5º 5 · 6º 5 · 7º 4 · 8º 3 · 9º 2 · 10º 1. Penalización: −0.2 puntos por cada muerto (Caja 18). Total = suma jornadas − 0.2 × muertos.

💰 **7. Monedas (sin detallar precios)**
- Monedas por medallas: 3 por cada medalla (máx. 8).
- Monedas por Liga A/B: A → 1º 15 · 2º 14 · 3º 12 · 4º 11 · 5º 10; B → 6º 11 · 7º 9 · 8º 8 · 9º 6 · 10º 4.
- Saldo = (medallas × 3 + liga) − gastado.

🃏 **8. Comodines**
- Revivir: revive un Pokémon de Caja 18; queda marcado blindado + revivido.
- Robar: si el objetivo no está blindado, se registra el robo y el Pokémon queda robado + blindado; obtienes gratis un Comodín de Blindaje por Robo.
- Blindar: marca el Pokémon como blindado (no se puede robar ni blindar otra vez).
- Captura Extra: permite una captura adicional en una ruta desconocida (no eliges ruta conocida ni sabes qué Pokémon saldrá).
- Fósil: obtienes un fósil. Flags guardados en Supabase.

🤝 **9. Interacción**
- Se permiten intercambios y combates de práctica.
- Comodines sobre otros o sobre uno mismo (Robo no se repite dos veces seguidas sobre el mismo hasta que todos hayan sido objetivo).
- Directos obligatorios: jugar en Discord en directo y avisar por WhatsApp.
- Caramelos Raros y Escamas Corazón: uso ilimitado; venta prohibida.
"""
    with st.expander("Normativa ChampionsLocke", expanded=False):
        st.markdown(normativa_md)
        st.download_button(
            "Descargar normativa (TXT)",
            data=normativa_md,
            file_name="Normativa_ChampionsLocke.txt",
            mime="text/plain",
            use_container_width=True,
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

