from __future__ import annotations

import html as _html
import re
from typing import Any, Dict

from app.entrenadores.sprites import sprite_url_from_p
from dexdata import ability_desc_es, ability_name_es, item_name_es, move_info, move_name_es, type_color
from i18n import translate_type_es


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


def render_detail_html(
    *,
    p: dict,
    is_own: bool,
    stx: dict,
    up_key: str | None,
    down_key: str | None,
    ability: str | None,
    nature_txt: str,
    ivs_display: dict,
    evs_display: dict,
) -> str:
    def _as_int(val):
        try:
            return int(val)
        except Exception:
            return None

    def _style(*parts):
        return "; ".join(part.strip().rstrip(";") for part in parts if part)

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

    nature_row_style = _style(
        "padding:8px",
        "background:#8b95ed",
        "border-top:2px solid #6d73bd",
        "display:grid",
        "grid-template-columns:auto 1fr",
        "gap:8px",
        "align-items:center",
        "color:#f7f8ff",
    )
    nature_label_style = _style("font-size:11px")
    nature_value_style = _style(
        "background:#f7f6ef",
        "color:#2b2b2b",
        "padding:4px 6px",
        "border:2px solid #6a6a6a",
        "border-radius:6px",
        "font-size:11px",
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
    nature_value_text = _html.escape(str(nature_txt or "-"))

    order = [("hp", "HP"), ("atk", "Atk"), ("def", "Def"), ("spa", "SpA"), ("spd", "SpD"), ("spe", "Spe")]

    def _stat_line(vals: dict) -> str:
        parts = []
        for k, label in order:
            v = _as_int(vals.get(k))
            if v is None:
                v = 0
            parts.append(f"{label}:{v}")
        return " ".join(parts) if parts else "-"

    ivs_txt = _stat_line(ivs_display)
    evs_txt = _stat_line(evs_display)
    ivs_html = (
        "<div style='padding:8px; background:#8b95ed; border-top:2px solid #6d73bd;'>"
        "<div style='font-size:11px; margin-bottom:6px; color:#f7f8ff;'>IVs</div>"
        "<div style='background:#f7f6ef; color:#2b2b2b; padding:6px 8px; border:2px solid #6a6a6a; border-radius:6px; font-size:10px;'>"
        f"{_html.escape(ivs_txt)}</div>"
        "</div>"
    )
    evs_html = (
        "<div style='padding:8px; background:#8b95ed; border-top:2px solid #6d73bd;'>"
        "<div style='font-size:11px; margin-bottom:6px; color:#f7f8ff;'>EVs</div>"
        "<div style='background:#f7f6ef; color:#2b2b2b; padding:6px 8px; border:2px solid #6a6a6a; border-radius:6px; font-size:10px;'>"
        f"{_html.escape(evs_txt)}</div>"
        "</div>"
    )
    if not is_own:
        ivs_html = ""
        evs_html = ""

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

    nature_row = ""
    if is_own:
        nature_row = "<div style='{}'><div style='{}'>Naturaleza</div><div style='{}'>{}</div></div>".format(
            nature_row_style,
            nature_label_style,
            nature_value_style,
            nature_value_text,
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
        + nature_row
        + "<div style='{}'><div style='{}'>Habilid.</div><div style='{}'>{}</div></div>".format(
            ability_row_style,
            ability_label_style,
            ability_name_style,
            ability_name_text,
        )
        + "<div style='{}'>{}</div>".format(ability_desc_style, ability_desc_text)
        + ivs_html
        + evs_html
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
            move_id = None
            if idx < len(mdet) and isinstance(mdet[idx], dict):
                move_id = mdet[idx].get("id") or mdet[idx].get("MoveId") or mdet[idx].get("move_id")
            if move_id is None:
                try:
                    m = re.search(r"\d+", str(mv))
                    if m and str(mv).lower().startswith("move"):
                        move_id = int(m.group(0))
                except Exception:
                    move_id = None
            info = move_info(str(mv), move_id=move_id) or {}
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
    return detail_html

