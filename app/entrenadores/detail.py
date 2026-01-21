from __future__ import annotations

import html as _html
import streamlit as st

from app.entrenadores.constants import DETAIL_IMG_W
from app.entrenadores.sprites import sprite_url_from_p
from dexdata import ability_name_es, move_info, move_name_es, pokedex_data, type_color
from i18n import NATURES_ES, nature_display_es, translate_type_es
from showdown_sprites import showdown_id


def _extract_stats_from_p(p: dict) -> dict | None:
    try:
        stx = p.get("stats") if isinstance(p, dict) else None
        if isinstance(stx, dict) and any(k in stx for k in ("hp", "atk", "def", "spa", "spd", "spe")):
            out = {}
            for k in ("hp", "atk", "def", "spa", "spd", "spe"):
                v = stx.get(k)
                try:
                    out[k] = int(v)
                except Exception:
                    pass
            if out:
                return out

        keys = [("hp", "HP"), ("atk", "ATK"), ("def", "DEF"), ("spa", "SPA"), ("spd", "SPD"), ("spe", "SPE")]
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

        species = p.get("species_name") or p.get("species")
        if not species:
            return None
        sid = showdown_id(
            species_name=species,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            gender=p.get("gender"),
        )
        key = sid.replace("-", "").lower()
        pdx = pokedex_data()
        entry = pdx.get(key) or {}
        if not entry and "-" in sid:
            entry = pdx.get(sid.split("-", 1)[0].replace("-", "").lower()) or {}
        bstats = entry.get("baseStats") or {}
        if not bstats:
            return None

        def _to_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return default

        level = _to_int(p.get("level") or 50, 50)
        ivs = p.get("ivs") or {}
        evs = p.get("evs") or {}

        up = down = None
        nat = p.get("nature")
        key_nat = str(nat or "").strip()
        key_norm = key_nat.lower().capitalize()
        data = NATURES_ES.get(key_nat) or NATURES_ES.get(key_norm)
        if data:
            _name, up_long, down_long = data
            map_short = {
                "attack": "atk",
                "special-attack": "spa",
                "defense": "def",
                "special-defense": "spd",
                "speed": "spe",
            }
            up = map_short.get(up_long)
            down = map_short.get(down_long)

        def _nature_mult(stat_key: str) -> float:
            if up and stat_key == up:
                return 1.1
            if down and stat_key == down:
                return 0.9
            return 1.0

        def calc_hp(base, iv, ev) -> int:
            return int(((2 * base + iv + ev // 4) * level) // 100 + level + 10)

        def calc_other(base, iv, ev, mult) -> int:
            val = int(((2 * base + iv + ev // 4) * level) // 100 + 5)
            return int(val * mult)

        res = {}
        for k in ("hp", "atk", "def", "spa", "spd", "spe"):
            b = _to_int(bstats.get(k), None)
            if b is None:
                continue
            iv = _to_int((ivs or {}).get(k), 0)
            ev = _to_int((evs or {}).get(k), 0)
            if k == "hp":
                res[k] = calc_hp(b, iv, ev)
            else:
                res[k] = calc_other(b, iv, ev, _nature_mult(k))
        return res if res else None
    except Exception:
        return None


def _base_stats_at_level(mon: dict) -> dict:
    try:
        sid = showdown_id(
            species_name=mon.get("species_name") or mon.get("species") or "",
            form_index=mon.get("form_index"),
            form_name=mon.get("form_name"),
            gender=mon.get("gender"),
        )
        key = sid.replace("-", "").lower()
        pdx = pokedex_data()
        entry = pdx.get(key) or {}
        if not entry and "-" in sid:
            entry = pdx.get(sid.split("-", 1)[0].replace("-", "").lower()) or {}
        bstats = entry.get("baseStats") or {}
        lvl = int(mon.get("level") or 50)

        def hp_calc(base):
            return int(((2 * base) * lvl) // 100 + lvl + 10)

        def other_calc(base):
            return int(((2 * base) * lvl) // 100 + 5)

        res = {}
        for k in ("hp", "atk", "def", "spa", "spd", "spe"):
            b = bstats.get(k)
            if b is None:
                continue
            if k == "hp":
                res[k] = hp_calc(int(b))
            else:
                res[k] = other_calc(int(b))
        return res
    except Exception:
        return {}


def _nature_mods(nature_val):
    try:
        key = str(nature_val or "").strip()
        key_norm = key.lower().capitalize()
        data = NATURES_ES.get(key) or NATURES_ES.get(key_norm)
        if not data:
            return None, None
        _name, up, down = data
        map_short = {
            "attack": "atk",
            "special-attack": "spa",
            "defense": "def",
            "special-defense": "spd",
            "speed": "spe",
        }
        return map_short.get(up), map_short.get(down)
    except Exception:
        return None, None


def _move_es(name: str) -> str:
    manual = {
        "MagnetBomb": "Bomba Iman",
        "WakeUpSlap": "Espabila",
        "XScissor": "Tijera X",
        "SacredFire": "Fuego Sagrado",
        "Close Combat": "A Bocajarro",
        "Thunderbolt": "Rayo",
    }
    if name in manual:
        return manual[name]
    res = move_name_es(str(name))
    if res == name:
        try:
            import re
            spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", str(name)).replace("_", " ")
            res2 = move_name_es(spaced.strip())
            if res2 and res2 != name:
                return res2
        except Exception:
            pass
    return res


def _ability_es(name: str | None) -> str:
    if not name:
        return "-"
    manual = {
        "Blaze": "Mar Llamas",
        "Speed Boost": "Impulso",
        "Huge Power": "Potencia",
        "Intimidate": "Intimidacion",
        "Overgrow": "Espesura",
        "Torrent": "Torrente",
        "Swarm": "Enjambre",
        "Synchronize": "Sincronia",
    }
    if name in manual:
        return manual[name]
    res = ability_name_es(str(name))
    if res == name:
        try:
            import re
            spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", str(name)).replace("_", " ")
            res2 = ability_name_es(spaced.strip())
            if res2 and res2 != name:
                return res2
        except Exception:
            pass
    return res


def _item_name_es(name):
    if not name:
        return "-"
    id_str = str(name).lstrip("#")
    item_id_es = {
        "234": "Restos",
        "275": "Banda Focus",
        "210": "Gafas Elegidas",
        "220": "Cinta Elegida",
        "287": "Panuelo Elegido",
        "247": "Vidasfera",
        "226": "Periscopio",
        "221": "Roca del Rey",
        "213": "Hierba Blanca",
        "233": "Revestimiento Metalico",
        "230": "Piedra Alba",
        "634": "Capsula Habilidad",
        "632": "Chapa Dorada",
        "631": "Chapa Plateada",
    }
    if id_str.isdigit() and id_str in item_id_es:
        return item_id_es[id_str]
    if isinstance(name, (int, float)) or id_str.isdigit():
        return f"Objeto #{id_str}"
    m = {
        "Leftovers": "Restos",
        "Choice Specs": "Gafas Elegidas",
        "Choice Band": "Cinta Elegida",
        "Choice Scarf": "Panuelo Elegido",
        "Life Orb": "Vidasfera",
        "Focus Sash": "Banda Focus",
        "Scope Lens": "Periscopio",
        "King's Rock": "Roca del Rey",
        "White Herb": "Hierba Blanca",
        "Metal Coat": "Revestimiento Metalico",
        "Dawn Stone": "Piedra Alba",
        "Ability Capsule": "Capsula Habilidad",
        "Bottle Cap": "Chapa Plateada",
        "Gold Bottle Cap": "Chapa Dorada",
        "Ultra Ball": "Ultra Ball",
        "Repeat Ball": "Turno Ball",
        "Max Revive": "Revivir Maximo",
        "Helix Fossil": "Fosil Helix",
        "Oran Berry": "Baya Aranja",
        "Sitrus Berry": "Baya Zidra",
        "Cheri Berry": "Baya Zreza",
        "Chesto Berry": "Baya Ziuela",
        "Pecha Berry": "Baya Meloc",
        "Rawst Berry": "Baya Safre",
        "Aspear Berry": "Baya Perasi",
        "Persim Berry": "Baya Atania",
        "Salac Berry": "Baya Aslac",
        "Liechi Berry": "Baya Lichi",
        "Petaya Berry": "Baya Petaya",
        "Ganlon Berry": "Baya Ganlon",
        "Apicot Berry": "Baya Apicot",
        "Lansat Berry": "Baya Lansat",
        "Starf Berry": "Baya Starf",
    }
    return m.get(str(name), str(name))


def _fmt_stat(stx: dict, key: str) -> str:
    try:
        v = stx.get(key)
        return str(int(v)) if v is not None else "-"
    except Exception:
        return "-"


def pokemon_detail_panel() -> None:
    st.subheader("Detalle del Pokemon")
    p = st.session_state.get("selected_pokemon")
    if not p:
        st.markdown(
            "<div class='panel-dashed'>Selecciona un Pokemon del equipo o de una caja para ver sus datos.</div>",
            unsafe_allow_html=True,
        )
        return

    css = """
    <style>
    .ds-detail { display:grid; grid-template-columns: 1fr 1fr 1.6fr; gap: 12px; }
    .ds-col { display:flex; flex-direction:column; gap:8px; }
    .ds-card { border-radius:0; background:#0f1319; padding:10px 12px; border:1px solid #2a2f38; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), inset 0 0 0 1px rgba(255,255,255,0.02); }
    .ds-label { font-weight:800; letter-spacing:.3px; text-transform:uppercase; font-size:.72rem; color:#c9d1d9; margin-bottom:4px; }
    .ds-value { font-weight:700; color:#e6edf3; }
    .ds-sprite { display:flex; align-items:center; justify-content:center; }
    .ds-sprite img { image-rendering: pixelated; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.4)); }
    .hp-head { display:flex; align-items:center; justify-content:space-between; font-weight:700; margin-bottom:6px; }
    .hp-bar { height:8px; background:#1b2028; border-radius:0; overflow:hidden; border:1px solid #2a2f38; box-shadow: inset 0 1px 0 rgba(255,255,255,0.06); }
    .hp-fill { height:100%; background: linear-gradient(90deg, #8fd17e, #5bbf68); width:100%; }
    .stats-table { display:flex; flex-direction:column; gap:6px; }
    .stat-row { display:grid; grid-template-columns: 86px 54px 1fr; gap:6px; align-items:center; }
    .stat-label { font-weight:700; color:#e6edf3; padding:2px 8px; border-radius:0; background:#232832; border:1px solid #2f3540; text-transform:uppercase; letter-spacing:.2px; font-size:.72rem; }
    .stat-val { text-align:right; font-weight:700; opacity:.95; padding:2px 8px; border-radius:0; background:#121720; border:1px solid #2a2f38; min-width:48px; }
    .stat-bar { height:6px; background:#1b2028; border-radius:0; overflow:hidden; border:1px solid #2a2f38; }
    .stat-fill { height:100%; background:#9ca3af; width:var(--stat); }
    .stat-row.stat-up .stat-label, .stat-row.stat-up .stat-val { background:#6b1f1f; color:#ffe4e6; border-color:#7f1d1d; }
    .stat-row.stat-down .stat-label, .stat-row.stat-down .stat-val { background:#12324e; color:#e0f2fe; border-color:#0e3a5e; }
    .stat-row.stat-up .stat-fill { background:#ef4444; }
    .stat-row.stat-down .stat-fill { background:#38bdf8; }
    .moves-list { display:flex; flex-direction:column; gap:8px; }
    .move-row { display:grid; grid-template-columns: auto 1fr auto; align-items:center; gap:10px; padding:6px 8px; border-radius:0; border:1px solid #2a2f38; background:#0f1319; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); }
    .move-name { font-weight:700; }
    .type-pill { font-weight:800; letter-spacing:.5px; color:#0b0f14; background:#cbd5e1; border-radius:0; padding:2px 6px; text-transform:uppercase; font-size:.7rem; border:1px solid rgba(255,255,255,0.25); }
    .pp-box { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color:#e6edf3; text-align:right; min-width:54px; }
    .pp-text { font-weight:700; }
    .pp-bar { height:5px; background:#1b2028; border-radius:0; overflow:hidden; margin-top:4px; border:1px solid #2a2f38; }
    .pp-fill { height:100%; background:linear-gradient(90deg,#ffcc80,#fb8c00); width:var(--pp); }
    .caption { opacity:.85 }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    up_key, down_key = _nature_mods(p.get("nature"))
    is_own = st.session_state.get("trainer_selected") == st.session_state.get("user")
    stx = _extract_stats_from_p(p) or {}
    ability = p.get("ability") or p.get("Ability")
    if not is_own:
        p = dict(p)
        p["nature"] = None
        up_key, down_key = None, None
        stx = _base_stats_at_level(p)
        ability = None

    img_url = sprite_url_from_p(p, prefer_animated=True)
    raw_item = p.get("held_item") or p.get("item") or "-"
    item = _item_name_es(raw_item)
    ability_txt = _ability_es(str(ability)) if ability else ""

    ps = _fmt_stat(stx, "hp")
    labels = [("atk", "Ataque"), ("def", "Defensa"), ("spa", "At. Esp."), ("spd", "Def. Esp."), ("spe", "Veloc.")]
    stat_rows = []
    for key, label in labels:
        val = _fmt_stat(stx, key)
        try:
            val_int = int(val)
        except Exception:
            val_int = 0
        pct = max(0, min(100, int(round((val_int / 200) * 100)))) if val_int else 0
        row_cls = "stat-row"
        if up_key and key == up_key:
            row_cls += " stat-up"
        if down_key and key == down_key:
            row_cls += " stat-down"
        stat_rows.append(
            f"<div class='{row_cls}' style='--stat:{pct}%;'>"
            f"<div class='stat-label'>{label}</div>"
            f"<div class='stat-val'>{val}</div>"
            "<div class='stat-bar'><div class='stat-fill'></div></div>"
            "</div>"
        )
    stats_html = "<div class='ds-card'><div class='stats-table'>" + "".join(stat_rows) + "</div></div>"

    ivs_txt = ""
    if is_own:
        ivs = p.get("ivs") or {}
        order = [("hp", "HP"), ("atk", "Atk"), ("def", "Def"), ("spa", "SpA"), ("spd", "SpD"), ("spe", "Spe")]
        parts = []
        for k, label in order:
            v = ivs.get(k)
            try:
                v = int(v)
            except Exception:
                v = None
            if v is not None:
                parts.append(f"{label}:{v}")
        ivs_txt = " ".join(parts) if parts else "-"

    moves = list(p.get("moves", []) or [])
    moves = moves[:4]
    while len(moves) < 4:
        moves.append(None)
    mdet = p.get("moves_detail") or []
    mv_rows = []
    for idx, mv in enumerate(moves):
        if mv:
            mv_es = _move_es(str(mv))
            info = move_info(str(mv)) or {}
            t = info.get("type")
            t_es = translate_type_es(t).upper() if t else "-"
            color = type_color(t) if t else "#475569"
            pp_tot = info.get("pp") or 0
            pp_cur = None
            if idx < len(mdet) and isinstance(mdet[idx], dict):
                pp_cur = mdet[idx].get("pp")
            if pp_cur is None:
                pp_cur = pp_tot
            pp_text = f"{pp_cur}/{pp_tot}" if pp_tot else "--/--"
            try:
                perc = int(max(0, min(100, round(100 * pp_cur / pp_tot)))) if pp_tot else 0
            except Exception:
                perc = 0
        else:
            mv_es = "-"
            t_es = "---"
            color = "#475569"
            pp_text = "--/--"
            perc = 0
        mv_rows.append(
            "<div class='move-row' style='--pp:{}%;'>"
            "<span class='type-pill' style='background:{}; color:#fff'>{}</span>"
            "<div class='move-name'>{}</div>"
            "<div class='pp-box'><div class='pp-text'>{}</div>"
            "<div class='pp-bar'><div class='pp-fill'></div></div></div>"
            "</div>".format(perc, color, t_es, _html.escape(str(mv_es)), pp_text)
        )
    moves_html = "<div class='ds-card'><div class='moves-list'>" + "".join(mv_rows) + "</div></div>"

    item_html = (
        "<div class='ds-card'><div class='ds-label'>Objeto</div>"
        f"<div class='ds-value'>{_html.escape(str(item))}</div></div>"
    )
    ability_html = ""
    if ability_txt:
        ability_html = (
            "<div class='ds-card'><div class='ds-label'>Habilidad</div>"
            f"<div class='ds-value'>{_html.escape(str(ability_txt))}</div></div>"
        )
    ivs_html = ""
    if is_own:
        ivs_html = (
            "<div class='ds-card'><div class='ds-label'>IVs</div>"
            f"<div class='ds-value'>{_html.escape(str(ivs_txt))}</div></div>"
        )

    detail_html = (
        "<div class='ds-detail'>"
        "<div class='ds-col'>"
        f"<div class='ds-card ds-sprite'><img src='{_html.escape(str(img_url))}' width='{DETAIL_IMG_W}' alt='sprite'></div>"
        f"{item_html}{ability_html}"
        "</div>"
        "<div class='ds-col'>"
        "<div class='ds-card'>"
        f"<div class='hp-head'><span>PS</span><span>{ps}/{ps}</span></div>"
        "<div class='hp-bar'><div class='hp-fill'></div></div>"
        "</div>"
        f"{stats_html}{ivs_html}"
        "</div>"
        "<div class='ds-col'>"
        f"{moves_html}"
        "</div>"
        "</div>"
    )
    st.markdown(detail_html, unsafe_allow_html=True)
