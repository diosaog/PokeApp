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
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    .gb-font { font-family: 'Press Start 2P', monospace; font-size: 12px; line-height: 1.2; color:#2b2b2b; }
    .gb-font * { box-sizing: border-box; }
    .gb-left { background:#d7d4c0; border:2px solid #9a9680; border-radius:6px; padding:8px; }
    .gb-header { background:#f1c258; border:2px solid #c28f27; border-radius:6px; padding:6px 8px; display:flex; align-items:center; justify-content:space-between; }
    .gb-name { display:flex; align-items:center; gap:6px; font-size:0.9rem; }
    .gb-ball { width:14px; height:14px; border:2px solid #2a2a2a; border-radius:50%; background: linear-gradient(#d94134 0 50%, #f5f5f5 50% 100%); position:relative; }
    .gb-ball::after { content:""; position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); width:4px; height:4px; border:2px solid #2a2a2a; border-radius:50%; background:#f5f5f5; }
    .gb-gender { font-size:0.8rem; padding:2px 6px; border:2px solid #6a6a6a; border-radius:4px; background:#f7f7f7; }
    .gb-gender.f { color:#d6447a; }
    .gb-gender.m { color:#2f6ad9; }
    .gb-level { margin-top:6px; background:#f7f6ef; border:2px solid #b1ac96; border-radius:4px; padding:4px 6px; font-size:0.8rem; }
    .gb-sprite { margin-top:8px; background: repeating-linear-gradient(0deg, #e9e7d3 0 4px, #d7d5c1 4px 8px); border:2px solid #a29e86; border-radius:6px; padding:10px; display:flex; align-items:center; justify-content:center; min-height:170px; }
    .gb-sprite img { image-rendering: pixelated; width:140px; max-width:100%; height:auto; }
    .gb-item { margin-top:8px; border:2px solid #c28f27; border-radius:6px; overflow:hidden; }
    .gb-item-label { background:#f1c258; padding:6px 8px; border-bottom:2px solid #c28f27; font-size:0.8rem; }
    .gb-item-value { background:#f7f6ef; padding:6px 8px; font-size:0.85rem; }
    .gb-tabs { display:flex; gap:4px; margin-bottom:6px; }
    .gb-tab { width:18px; height:18px; border:2px solid #5a5a5a; border-radius:3px; background:#c7c7c7; }
    .gb-tab.green { background:#9de1a5; }
    .gb-tab.blue { background:#9ad0ff; }
    .gb-tab.cyan { background:#a3efe9; }
    .gb-tab.red { background:#f2a1a1; }
    .gb-tab.purple { background:#c9a4ff; }
    .gb-tab.yellow { background:#f3e28d; }
    .gb-screen { border:2px solid #6168b2; border-radius:6px; overflow:hidden; }
    .gb-stats { background:#7f88dd; color:#f7f8ff; }
    .gb-ps-row { padding:8px; background:#8b95ed; border-bottom:2px solid #6d73bd; display:grid; grid-template-columns: auto 1fr; gap:8px; align-items:center; }
    .gb-ps-label { font-size:0.85rem; }
    .gb-ps-value { justify-self:end; background:#f7f6ef; color:#2b2b2b; padding:4px 6px; border:2px solid #6a6a6a; border-radius:6px; font-size:0.8rem; }
    .gb-ps-bar { grid-column:1 / -1; height:10px; background:#2b2b2b; border-radius:6px; border:2px solid #2b2b2b; position:relative; overflow:hidden; }
    .gb-ps-fill { height:100%; background:linear-gradient(90deg,#7be16f,#3ecf5b); width:100%; }
    .gb-stat-row { display:grid; grid-template-columns: 1fr auto; align-items:center; padding:6px 8px; border-bottom:2px solid #6d73bd; }
    .gb-stat-row.row-a { background:#8b95ed; }
    .gb-stat-row.row-b { background:#7d86db; }
    .gb-stat-name { font-size:0.78rem; }
    .gb-stat-value { background:#f7f6ef; color:#2b2b2b; padding:4px 6px; border:2px solid #6a6a6a; border-radius:6px; font-size:0.8rem; min-width:64px; text-align:right; }
    .gb-stat-row.up .gb-stat-value { background:#f6e7b2; }
    .gb-stat-row.down .gb-stat-value { background:#d4ecff; }
    .gb-ability { background:#8b95ed; border-top:2px solid #6d73bd; padding:8px; }
    .gb-ability-label { margin-bottom:6px; font-size:0.78rem; }
    .gb-ability-name { background:#f7f6ef; color:#2b2b2b; padding:6px 8px; border:2px solid #6a6a6a; border-radius:6px; font-size:0.8rem; }
    .gb-ivs { background:#8b95ed; border-top:2px solid #6d73bd; padding:8px; }
    .gb-ivs-label { margin-bottom:6px; font-size:0.78rem; }
    .gb-ivs-value { background:#f7f6ef; color:#2b2b2b; padding:6px 8px; border:2px solid #6a6a6a; border-radius:6px; font-size:0.7rem; }
    .gb-moves { background:#f1a39a; border-color:#c9756b; }
    .gb-move-row { display:grid; grid-template-columns: auto 1fr auto; align-items:center; gap:8px; padding:8px; border-bottom:2px solid #c9756b; background:#f1a39a; }
    .gb-move-type { font-size:0.72rem; padding:4px 6px; border:2px solid #6a6a6a; border-radius:6px; background:#cfcfcf; text-transform:uppercase; }
    .gb-move-name { font-size:0.78rem; color:#2b2b2b; }
    .gb-move-pp { display:flex; align-items:center; gap:6px; background:#f7f6ef; border:2px solid #6a6a6a; border-radius:6px; padding:4px 6px; font-size:0.75rem; color:#2b2b2b; }
    .gb-pp-label { font-size:0.7rem; }
    .gb-pp-val { font-size:0.75rem; }
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

    def _as_int(val):
        try:
            return int(val)
        except Exception:
            return None

    def _text_color(hex_color: str) -> str:
        try:
            if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
                return "#1f1f1f"
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            lum = (r * 299 + g * 587 + b * 114) / 1000
            return "#1f1f1f" if lum > 140 else "#f7f7f7"
        except Exception:
            return "#1f1f1f"

    species = str(p.get("species_name") or p.get("species") or "?").strip()
    nickname = str(p.get("nickname") or "").strip()
    display_name = nickname if nickname and nickname.lower() != species.lower() else species
    display_name = _html.escape(display_name or "?")

    gender_raw = str(p.get("gender") or "").strip().upper()
    if gender_raw.startswith("F"):
        gender_txt = "F"
        gender_cls = "f"
    elif gender_raw.startswith("M"):
        gender_txt = "M"
        gender_cls = "m"
    else:
        gender_txt = ""
        gender_cls = ""

    level_txt = "Nv.--"
    level_raw = _as_int(p.get("level"))
    if level_raw is not None:
        level_txt = f"Nv.{level_raw}"

    img_url = sprite_url_from_p(p, prefer_animated=True)
    raw_item = p.get("held_item") or p.get("item") or "-"
    item = _item_name_es(raw_item)
    ability_txt = _ability_es(str(ability)) if ability else ""

    ps = _fmt_stat(stx, "hp")
    hp_max = _as_int(ps)
    hp_cur = _as_int(p.get("hp_current") or p.get("current_hp") or p.get("hp")) or hp_max
    if hp_max and hp_cur is not None:
        hp_pct = int(max(0, min(100, round(100 * hp_cur / hp_max))))
        hp_text = f"{hp_cur}/{hp_max}"
    else:
        hp_pct = 100
        hp_text = "--/--"

    labels = [("atk", "Ataque"), ("def", "Defensa"), ("spa", "At. Esp."), ("spd", "Def. Esp."), ("spe", "Veloc.")]
    stat_rows = []
    for idx, (key, label) in enumerate(labels):
        row_cls = "gb-stat-row row-a" if idx % 2 == 0 else "gb-stat-row row-b"
        if up_key and key == up_key:
            row_cls += " up"
        if down_key and key == down_key:
            row_cls += " down"
        val = _fmt_stat(stx, key)
        stat_rows.append(
            f"<div class='{row_cls}'><div class='gb-stat-name'>{label}</div>"
            f"<div class='gb-stat-value'>{val}</div></div>"
        )

    ability_html = ""
    if ability_txt:
        ability_html = (
            "<div class='gb-ability'>"
            "<div class='gb-ability-label'>Habilidad</div>"
            f"<div class='gb-ability-name'>{_html.escape(ability_txt)}</div>"
            "</div>"
        )

    ivs_html = ""
    if is_own:
        ivs = p.get("ivs") or {}
        order = [("hp", "HP"), ("atk", "Atk"), ("def", "Def"), ("spa", "SpA"), ("spd", "SpD"), ("spe", "Spe")]
        parts = []
        for k, label in order:
            v = _as_int(ivs.get(k))
            if v is not None:
                parts.append(f"{label}:{v}")
        ivs_txt = " ".join(parts) if parts else "-"
        ivs_html = (
            "<div class='gb-ivs'>"
            "<div class='gb-ivs-label'>IVs</div>"
            f"<div class='gb-ivs-value'>{_html.escape(ivs_txt)}</div>"
            "</div>"
        )

    tabs_html = (
        "<div class='gb-tabs'>"
        "<div class='gb-tab green'></div>"
        "<div class='gb-tab blue'></div>"
        "<div class='gb-tab cyan'></div>"
        "<div class='gb-tab red'></div>"
        "<div class='gb-tab purple'></div>"
        "<div class='gb-tab yellow'></div>"
        "</div>"
    )

    left_html = (
        "<div class='gb-font gb-left'>"
        "<div class='gb-header'>"
        f"<div class='gb-name'><span class='gb-ball'></span><span>{display_name}</span></div>"
        + (f"<div class='gb-gender {gender_cls}'>{gender_txt}</div>" if gender_txt else "")
        + "</div>"
        f"<div class='gb-level'>{level_txt}</div>"
        f"<div class='gb-sprite'><img src='{_html.escape(str(img_url))}' width='{DETAIL_IMG_W}' alt='sprite'></div>"
        "<div class='gb-item'>"
        "<div class='gb-item-label'>Objeto</div>"
        f"<div class='gb-item-value'>{_html.escape(str(item))}</div>"
        "</div>"
        "</div>"
    )

    stats_html = (
        "<div class='gb-font'>"
        f"{tabs_html}"
        "<div class='gb-screen gb-stats'>"
        "<div class='gb-ps-row'>"
        f"<div class='gb-ps-label'>PS</div><div class='gb-ps-value'>{hp_text}</div>"
        f"<div class='gb-ps-bar'><div class='gb-ps-fill' style='width:{hp_pct}%;'></div></div>"
        "</div>"
        + "".join(stat_rows)
        + ability_html
        + ivs_html
        + "</div></div>"
    )

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
            t_es = translate_type_es(t).upper() if t else "---"
            color = type_color(t) if t else "#cfcfcf"
            text_color = _text_color(color)
            pp_tot = info.get("pp") or 0
            pp_cur = None
            if idx < len(mdet) and isinstance(mdet[idx], dict):
                pp_cur = mdet[idx].get("pp")
            if pp_cur is None:
                pp_cur = pp_tot
            pp_text = f"{pp_cur}/{pp_tot}" if pp_tot else "--/--"
        else:
            mv_es = "---"
            t_es = "---"
            color = "#cfcfcf"
            text_color = _text_color(color)
            pp_text = "--/--"
        mv_rows.append(
            "<div class='gb-move-row'>"
            f"<div class='gb-move-type' style='background:{color}; color:{text_color};'>{t_es}</div>"
            f"<div class='gb-move-name'>{_html.escape(str(mv_es))}</div>"
            "<div class='gb-move-pp'><span class='gb-pp-label'>PP</span>"
            f"<span class='gb-pp-val'>{pp_text}</span></div>"
            "</div>"
        )

    moves_html = (
        "<div class='gb-font'>"
        f"{tabs_html}"
        "<div class='gb-screen gb-moves'>"
        + "".join(mv_rows)
        + "</div></div>"
    )

    colL, colM, colR = st.columns([1.1, 1.15, 1.15], gap="large")
    with colL:
        st.markdown(left_html, unsafe_allow_html=True)
    with colM:
        st.markdown(stats_html, unsafe_allow_html=True)
    with colR:
        st.markdown(moves_html, unsafe_allow_html=True)
