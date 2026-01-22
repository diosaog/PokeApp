from __future__ import annotations

import html as _html
import streamlit as st

from app.entrenadores.constants import DETAIL_IMG_W
from app.entrenadores.sprites import sprite_url_from_p
from dexdata import ability_desc_es, ability_name_es, item_name_es, move_info, move_name_es, pokedex_data, type_color
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
    if isinstance(name, (int, float)) or id_str.isdigit():
        resolved = item_name_es(id_str)
        if resolved and resolved not in (id_str, f"#{id_str}"):
            return resolved
        return "Objeto"
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
    base = m.get(str(name), str(name))
    if base == str(name):
        resolved = item_name_es(str(name))
        if resolved:
            return resolved
    return base


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

    def _style(*parts):
        return "; ".join(p.strip().rstrip(";") for p in parts if p)

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
    ability_desc = ability_desc_es(str(ability)) if ability else ""

    ps = _fmt_stat(stx, "hp")
    hp_max = _as_int(ps)
    hp_cur = _as_int(p.get("hp_current") or p.get("current_hp") or p.get("hp")) or hp_max
    if hp_max and hp_cur is not None:
        hp_pct = int(max(0, min(100, round(100 * hp_cur / hp_max))))
        hp_text = f"{hp_cur}/{hp_max}"
    else:
        hp_pct = 100
        hp_text = "--/--"

    font_base = 'font-family:"Press Start 2P", monospace; font-size:12px; line-height:1.2; font-weight:900; text-shadow: 0 0 1.2px currentColor;'
    root_style = _style(font_base, "display:grid", "grid-template-columns:1.05fr 1fr 1fr", "gap:16px", "align-items:start")

    left_style = _style("background:#d7d4c0", "border:2px solid #9a9680", "border-radius:6px", "padding:8px", "color:#2b2b2b")
    header_style = _style(
        "background:#f1c258",
        "border:2px solid #c28f27",
        "border-radius:6px",
        "padding:6px 8px",
        "display:flex",
        "align-items:center",
        "justify-content:space-between",
        "color:#2b2b2b",
    )
    name_style = _style("display:flex", "align-items:center", "gap:6px", "font-size:12px", "color:#1f1f1f")
    gender_color = "#d6447a" if gender_cls == "f" else "#2f6ad9"
    gender_style = _style(
        "font-size:12px",
        "padding:2px 6px",
        "border:2px solid #6a6a6a",
        "border-radius:4px",
        "background:#f7f7f7",
        f"color:{gender_color}",
    )
    level_style = _style(
        "margin-top:6px",
        "background:#f7f6ef",
        "border:2px solid #b1ac96",
        "border-radius:4px",
        "padding:4px 6px",
        "font-size:11px",
        "color:#1f1f1f",
    )
    sprite_style = _style(
        "margin-top:8px",
        "background:repeating-linear-gradient(0deg, #e9e7d3 0 4px, #d7d5c1 4px 8px)",
        "border:2px solid #a29e86",
        "border-radius:6px",
        "padding:10px",
        "display:flex",
        "align-items:center",
        "justify-content:center",
        "min-height:180px",
    )
    item_box_style = _style("margin-top:8px", "border:2px solid #c28f27", "border-radius:6px", "overflow:hidden")
    item_label_style = _style(
        "background:#f1c258",
        "border-bottom:2px solid #c28f27",
        "padding:6px 8px",
        "font-size:11px",
        "color:#1f1f1f",
    )
    item_value_style = _style("background:#f7f6ef", "padding:6px 8px", "font-size:11px", "color:#1f1f1f")

    tab_wrap_style = _style("display:flex", "gap:4px", "margin-bottom:6px")
    tab_base_style = _style("width:18px", "height:18px", "border:2px solid #5a5a5a", "border-radius:3px", "display:inline-block")
    tab_colors = ["#9de1a5", "#9ad0ff", "#a3efe9", "#f2a1a1", "#c9a4ff", "#f3e28d"]
    tabs_html = "<div style='{}'>".format(tab_wrap_style)
    for color in tab_colors:
        tabs_html += "<div style='{}; background:{};'></div>".format(tab_base_style, color)
    tabs_html += "</div>"

    stats_screen_style = _style("border:2px solid #6168b2", "border-radius:6px", "overflow:hidden", "background:#7f88dd", "color:#f7f8ff")
    ps_row_style = _style(
        "padding:8px",
        "background:#8b95ed",
        "border-bottom:2px solid #6d73bd",
        "display:grid",
        "grid-template-columns:auto 1fr",
        "gap:8px",
        "align-items:center",
    )
    ps_label_style = _style("font-size:11px", "color:#f7f8ff")
    ps_value_style = _style(
        "justify-self:end",
        "background:#f7f6ef",
        "color:#2b2b2b",
        "padding:4px 6px",
        "border:2px solid #6a6a6a",
        "border-radius:6px",
        "font-size:11px",
    )
    ps_bar_style = _style(
        "grid-column:1 / -1",
        "height:10px",
        "background:#2b2b2b",
        "border:2px solid #2b2b2b",
        "border-radius:6px",
        "overflow:hidden",
    )
    ps_fill_style = _style("height:100%", "background:linear-gradient(90deg,#7be16f,#3ecf5b)")

    labels = [("atk", "Ataque"), ("def", "Defensa"), ("spa", "At. Esp."), ("spd", "Def. Esp."), ("spe", "Veloc.")]
    stat_rows = []
    for idx, (key, label) in enumerate(labels):
        row_bg = "#8b95ed" if idx % 2 == 0 else "#7d86db"
        row_style = _style(
            "display:grid",
            "grid-template-columns:1fr auto",
            "align-items:center",
            "padding:6px 8px",
            f"background:{row_bg}",
            "border-bottom:2px solid #6d73bd",
            "color:#f7f8ff",
        )
        val_bg = "#f7f6ef"
        if up_key and key == up_key:
            val_bg = "#f6e7b2"
        if down_key and key == down_key:
            val_bg = "#d4ecff"
        val_style = _style(
            f"background:{val_bg}",
            "border:2px solid #6a6a6a",
            "border-radius:6px",
            "padding:4px 6px",
            "min-width:64px",
            "text-align:right",
            "color:#2b2b2b",
            "font-size:11px",
        )
        stat_rows.append(
            "<div style='{}'><div style='font-size:11px;'>{}</div><div style='{}'>{}</div></div>".format(
                row_style,
                label,
                val_style,
                _fmt_stat(stx, key),
            )
        )

    ability_row_style = _style(
        "padding:8px",
        "background:#8b95ed",
        "border-top:2px solid #6d73bd",
        "display:grid",
        "grid-template-columns:auto 1fr",
        "gap:8px",
        "align-items:center",
        "color:#f7f8ff",
    )
    ability_label_style = _style("font-size:11px")
    ability_name_style = _style(
        "background:#f7f6ef",
        "color:#2b2b2b",
        "padding:4px 6px",
        "border:2px solid #6a6a6a",
        "border-radius:6px",
        "font-size:11px",
    )
    ability_desc_style = _style(
        "background:#f1e7b2",
        "border-top:2px solid #cbb777",
        "padding:8px",
        "color:#2b2b2b",
        "font-size:10px",
        "line-height:1.2",
        "min-height:40px",
        "white-space:normal",
        "word-break:break-word",
    )

    ability_name_text = _html.escape(ability_txt) if ability_txt else "-"
    ability_desc_text = _html.escape(ability_desc) if ability_desc else "-"

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
            "<div style='padding:8px; background:#8b95ed; border-top:2px solid #6d73bd;'>"
            "<div style='font-size:11px; margin-bottom:6px; color:#f7f8ff;'>IVs</div>"
            "<div style='background:#f7f6ef; color:#2b2b2b; padding:6px 8px; border:2px solid #6a6a6a; border-radius:6px; font-size:10px;'>"
            f"{_html.escape(ivs_txt)}</div>"
            "</div>"
        )

    pokeball_html = (
        "<span style='display:inline-block; width:14px; height:14px; border:2px solid #2a2a2a; "
        "border-radius:50%; background:linear-gradient(#d94134 0 50%, #f5f5f5 50% 100%); "
        "position:relative;'>"
        "<span style='position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); "
        "width:4px; height:4px; border:2px solid #2a2a2a; border-radius:50%; background:#f5f5f5;'></span>"
        "</span>"
    )
    gender_html = f"<div style='{gender_style}'>{gender_txt}</div>" if gender_txt else ""
    left_html = (
        f"<div style='{left_style}'>"
        f"<div style='{header_style}'>"
        f"<div style='{name_style}'>{pokeball_html}<span>{display_name}</span></div>"
        f"{gender_html}</div>"
        f"<div style='{level_style}'>{level_txt}</div>"
        f"<div style='{sprite_style}'><img src='{_html.escape(str(img_url))}' "
        f"style='image-rendering:pixelated; width:140px; height:auto;' alt='sprite'></div>"
        f"<div style='{item_box_style}'>"
        f"<div style='{item_label_style}'>Objeto</div>"
        f"<div style='{item_value_style}'>{_html.escape(str(item))}</div>"
        "</div></div>"
    )

    stats_html = (
        f"<div>{tabs_html}"
        f"<div style='{stats_screen_style}'>"
        f"<div style='{ps_row_style}'>"
        f"<div style='{ps_label_style}'>PS</div>"
        f"<div style='{ps_value_style}'>{hp_text}</div>"
        f"<div style='{ps_bar_style}'><div style='{ps_fill_style}; width:{hp_pct}%;'></div></div>"
        "</div>"
        + "".join(stat_rows)
        + "<div style='{}'><div style='{}'>Habilid.</div><div style='{}'>{}</div></div>".format(
            ability_row_style,
            ability_label_style,
            ability_name_style,
            ability_name_text,
        )
        + "<div style='{}'>{}</div>".format(ability_desc_style, ability_desc_text)
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
        move_row_style = _style(
            "display:grid",
            "grid-template-columns:auto 1fr auto",
            "align-items:center",
            "gap:8px",
            "padding:8px",
            "border-bottom:2px solid #c9756b",
            "background:#f1a39a",
        )
        move_type_style = _style(
            f"background:{color}",
            f"color:{text_color}",
            "border:2px solid #6a6a6a",
            "border-radius:6px",
            "padding:4px 6px",
            "font-size:10px",
            "text-transform:uppercase",
            "min-width:70px",
            "text-align:center",
        )
        move_name_style = _style("font-size:11px", "color:#2b2b2b")
        move_pp_style = _style(
            "display:flex",
            "align-items:center",
            "gap:6px",
            "background:#f7f6ef",
            "border:2px solid #6a6a6a",
            "border-radius:6px",
            "padding:4px 6px",
            "font-size:10px",
            "color:#2b2b2b",
        )
        mv_rows.append(
            "<div style='{}'><div style='{}'>{}</div><div style='{}'>{}</div>"
            "<div style='{}'><span>PP</span><span>{}</span></div></div>".format(
                move_row_style,
                move_type_style,
                t_es,
                move_name_style,
                _html.escape(str(mv_es)),
                move_pp_style,
                pp_text,
            )
        )

    moves_screen_style = _style("border:2px solid #c9756b", "border-radius:6px", "overflow:hidden", "background:#f1a39a")
    moves_html = f"<div>{tabs_html}<div style='{moves_screen_style}'>" + "".join(mv_rows) + "</div></div>"

    detail_html = f"<div style='{root_style}'>{left_html}{stats_html}{moves_html}</div>"
    st.markdown(detail_html, unsafe_allow_html=True)
