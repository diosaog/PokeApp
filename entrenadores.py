# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import List
from urllib import request
from urllib.parse import urlparse

import streamlit as st

from showdown_sprites import showdown_sprite_url
from i18n import nature_display_es, translate_types_es, translate_type_es
from dexdata import move_name_es, ability_name_es
from dexdata import species_types, move_info, type_color, showdown_export
from ui_enhanced import team_grid_ui as _team_grid_ui_enhanced
from utils import USERS, DEFAULT_DLL_HINT, list_user_saves
from storage import get_flags_by_fingerprints, list_inventory
from pkmmeta import pokemon_fingerprint
from conex_pkhex import (
    PKHeXRuntime, extract_team, extract_box, has_pc_data, get_bridge_path, get_box_meta_quick
)

# TamaÂ±os y ajustes
TEAM_IMG_W = 88
BOX_IMG_W = 56
DETAIL_IMG_W = 112
TOTAL_BOXES = 18  # valor por defecto/fallback

# ===== Pokepaste helpers (compartido con Copa) =====
def _ensure_pokepaste_state() -> None:
    st.session_state.setdefault("pokepastes", {})


def _fetch_pokepaste_text(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        url = "https://" + url
    if "/raw" not in url:
        url = url.rstrip("/") + "/raw"
    with request.urlopen(url) as resp:  # type: ignore[call-arg]
        return resp.read().decode("utf-8", errors="ignore")


def _parse_pokepaste(txt: str) -> list[dict]:
    if "<!DOCTYPE" in txt or "<html" in txt.lower():
        raise ValueError("El enlace no devuelve texto plano (intenta con la URL /raw de Pokepaste).")
    import re
    blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    team = []
    for b in blocks:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if not lines:
            continue
        head = lines[0]
        species, item = head, None
        if "@" in head:
            parts = head.split("@", 1)
            species = parts[0].strip()
            item = parts[1].strip()
        ability = None
        moves = []
        for ln in lines[1:]:
            if ln.lower().startswith("ability:"):
                ability = ln.split(":", 1)[1].strip()
            elif ln.startswith("-"):
                mv = ln[1:].strip()
                if mv:
                    moves.append(mv)
                    if len(moves) >= 4:
                        break
        team.append({"species": species, "item": item, "ability": ability, "moves": moves})
    return team


def _clean_text(val: str | None) -> str:
    if not val:
        return ""
    import re
    txt = str(val)
    # quita etiquetas HTML simples y espacios
    txt = re.sub(r"<[^>]+>", "", txt)
    return txt.strip()


def _sanitize_mon(mon: dict) -> dict:
    sp_raw = _clean_text(mon.get("species"))
    nickname = ""
    species_clean = sp_raw
    try:
        import re
        m = re.match(r"^(.*?)\(([^)]+)\)", sp_raw)
        if m:
            nickname = m.group(1).strip()
            species_clean = m.group(2).strip()
    except Exception:
        species_clean = sp_raw
    item = _clean_text(mon.get("item"))
    ability = _clean_text(mon.get("ability"))
    moves_raw = mon.get("moves") or []
    moves: list[str] = []
    for m in moves_raw:
        cm = _clean_text(m)
        if cm:
            moves.append(cm)
    title = f"{nickname} ({species_clean})" if nickname else species_clean
    return {"species": species_clean, "nickname": nickname, "title": title, "item": item, "ability": ability, "moves": moves}


def _pokepaste_preview(paste: dict | None) -> None:
    if not paste or not paste.get("team"):
        st.caption("Sin Pokepaste guardado.")
        return
    st.caption(f"URL: {paste.get('url')}")
    team = [ _sanitize_mon(mon) for mon in (paste.get("team") or []) ]
    team = [m for m in team if m.get("species")]
    for mon in team:
        sp = mon.get("species") or "Pokemon"
        title = mon.get("title") or sp
        item = mon.get("item")
        ability = mon.get("ability")
        moves = mon.get("moves") or []
        img = showdown_sprite_url(species_name=str(sp), prefer_animated=False)
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(img, width=72)
            with cols[1]:
                st.markdown(f"**{title}** {f'@ {item}' if item else ''}")
                if ability:
                    st.caption(f"Habilidad: {ability}")
                if moves:
                    st.markdown("\n".join([f"- {m}" for m in moves]))

# Helpers de cajas para manejar Gen3/Gen4
def _resolve_total_boxes(box_count: int, box_names: List[str]) -> int:
    if box_count and box_count > 0:
        return box_count
    if box_names:
        return len(box_names)
    return TOTAL_BOXES

def _muertos_box_index(box_count: int) -> int:
    """Caja que se usa como 'muertos'. Preferimos la última caja disponible."""
    if box_count and box_count > 0:
        return max(0, min(box_count - 1, 17))
    return 17


# ---------- Trainer portraits (AI images) ----------
PORTRAITS_DIR = Path("assets") / "trainers"
BADGES_DIR = Path("assets") / "medallas"

# ---------- Bridge auto-load helper ----------
def _try_auto_load_bridge() -> bool:
    """Intenta cargar PKHeXBridge automÃ¡ticamente sin interacción.
    Devuelve True si queda cargado en session_state.
    """
    try:
        if st.session_state.get("pkhex_loaded", False):
            return True

        # Candidatos habituales (carpeta o exe)
        candidates = [
            st.session_state.get("pkhex_dll_path") or DEFAULT_DLL_HINT,
            r"Bridge\PKHeXBridge\bin\Release\net9.0\win-x64\publish",
            r"Bridge\PKHeXBridge\bin\Release\net9.0",
            r"Bridge\PKHeXBridge\bin\Debug\net9.0",
            r"Bridge\PKHeXBridge\bin\Release\net8.0\win-x64\publish",
            r"Bridge\PKHeXBridge\bin\Debug\net8.0\win-x64\publish",
        ]

        # BÃºsqueda rÃ¡pida del ejecutable en el repo (limitada)
        try:
            roots = [Path("Bridge"), Path("."), Path("tools")]
            seen = set()
            for root in roots:
                if not root.exists():
                    continue
                for exe in root.rglob("PKHeXBridge.exe"):
                    # Evitar duplicados; añadimos tanto exe como carpeta
                    candidates.append(str(exe))
                    parent = str(exe.parent)
                    if parent not in seen:
                        seen.add(parent)
                        candidates.append(parent)
        except Exception:
            pass

        for cand in candidates:
            try:
                if not cand:
                    continue
                PKHeXRuntime.load(cand)
                st.session_state.pkhex_loaded = True
                st.session_state.pkhex_dll_path = cand
                # Modo auto por defecto
                st.session_state.setdefault("pkhex_mode", "auto")
                return True
            except Exception:
                continue
        # Si no se pudo, marcar explícitamente como no cargado
        st.session_state.pkhex_loaded = False
        return False
    except Exception:
        # No bloquear la UI si algo falla
        return False

def _slug_candidates(name: str) -> List[str]:
    s = (name or "").strip()
    if not s:
        return []
    base = [s, s.lower(), s.capitalize()]
    # Variantes con guiones y subrayados por si el archivo llega con otro formato
    norm = s.replace(" ", "_")
    base += [norm, norm.lower()]
    norm2 = s.replace(" ", "-")
    base += [norm2, norm2.lower()]
    return list(dict.fromkeys(base))  # unique, preserve order

def _find_trainer_image(trainer: str) -> str | None:
    try:
        if not PORTRAITS_DIR.exists():
            return None
        exts = (".png", ".jpg", ".jpeg", ".webp")
        for cand in _slug_candidates(trainer):
            for ext in exts:
                p = PORTRAITS_DIR / f"{cand}{ext}"
                if p.exists():
                    return str(p)
        # BÂºsqueda case-insensitive por si los nombres no coinciden exactamente
        low = {f.name.lower(): str(f) for f in PORTRAITS_DIR.glob("*") if f.suffix.lower() in exts}
        for cand in _slug_candidates(trainer):
            for ext in exts:
                key = f"{cand}{ext}".lower()
                if key in low:
                    return low[key]
        return None
    except Exception:
        return None

def _render_trainer_hero(trainer: str) -> None:
    """Muestra una imagen destacada del entrenador si existe.
    Busca en assets/trainers con el nombre del jugador (png/jpg/jpeg/webp).
    """
    try:
        img = _find_trainer_image(trainer)
        if not img:
            return
        # Estilos locales suaves para integrar con el tema existente
        css = """
        <style>
        .trainer-hero { display:flex; gap:18px; align-items:center; margin: 6px 0 14px; }
        .trainer-hero .portrait { border-radius: 16px; overflow:hidden;
                                   border:1px solid color-mix(in srgb, var(--accent) 45%, rgba(255,255,255,0.08));
                                   box-shadow: 0 8px 24px rgba(0,0,0,0.35);
                                   background: rgba(255,255,255,0.02); backdrop-filter: blur(2px); }
        .trainer-hero .caption { font-size: 1.25rem; font-weight: 700; opacity: .95; }
        .trainer-hero .note { opacity:.75; }
        @media (max-width: 900px) { .trainer-hero { flex-direction: column; align-items: flex-start; } }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        with st.container():
            colL, colR = st.columns([1, 2], gap="large")
            with colL:
                st.markdown("<div class='portrait'>", unsafe_allow_html=True)
                st.image(img, use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with colR:
                st.markdown(f"<div class='caption'>Entrenador: {trainer}</div>", unsafe_allow_html=True)
                st.caption("Imagen generada por IA")
    except Exception:
        # No romper la pÂ¡gina si hay algÂºn problema de assets
        pass

# ---------- Medals (Sinnoh) ----------
_SINNOH_BADGE_FILES = [
    "Medalla_Lignito.png",   # Coal
    "Medalla_Bosque.png",    # Forest
    "Medalla_Reliquia.png",  # Relic
    "Medalla_Adoquin.png",   # Cobble
    "Medalla_Cienaga.png",   # Fen
    "Medalla_Mina.png",      # Mine
    "Medalla_Carambano.png", # Icicle
    "Medalla_Faro.png",      # Beacon
]

def _render_medals_row(count: int) -> None:
    try:
        n = max(0, min(int(count or 0), 8))
    except Exception:
        n = 0
    files: List[str] = []
    for i in range(n):
        p = BADGES_DIR / _SINNOH_BADGE_FILES[i]
        if p.exists():
            files.append(str(p))
    if not files:
        st.caption("Sin medallas todavía")
        return
    cols = st.columns(len(files))
    for i, f in enumerate(files):
        with cols[i]:
            try:
                st.image(f, width=32)
            except Exception:
                pass

# ---------- Sprites helpers ----------
def _url_official_art_by_id(dex_id: int) -> str:
    return (
        "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/"
        f"pokemon/other/official-artwork/{dex_id}.png"
    )


def _sprite_url_from_p(p: dict, *, prefer_animated: bool = True) -> str:
    species_name = p.get("species_name") or p.get("species")
    if isinstance(species_name, str) and species_name.startswith("#") and species_name[1:].isdigit():
        species_name = None
    if species_name:
        return showdown_sprite_url(
            species_name=species_name,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            is_shiny=bool(p.get("is_shiny", False)),
            gender=p.get("gender"),
            prefer_animated=prefer_animated,
        )
    dex_id = p.get("dex_id")
    if isinstance(dex_id, int) and dex_id > 0:
        return _url_official_art_by_id(dex_id)
    return f"https://via.placeholder.com/{TEAM_IMG_W}?text=PKM"


# ---------- UI helpers ----------
def _extract_stats_from_p(p: dict) -> dict | None:
    """Obtiene estadísticas visibles. Si no existen en el dict,
    intenta calcularlas con baseStats + IVs/EVs + nivel + naturaleza."""
    try:
        # 1) Si ya vienen incluidas
        stx = p.get('stats') if isinstance(p, dict) else None
        if isinstance(stx, dict) and any(k in stx for k in ('hp','atk','def','spa','spd','spe')):
            # normaliza a int
            out = {}
            for k in ('hp','atk','def','spa','spd','spe'):
                v = stx.get(k)
                try:
                    out[k] = int(v)
                except Exception:
                    pass
            if out:
                return out

        # 2) Si vienen sueltas en p
        keys = [('hp','HP'),('atk','ATK'),('def','DEF'),('spa','SPA'),('spd','SPD'),('spe','SPE')]
        out = {}
        for k, up in keys:
            v = p.get(k)
            if v is None:
                v = p.get(up)
            if v is not None:
                try:
                    out[k] = int(v)
                except Exception:
                    pass
        if out and len(out) >= 3:
            return out

        # 3) Calcularlas a partir de datos
        species = p.get('species_name') or p.get('species')
        if not species:
            return None
        # Datos base
        try:
            from dexdata import pokedex_data
            from showdown_sprites import showdown_id  # evitar ciclos
            sid = showdown_id(
                species_name=species,
                form_index=p.get('form_index'),
                form_name=p.get('form_name'),
                gender=p.get('gender'),
            )
            key = sid.replace('-', '').lower()
            pdx = pokedex_data()
            entry = pdx.get(key) or {}
            if not entry and '-' in sid:
                entry = pdx.get(sid.split('-', 1)[0].replace('-', '').lower()) or {}
            bstats = entry.get('baseStats') or {}
        except Exception:
            bstats = {}
        if not bstats:
            return None

        def _to_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return default

        level = _to_int(p.get('level') or 50, 50)
        ivs = p.get('ivs') or {}
        evs = p.get('evs') or {}

        # Naturaleza
        up = down = None
        try:
            from i18n import NATURES_ES
            nat = p.get('nature')
            key = str(nat or '').strip()
            key_norm = key.lower().capitalize()
            data = NATURES_ES.get(key) or NATURES_ES.get(key_norm)
            if data:
                _name, up_long, down_long = data
                map_short = {
                    'attack': 'atk',
                    'special-attack': 'spa',
                    'defense': 'def',
                    'special-defense': 'spd',
                    'speed': 'spe',
                }
                up = map_short.get(up_long)
                down = map_short.get(down_long)
        except Exception:
            pass

        def _nature_mult(stat_key: str) -> float:
            if up and stat_key == up:
                return 1.1
            if down and stat_key == down:
                return 0.9
            return 1.0

        def calc_hp(base, iv, ev) -> int:
            return int(((2*base + iv + ev//4) * level) // 100 + level + 10)

        def calc_other(base, iv, ev, mult) -> int:
            val = int(((2*base + iv + ev//4) * level) // 100 + 5)
            return int(val * mult)

        res = {}
        for k in ('hp','atk','def','spa','spd','spe'):
            b = _to_int(bstats.get(k), None)
            if b is None:
                continue
            iv = _to_int((ivs or {}).get(k), 0)
            ev = _to_int((evs or {}).get(k), 0)
            if k == 'hp':
                res[k] = calc_hp(b, iv, ev)
            else:
                res[k] = calc_other(b, iv, ev, _nature_mult(k))
        return res if res else None
    except Exception:
        return None
def _badge_row(level: int | str | None, is_shiny: bool, gender: str | None) -> str:
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "Â¢Â¢Ã¢Å¡Â¬Â¢Ã¢Â¬Â") else "<span></span>"
    sh = "?" if is_shiny else ""
    gd = {"M": "?", "F": "?"}.get((gender or "").upper(), "")
    right = f"<span style='opacity:.9'>{sh} {gd}</span>".strip()
    return f"<div class='badges'><div>{lv}</div><div>{right}</div></div>"


def _slot_card_html(img_url: str, title: str, subtitle: str, img_w: int, level, is_shiny, gender, types: list[str] | None = None) -> str:
    badges = _badge_row(level, is_shiny, gender)
    types_html = ""
    if types:
        labels = translate_types_es(types)
        chips = " ".join(
            f"<span class='type-chip' style='background:{type_color(t)}'>{labels[i]}</span>" for i, t in enumerate(types[:2])
        )
        types_html = f"<div class='types'>{chips}</div>"
    return f"""
    <div class='slot'>
      {badges}
      <img src="{img_url}" width="{img_w}" alt="{title}">
      <div class='title'>{title}</div>
      <div class='sub'>{subtitle}</div>
      {types_html}
    </div>
    """

# Override badge row to fix mojibake and symbols
def _badge_row(level: int | str | None, is_shiny: bool, gender: str | None) -> str:  # type: ignore[override]
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "-") else "<span></span>"
    sh = "★" if is_shiny else ""
    gd = {"M": "♂", "F": "♀"}.get((gender or "").upper(), "")
    right = f"<span style='opacity:.9'>{sh} {gd}</span>".strip()
    return f"<div class='badges'><div>{lv}</div><div>{right}</div></div>"


def _slot_empty_html(label: str) -> str:
    return f"""
    <div class='slot slot-empty'>
      <div class='hint'>Vac&iacute;o &ndash; {label}</div>
    </div>
    """


# ---------- Badges/monedas/puntos ----------
COINS_BY_POSITION = {1: 12, 2: 11, 3: 9, 4: 8, 5: 9, 6: 6, 7: 5, 8: 4, 9: 2}


def coins_from_league(user: str) -> int:
    lr = st.session_state.get("league_results", {})
    user_map = lr.get(user, {})
    return sum(COINS_BY_POSITION.get(pos, 0) for pos in user_map.values())


def _bitcount(n: int) -> int:
    try:
        return int(bin(int(n)).count("1"))
    except Exception:
        return 0


def _sum_truthy(iterable) -> int:
    return sum(1 for x in iterable if bool(x))


def _count_badges_from_value(v) -> int:
    if isinstance(v, (list, tuple)):
        return _sum_truthy(v)
    if isinstance(v, dict):
        return _sum_truthy(v.values())
    if isinstance(v, int):
        return _bitcount(v)
    if isinstance(v, bool):
        return 1 if v else 0
    return 0


def _count_badges(sav_json: dict) -> int:
    if not isinstance(sav_json, dict):
        return 0
    for path in [("trainer", "badges"), ("Trainer", "Badges"), ("badges",), ("Badges",)]:
        cur, ok = sav_json, True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok:
            cnt = _count_badges_from_value(cur)
            if cnt:
                return min(cnt, 8)
    for k in ("BadgeFlags", "Badges", "badgesFlags", "badge_flags"):
        if k in sav_json and isinstance(sav_json[k], int):
            return min(_bitcount(sav_json[k]), 8)
    SINNOH = {"coal", "forest", "relic", "cobble", "fen", "mine", "icicle", "beacon"}
    def scan(o) -> int:
        tot = 0
        if isinstance(o, dict):
            for kk, vv in o.items():
                kl = str(kk).lower()
                if "badge" in kl:
                    tot += _count_badges_from_value(vv)
                for nm in SINNOH:
                    if nm in kl:
                        tot += _count_badges_from_value(vv)
                tot += scan(vv)
        elif isinstance(o, (list, tuple)):
            for it in o:
                tot += scan(it)
        return tot
    return min(scan(sav_json), 8)


def _trainer_summary_ui(sav_json: dict, box_count: int) -> None:
    """Monedas netas (liga+medallas Â¢Ã¢Â Â¢Ã¢Â¬Ã¢Â¢ compras), Puntos, Muertos, Medallas."""
    try:
        medallas = _count_badges(sav_json)
    except Exception:
        medallas = 0
    monedas_badges = 3 * medallas

    jugador = st.session_state.get("trainer_selected") or st.session_state.get("user")
    monedas_liga = coins_from_league(jugador or "")
    bruto = monedas_badges + monedas_liga
    try:
        from storage import total_spent
        spent = total_spent(jugador or "")
    except Exception:
        spent = 0
    monedas = max(bruto - spent, 0)

    try:
        from liga_tabla import current_points_total
        puntos = current_points_total(jugador or "")
    except Exception:
        puntos = 0.0

    box_index_muertos = _muertos_box_index(box_count)
    try:
        muertos_list = extract_box(sav_json, box_index_muertos) if box_count > box_index_muertos else []
    except Exception:
        muertos_list = []
    muertos = len(muertos_list)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Monedas", monedas)
    with c2:
        st.metric("Puntos", puntos)
    with c3:
        st.metric("Muertos", muertos)
    with c4:
        st.markdown("**Medallas**")
        _render_medals_row(medallas)


def _hp_bar(label: str, value: float, cap: float, color: str) -> str:
    try:
        pct = 0 if cap <= 0 else max(0, min(100, int(100 * float(value) / float(cap))))
    except Exception:
        pct = 0
    return (
        f"<div class='hp-row'><div class='hp-label'>{label}</div>"
        f"<div class='hp-bar'><div class='hp-fill' style='width:{pct}%; background:{color}'></div></div>"
        f"<div class='hp-val'>{value}</div></div>"
    )

def _ensure_trainer_css() -> None:
    css = """
    <style>
    .trainer-card { border:1px solid rgba(255,255,255,0.14); background:rgba(255,255,255,0.03);
                    border-radius:14px; padding:12px 14px; }
    .hp-row { display:grid; grid-template-columns: 96px 1fr 52px; align-items:center; gap:10px; margin:6px 0; }
    .hp-label { opacity:.85; font-weight:700; }
    .hp-bar { height:10px; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden; border:1px solid rgba(255,255,255,0.12); }
    .hp-fill { height:100%; border-radius:999px; box-shadow: 0 0 10px rgba(255,255,255,0.12) inset; }
    .medals-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:6px; }
    .medals-row img { width: 32px; height:auto; filter: drop-shadow(0 2px 6px rgba(0,0,0,0.35)); }
    </style>
    """
    try:
        st.markdown(css, unsafe_allow_html=True)
    except Exception:
        pass

def _trainer_summary_with_portrait_ui(sav_json: dict, box_count: int) -> None:
    _ensure_trainer_css()
    """Resumen con imagen del entrenador a la izquierda y KPIs a la derecha."""
    try:
        medallas = _count_badges(sav_json)
    except Exception:
        medallas = 0
    monedas_badges = 3 * medallas

    jugador = st.session_state.get("trainer_selected") or st.session_state.get("user")
    monedas_liga = coins_from_league(jugador or "")
    bruto = monedas_badges + monedas_liga
    try:
        from storage import total_spent
        spent = total_spent(jugador or "")
    except Exception:
        spent = 0
    monedas = max(bruto - spent, 0)

    try:
        from liga_tabla import current_points_total
        puntos = current_points_total(jugador or "")
    except Exception:
        puntos = 0.0

    box_index_muertos = _muertos_box_index(box_count)
    try:
        muertos_list = extract_box(sav_json, box_index_muertos) if box_count > box_index_muertos else []
    except Exception:
        muertos_list = []
    muertos = len(muertos_list)

    colL, colR = st.columns([1, 3], gap="large")
    with colL:
        trainer = jugador or ""
        img = _find_trainer_image(trainer)
        if img:
            st.image(img, caption=trainer, width=260)
        else:
            st.markdown("<div class='pokedex-card'>Sin retrato disponible</div>", unsafe_allow_html=True)
    with colR:
        # Tarjeta estilo "trainer"
        with st.container(border=False):
            st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
            region = st.session_state.get("trainer_region", {}).get(jugador or "", "Sinnoh")
            st.markdown(f"**Entrenador:** {jugador}    **Regin:** {region}")
            # Barras estilo HP (Monedas, Puntos) + fila de medallas
            html = "".join([
                _hp_bar("Monedas", monedas, 20, "#ffd54f"),
                _hp_bar("Puntos", puntos, 30, "#4fc3f7"),
            ])
            st.markdown(html, unsafe_allow_html=True)
            _render_medals_row(medallas)
            try:
                st.markdown(
                    f"<div class='panel-ghost'><div class='title'>Muertos (Caja 18)</div><div class='value'>{muertos}</div></div>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass
            st.markdown("</div>", unsafe_allow_html=True)


def _team_grid_ui(team: List[dict]) -> None:
    st.subheader("Equipo actual")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            if i < len(team):
                t = team[i]
                img_url = _sprite_url_from_p(t, prefer_animated=True)
                nickname = t.get("nickname") or ""
                species = t.get("species_name") or t.get("species")
                subtitle = species if nickname else ""
                title = nickname if nickname else species
                html = _slot_card_html(
                    img_url=img_url,
                    title=title,
                    subtitle=subtitle,
                    img_w=TEAM_IMG_W,
                    level=t.get("level", "-"),
                    is_shiny=bool(t.get("is_shiny", False)),
                    gender=t.get("gender"),
                )
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Ver detalles", key=f"team_view_{i}"):
                    st.session_state.selected_pokemon = {
                        "from": "team", "slot": i + 1,
                        "species": species,
                        "nickname": nickname,
                        "level": t.get("level", "-"),
                        "nature": t.get("nature", "-"),
                        "moves": t.get("moves", []),
                        "moves_detail": t.get("moves_detail"),
                        "form_name": t.get("form_name"),
                        "form_index": t.get("form_index"),
                        "is_shiny": t.get("is_shiny", False),
                        "gender": t.get("gender"),
                        "dex_id": t.get("dex_id"),
                        "ivs": t.get("ivs"),
                        "held_item": t.get("held_item") or t.get("Item"),
                        "evs": t.get("evs"),
                    }
                # selección por click (sin botón adicional)
            else:
                st.markdown(_slot_empty_html(f"Slot {i+1}"), unsafe_allow_html=True)



        apodo = p.get('nickname','') or 'Â¢Ã¢Â¬Ã¢Â'
        nivel = p.get('level', '-')
        natura = nature_display_es(p.get('nature'))
        shiny = "<div><strong>Shiny:</strong> SÂ­ ?</div>" if p.get("is_shiny") else ""
        forma = f"<div><strong>Forma:</strong> {p.get('form_name')}</div>" if p.get("form_name") else ""
        html = f"""
        <div class='pokedex-card'>
          <div><strong>Especie:</strong> {especie}</div>
          <div><strong>Apodo:</strong> {apodo}</div>
          <div><strong>Nivel:</strong> {nivel}</div>
          <div><strong>Naturaleza:</strong> {natura}</div>
          {shiny}
          {forma}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        # Características (stats) bajo los datos centrales; IVs se muestran sólo en la columna central
        try:
            stx = _extract_stats_from_p(p) or {}
        except Exception:
            stx = {}
        if stx:
            ps = stx.get('hp','-'); atk = stx.get('atk','-'); deff = stx.get('def','-')
            spa = stx.get('spa','-'); spd = stx.get('spd','-'); spe = stx.get('spe','-')
            stats_html = f"""
            <div class='pokedex-card'>
              <div><strong>PS:</strong> {ps}</div>
              <div><strong>Ataque:</strong> {atk}</div>
              <div><strong>Defensa:</strong> {deff}</div>
              <div><strong>At. Esp.:</strong> {spa}</div>
              <div><strong>Def. Esp.:</strong> {spd}</div>
              <div><strong>Veloc.:</strong> {spe}</div>
            </div>
            """
            st.markdown(stats_html, unsafe_allow_html=True)
        # Características (stats) e IVs: IVs solo para tu propio perfil
        try:
            current_user = st.session_state.get("user")
            trainer_sel = st.session_state.get("trainer_selected")
            own = bool(current_user) and (current_user == trainer_sel)
        except Exception:
            own = False
        if own:
            ivs = p.get('ivs') or {}
            order = [("hp","HP"),("atk","Atk"),("def","Def"),("spa","SpA"),("spd","SpD"),("spe","Spe")]
            def _fmt(d):
                parts=[]
                for k,label in order:
                    v=d.get(k)
                    try:
                        v=int(v)
                    except Exception:
                        v=None
                    if v is not None:
                        parts.append(f"{label}:{v}")
                return (' '.join(parts)) if parts else '-'
            ivs_html = f"<div><strong>IVs:</strong> {_fmt(ivs)}</div>" if ivs else ""
            st.markdown(f"<div class='pokedex-card'>{ivs_html}</div>", unsafe_allow_html=True)
        try:
            stx = _extract_stats_from_p(p) or {}
        except Exception:
            stx = {}
        if stx:
            ps = stx.get('hp','-'); atk = stx.get('atk','-'); deff = stx.get('def','-')
            spa = stx.get('spa','-'); spd = stx.get('spd','-'); spe = stx.get('spe','-')
            stats_html = f"""
            <div class='pokedex-card'>
              <div><strong>PS:</strong> {ps}</div>
              <div><strong>Ataque:</strong> {atk}</div>
              <div><strong>Defensa:</strong> {deff}</div>
              <div><strong>At. Esp.:</strong> {spa}</div>
              <div><strong>Def. Esp.:</strong> {spd}</div>
              <div><strong>Veloc.:</strong> {spe}</div>
            </div>
            """
            st.markdown(stats_html, unsafe_allow_html=True)
        # Estadísticas (si están disponibles)
        try:
            stx = _extract_stats_from_p(p) or {}
        except Exception:
            stx = {}
        if stx:
            ps = stx.get('hp', '-')
            atk = stx.get('atk', '-')
            deff = stx.get('def', '-')
            spa = stx.get('spa', '-')
            spd = stx.get('spd', '-')
            spe = stx.get('spe', '-')
            stats_html = f"""
            <div class='pokedex-card'>
              <div><strong>PS:</strong> {ps}</div>
              <div><strong>Ataque:</strong> {atk}</div>
              <div><strong>Defensa:</strong> {deff}</div>
              <div><strong>At. Esp.:</strong> {spa}</div>
              <div><strong>Def. Esp.:</strong> {spd}</div>
              <div><strong>Veloc.:</strong> {spe}</div>
            </div>
            """
            st.markdown(stats_html, unsafe_allow_html=True)
    with info_cols[2]:
        moves = p.get("moves", []) or ["Â¢Ã¢Â¬Ã¢Â", "Â¢Ã¢Â¬Ã¢Â", "Â¢Ã¢Â¬Ã¢Â", "Â¢Ã¢Â¬Ã¢Â"]
        "".join(f"<li>{mv}</li>" for mv in moves)
        # Enriched moves: type/category/power/accuracy/PP
        mdet = p.get("moves_detail") or []
        rows = []
        for idx, mv in enumerate(moves):
            if not mv:
                continue
            mv_es = move_name_es(str(mv))
            info = move_info(str(mv)) or {}
            t = info.get('type')
            # categoria (FÂ­sico/Especial/Estado) no se muestra por preferencia del usuario
            info.get('category')
            powr = info.get('power')
            acc = info.get('accuracy')
            pp_tot = info.get('pp')
            pp_cur = None
            if idx < len(mdet) and isinstance(mdet[idx], dict):
                pp_cur = mdet[idx].get('pp')
            t_es = translate_type_es(t)
            type_chip = f"<span style=\"display:inline-block;padding:2px 8px;border-radius:999px;color:#fff;background:{type_color(t)};font-weight:600;font-size:0.72rem;margin-right:6px;\">{t_es}</span>"
            stats = f"{powr or '-'} Pot. / {acc if (isinstance(acc,int) or isinstance(acc,float)) else '-'} Prec. / PP {pp_cur if pp_cur is not None else '-'}{('/'+str(pp_tot)) if pp_tot else ''}"
            rows.append(f"<div style='margin:4px 0'><strong>{mv_es}</strong><div>{type_chip}</div><div style='opacity:.85'>{stats}</div></div>")
        block = "".join(rows)
        st.markdown(f"<div class='pokedex-card'><strong>Movimientos</strong>{block}</div>", unsafe_allow_html=True)


def _pokemon_detail_panel() -> None:
    st.subheader("Detalle del Pokemon")
    p = st.session_state.get("selected_pokemon")
    if not p:
        st.markdown(
            "<div class='panel-dashed'>Selecciona un Pokemon del equipo o de una caja para ver sus estadisticas y movimientos.</div>",
            unsafe_allow_html=True,
        )
        return

    css = """
    <style>
    .ds-detail { display: grid; grid-template-columns: 1fr 1fr 1.6fr; gap: 14px; }
    .ds-card { border-radius: 16px; background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.025)); padding: 10px 12px; border:1px solid rgba(255,255,255,0.12); }
    .ds-left img { image-rendering: pixelated; }
    .hp-head { display:flex; align-items:center; justify-content:space-between; font-weight:700; margin-bottom:6px; }
    .hp-bar { height:10px; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden; border:1px solid rgba(255,255,255,0.12); }
    .hp-fill { height:100%; background: linear-gradient(90deg, #66bb6a, #43a047); width:100%; }
    .stats-table { display:grid; grid-template-columns: 1fr auto; gap:6px 12px; }
    .stat-label { font-weight:700; color:#e6edf3; padding:2px 10px; border-radius:12px; background:#334155; }
    .stat-up { background:#7f1d1d; color:#ffebee; }
    .stat-down { background:#0e3a5e; color:#e3f2fd; }
    .stat-val { text-align:right; font-weight:700; opacity:.95; }

    .moves-list { display:flex; flex-direction:column; gap:10px; }
    .move-row { display:grid; grid-template-columns: auto 1fr auto; align-items:center; gap:10px; padding:8px 10px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); }
    .type-pill { font-weight:800; letter-spacing:.5px; color:#0b0f14; background:#cbd5e1; border-radius:8px; padding:2px 8px; text-transform:uppercase; font-size:.72rem; }
    .pp-box { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color:#e6edf3; }
    .pp-bar { height:6px; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden; margin-top:4px; }
    .pp-fill { height:100%; background:linear-gradient(90deg,#ffcc80,#fb8c00); width:var(--pp); }
    .caption { opacity:.8 }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    def _nature_mods(nature_val):
        try:
            from i18n import NATURES_ES
            key = str(nature_val or '').strip()
            key_norm = key.lower().capitalize()
            data = NATURES_ES.get(key) or NATURES_ES.get(key_norm)
            if not data:
                return None, None
            _name, up, down = data
            map_short = {
                'attack': 'atk',
                'special-attack': 'spa',
                'defense': 'def',
                'special-defense': 'spd',
                'speed': 'spe',
            }
            return map_short.get(up), map_short.get(down)
        except Exception:
            return None, None

    up_key, down_key = _nature_mods(p.get('nature'))

    stx = _extract_stats_from_p(p) or {}
    def _s(k):
        try:
            v = stx.get(k)
            return int(v) if v is not None else '-'
        except Exception:
            return '-'

    colL, colM, colR = st.columns([1, 1, 1.6], gap="large")

    with colL:
        img_url = _sprite_url_from_p(p, prefer_animated=True)
        st.image(img_url, width=DETAIL_IMG_W)
        try:
            item = p.get('held_item') or p.get('item') or '-'
        except Exception:
            item = '-'
        st.markdown(f"<div class='ds-card'><div><strong>Objeto</strong></div><div class='caption'>{item}</div></div>", unsafe_allow_html=True)

    with colM:
        ps = _s('hp')
        st.markdown("<div class='ds-card'>" + f"<div class='hp-head'><span>PS</span><span>{ps}/{ps}</span></div>" + "<div class='hp-bar'><div class='hp-fill'></div></div>" + "</div>", unsafe_allow_html=True)
        labels = [('atk', 'Ataque'), ('def', 'Defensa'), ('spa', 'At. Esp.'), ('spd', 'Def. Esp.'), ('spe', 'Veloc.')]
        rows = []
        for key, label in labels:
            cls = 'stat-label'
            if up_key and key == up_key:
                cls += ' stat-up'
            if down_key and key == down_key:
                cls += ' stat-down'
            rows.append(f"<div class='{cls}'>{label}</div><div class='stat-val'>{_s(key)}</div>")
        stats_html = ("<div class='ds-card'>" + "<div class='stats-table'>" + "".join(rows) + "</div>" + "</div>")
        st.markdown(stats_html, unsafe_allow_html=True)

    with colR:
        moves = p.get('moves', []) or [None, None, None, None]
        mdet = p.get('moves_detail') or []
        mv_rows = []
        for idx, mv in enumerate(moves):
            if not mv:
                continue
            mv_es = move_name_es(str(mv))
            info = move_info(str(mv)) or {}
            t = info.get('type')
            t_es = translate_type_es(t).upper() if t else '-'
            color = type_color(t) if t else '#475569'
            pp_tot = info.get('pp') or 0
            pp_cur = None
            if idx < len(mdet) and isinstance(mdet[idx], dict):
                pp_cur = mdet[idx].get('pp')
            if pp_cur is None:
                pp_cur = pp_tot
            try:
                perc = int(max(0, min(100, round(100*pp_cur/pp_tot)))) if pp_tot else 0
            except Exception:
                perc = 0
            row = (
                f"<div class='move-row' style='--pp:{perc}%;'>"
                f"<span class='type-pill' style='background:{color}; color:#fff'>{t_es}</span>"
                f"<div style='font-weight:700'>{mv_es}</div>"
                f"<div class='pp-box' style='text-align:right'>{pp_cur}/{pp_tot}<div class='pp-bar'><div class='pp-fill'></div></div></div>"
                f"</div>"
            )
            mv_rows.append(row)
        st.markdown("<div class='moves-list'>" + "".join(mv_rows) + "</div>", unsafe_allow_html=True)
def _boxes_grid_ui(sav_json: dict, box_count: int, box_names: List[str], *, save_path: str | None = None) -> None:
    st.subheader("PC (Cajas)")
    if not has_pc_data(sav_json, save_path=save_path):
        st.warning("PC no disponible. Revisa el Bridge si persiste.")
        return
    total_boxes = _resolve_total_boxes(box_count, box_names)
    virtual_names = list(box_names)[:total_boxes]
    if len(virtual_names) < total_boxes:
        start = len(virtual_names)
        virtual_names += [f"Caja {i+1}" for i in range(start, total_boxes)]
    box_index = st.selectbox(
        "Caja",
        options=list(range(total_boxes)),
        index=0,
        format_func=lambda i: virtual_names[i] if i < len(virtual_names) else f"Caja {i+1}",
    )
    try:
        box_list = extract_box(sav_json, box_index, save_path=save_path)
    except Exception as e:
        st.error(f"Error al leer la caja: {e}")
        box_list = []
    # Precalcular huellas y flags (blindado/robado) para la caja actual
    try:
        fps = []
        for _p in box_list:
            try:
                fps.append(pokemon_fingerprint(_p))
            except Exception:
                fps.append(None)
        fp_valid = [fp for fp in fps if isinstance(fp, str)]
        flags_map = get_flags_by_fingerprints(fp_valid) if fp_valid else {}
        blindados = set()
        robados = set()
        for fp, meta in flags_map.items():
            try:
                fj = meta.get("flags_json")
                if isinstance(fj, str) and fj.strip():
                    import json as _json
                    obj = _json.loads(fj)
                    if isinstance(obj, dict):
                        if obj.get("blindado"):
                            blindados.add(fp)
                        if obj.get("robado"):
                            robados.add(fp)
            except Exception:
                pass
    except Exception:
        fps = []
        blindados = set()
        robados = set()
    rows, cols = 5, 6
    idx = 0
    for _ in range(rows):
        row_cols = st.columns(cols)
        for cell in row_cols:
            with cell:
                if idx < len(box_list):
                    p = box_list[idx]
                    img_url = _sprite_url_from_p(p, prefer_animated=False)
                    title = p.get("species_name") or p.get("species")
                    subtitle = f"Lv.{p.get('level', '-')}"
                    html = _slot_card_html(
                        img_url=img_url,
                        title=title,
                        subtitle=subtitle,
                        img_w=BOX_IMG_W,
                        level=p.get("level", "Â¢Â¢Ã¢Å¡Â¬Â¢Ã¢Â¬Â"),
                        is_shiny=bool(p.get("is_shiny", False)),
                        gender=p.get("gender"),
                    )
                    # Mostrar tipos dentro de la tarjeta en lugar del nivel (cajas)
                    try:
                        types = species_types(
                            species_name=title,
                            form_index=p.get("form_index"),
                            form_name=p.get("form_name"),
                            gender=p.get("gender"),
                        )
                    except Exception:
                        types = []
                    subtitle = ""
                    html = _slot_card_html(
                        img_url=img_url,
                        title=title,
                        subtitle=subtitle,
                        img_w=BOX_IMG_W,
                        level=None,
                        is_shiny=bool(p.get("is_shiny", False)),
                        gender=p.get("gender"),
                        types=types,
                    )
                    st.markdown(html, unsafe_allow_html=True)
                    if st.button("Ver", key=f"box_{box_index}_{idx}"):
                        st.session_state.selected_pokemon = {
                            "from": "box", "box": box_index, "slot": idx + 1,
                            "species": title,
                            "nickname": p.get("nickname", ""),
                            "level": p.get("level", "-"),
                            "nature": p.get("nature", "-"),
                            "moves": p.get("moves", []),
                            "moves_detail": p.get("moves_detail"),
                            "form_name": p.get("form_name"),
                            "form_index": p.get("form_index"),
                            "is_shiny": p.get("is_shiny", False),
                            "gender": p.get("gender"),
                            "dex_id": p.get("dex_id"),
                            "ivs": p.get("ivs"),
                            "evs": p.get("evs"),
                            "held_item": p.get("held_item") or p.get("Item"),
                        }


def page_entrenadores_setup() -> None:
    """UI para cargar manualmente el bridge PKHeX (solo para tu propio perfil)."""
    is_own_profile = (
        st.session_state.get("trainer_selected") == st.session_state.get("user")
    )
    if not is_own_profile:
        return
    with st.expander(
        "Configurar lector de .sav (Bridge)",
        expanded=not st.session_state.get("pkhex_loaded", False),
    ):
        bridge_hint = st.session_state.get("pkhex_dll_path") or DEFAULT_DLL_HINT
        exe_in = st.text_input("Ruta a PKHeXBridge.exe (o carpeta)", value=bridge_hint)
        st.session_state.pkhex_mode = "auto"
        if st.button("Cargar lector", type="primary"):
            try:
                PKHeXRuntime.load(exe_in)
                st.session_state.pkhex_loaded = True
                st.session_state.pkhex_dll_path = exe_in
                st.success("Lector cargado correctamente.")
            except Exception as e:
                st.session_state.pkhex_loaded = False
                st.error(f"No se pudo cargar el lector: {e}")


def page_entrenadores_view() -> None:
    """Contenido principal de la pestaña Entrenadores para el entrenador seleccionado."""
    trainer = st.session_state.get("trainer_selected")
    current_user = st.session_state.get("user")
    is_own_profile = (trainer == current_user)
    _ensure_pokepaste_state()

    saves = list_user_saves(trainer) if trainer else []
    active_path = saves[0] if saves else None
    st.info(
        f"Guardado detectado para {trainer or '-'}: {Path(active_path).name if active_path else '(sin guardados)'}"
    )

    if not st.session_state.get("pkhex_loaded", False):
        if is_own_profile:
            st.warning("Configura el lector (bridge) para poder leer el .sav.")
        else:
            st.info("El guardado no está disponible en este momento.")
        return

    if not active_path:
        if is_own_profile:
            st.warning("Sube un .sav en la pestaña Saves.")
        else:
            st.info("Este entrenador no tiene guardados todavía.")
        return

    # Abrir .sav y leer meta
    try:
        save_path = Path(active_path)
        if not save_path.exists():
            st.error("El archivo .sav del entrenador no existe.")
            return
        sav_json = PKHeXRuntime.open_sav(save_path)
    except Exception as e:
        st.error(f"No se pudo abrir/validar el guardado: {e}")
        try:
            st.caption(f"Ruta del bridge actual: {get_bridge_path() or ''}")
        except Exception:
            pass
        return

    # Meta rápida de cajas (cantidad + nombres)
    try:
        box_count, box_names = get_box_meta_quick(sav_json, save_path=str(save_path))
    except Exception:
        box_count, box_names = 0, []

    # Resumen con retrato y KPIs
    _trainer_summary_with_portrait_ui(sav_json, box_count)

    # Equipo actual (con cache si hay ruta activa)
    try:
        active_spath = str(save_path) if save_path else None
        if active_spath:
            import os
            mtime = os.path.getmtime(active_spath)
            if st is not None:
                team = _cached_team(active_spath, mtime)
            else:
                team = extract_team(sav_json) or []
        else:
            team = extract_team(sav_json) or []
    except Exception:
        team = []
    _team_grid_ui_enhanced(team)

    # Pokepaste (editor para perfil propio, lectura para otros)
    st.markdown("---")
    st.subheader("Pokepaste del entrenador")
    pokes = st.session_state.get("pokepastes", {})
    existing = pokes.get(trainer or "", {})
    if is_own_profile:
        url_val = existing.get("url", "") if isinstance(existing, dict) else ""
        col1, col2 = st.columns([3,1])
        with col1:
            url_in = st.text_input("URL de Pokepaste", value=url_val, placeholder="https://pokepast.es/...")
        with col2:
            if st.button("Guardar Pokepaste", type="primary"):
                if not url_in.strip():
                    st.warning("Introduce una URL de Pokepaste.")
                else:
                    try:
                        txt = _fetch_pokepaste_text(url_in.strip())
                        team_pp = _parse_pokepaste(txt)
                        team_pp = [_sanitize_mon(m) for m in team_pp if m]
                        st.session_state.pokepastes[trainer] = {"url": url_in.strip(), "team": team_pp}
                        st.success("Pokepaste cargado y guardado.")
                    except Exception as e:
                        st.error(f"No se pudo cargar el Pokepaste: {e}")
        if st.button("Borrar Pokepaste"):
            st.session_state.pokepastes.pop(trainer, None)
            st.success("Pokepaste eliminado.")
        st.caption("Tu Pokepaste se reutiliza en la pestaña Copa para mostrar equipos.")
    _pokepaste_preview(existing)

    # Exportar equipo en formato Showdown (tematica competitiva)
    try:
        from dexdata import showdown_export as _sd_export
        if team:
            txt = _sd_export(team, include_ability=True, include_evs=False, include_ivs=False)
            with st.expander("Exportar equipo (Showdown)"):
                st.code(txt, language="")
                st.download_button(
                    label="Descargar .txt",
                    data=txt.encode("utf-8"),
                    file_name="equipo_showdown.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
    except Exception:
        pass

    # Panel de detalle del Pokémon seleccionado
    _pokemon_detail_panel()

    # Cuadrícula de cajas
    _boxes_grid_ui(sav_json, box_count, box_names, save_path=str(save_path))


def page_entrenadores() -> None:
    """Entrada principal de la pestaña Entrenadores (selector + contenido)."""
    st.title("Entrenadores")
    st.caption("Se alimenta del último .sav del entrenador seleccionado.")

    # Selector de entrenador
    users = list(USERS.keys())
    default_idx = 0
    try:
        cur = st.session_state.get("trainer_selected")
        if cur in users:
            default_idx = users.index(cur)
    except Exception:
        pass
    trainer = st.selectbox("Elige un entrenador", users, index=default_idx)
    st.session_state.trainer_selected = trainer

    # Intento de carga automática del bridge para el propio perfil
    # Intento de carga automática del bridge (sin UI manual)
    _try_auto_load_bridge()

    page_entrenadores_view()




# Re-define boxes grid to sanitize level default and avoid duplicate render
def _boxes_grid_ui(
    sav_json: dict, box_count: int, box_names: List[str], *, save_path: str | None = None
) -> None:
    st.subheader("PC (Cajas)")
    if not has_pc_data(sav_json, save_path=save_path):
        st.warning("PC no disponible. Revisa el Bridge si persiste.")
        return

    total_boxes = _resolve_total_boxes(box_count, box_names)
    virtual_names = list(box_names)[:total_boxes]
    if len(virtual_names) < total_boxes:
        start = len(virtual_names)
        virtual_names += [f"Caja {i+1}" for i in range(start, total_boxes)]

    box_index = st.selectbox(
        "Caja",
        options=list(range(total_boxes)),
        index=0,
        format_func=lambda i: virtual_names[i] if i < len(virtual_names) else f"Caja {i+1}",
    )

    try:
        if save_path and st is not None:
            import os
            mtime = os.path.getmtime(str(save_path))
            box_list = _cached_box(str(save_path), mtime, int(box_index))
        else:
            box_list = extract_box(sav_json, box_index, save_path=save_path)
    except Exception as e:
        st.error(f"Error al leer la caja: {e}")
        box_list = []

    # Precalcular huellas y flags (blindado/robado) para la caja actual
    try:
        fps = []
        for _p in box_list:
            try:
                fps.append(pokemon_fingerprint(_p))
            except Exception:
                fps.append(None)
        fp_valid = [fp for fp in fps if isinstance(fp, str)]
        flags_map = get_flags_by_fingerprints(fp_valid) if fp_valid else {}
        blindados = set()
        robados = set()
        for fp, meta in flags_map.items():
            try:
                fj = meta.get("flags_json")
                if isinstance(fj, str) and fj.strip():
                    import json as _json
                    obj = _json.loads(fj)
                    if isinstance(obj, dict):
                        if obj.get("blindado"):
                            blindados.add(fp)
                        if obj.get("robado"):
                            robados.add(fp)
            except Exception:
                pass
    except Exception:
        fps = []
        blindados = set()
        robados = set()

    rows, cols = 5, 6
    idx = 0
    for _ in range(rows):
        row_cols = st.columns(cols)
        for cell in row_cols:
            with cell:
                if idx < len(box_list):
                    p = box_list[idx]
                    img_url = _sprite_url_from_p(p, prefer_animated=False)
                    title = p.get("species_name") or p.get("species")
                    try:
                        types = species_types(
                            species_name=title,
                            form_index=p.get("form_index"),
                            form_name=p.get("form_name"),
                            gender=p.get("gender"),
                        )
                    except Exception:
                        types = []
                    html = _slot_card_html(
                        img_url=img_url,
                        title=title,
                        subtitle="",
                        img_w=BOX_IMG_W,
                        level=None,
                        is_shiny=bool(p.get("is_shiny", False)),
                        gender=p.get("gender"),
                        types=types,
                    )
                    st.markdown(html, unsafe_allow_html=True)
                    if st.button("Ver", key=f"box_{box_index}_{idx}"):
                        st.session_state.selected_pokemon = {
                            "from": "box",
                            "box": box_index,
                            "slot": idx + 1,
                            "species": title,
                            "nickname": p.get("nickname", ""),
                            "level": p.get("level", "-"),
                            "nature": p.get("nature", "-"),
                            "moves": p.get("moves", []),
                            "moves_detail": p.get("moves_detail"),
                            "form_name": p.get("form_name"),
                            "form_index": p.get("form_index"),
                            "is_shiny": p.get("is_shiny", False),
                            "gender": p.get("gender"),
                            "dex_id": p.get("dex_id"),
                            "ivs": p.get("ivs"),
                            "evs": p.get("evs"),
                            "held_item": p.get("held_item") or p.get("Item"),
                        }
                else:
                    st.markdown(_slot_empty_html(f"Slot {idx+1}"), unsafe_allow_html=True)
                idx += 1










# Rendimiento: caches de equipo y caja por save
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

def _active_save_for(trainer: str) -> str | None:
    try:
        saves = list_user_saves(trainer)
        if not saves:
            return None
        p = saves[0]
        return str(p)
    except Exception:
        return None

if st is not None:
    @st.cache_data(ttl=120, show_spinner=False)
    def _cached_team(save_path: str, mtime: float) -> List[dict]:
        try:
            sav_json = PKHeXRuntime.open_sav(save_path)
            return extract_team(sav_json, save_path=save_path) or []
        except Exception:
            return []

    @st.cache_data(ttl=120, show_spinner=False)
    def _cached_box(save_path: str, mtime: float, box_index: int) -> List[dict]:
        try:
            sav_json = PKHeXRuntime.open_sav(save_path)
            return extract_box(sav_json, box_index, save_path=save_path) or []
        except Exception:
            return []
