from __future__ import annotations

import html as _html
import re

from app.entrenadores.sprites import sprite_url_from_p
from app.entrenadores.inventory import _item_icon_url
from app.ui.type_icons import type_icon_html, type_icons_html
from dexdata import (
    ability_desc_es,
    ability_name_es,
    item_name_es,
    move_info,
    move_name_es,
    species_types,
)


STAT_ORDER = (
    ("hp", "PS"),
    ("atk", "Ataque"),
    ("def", "Defensa"),
    ("spa", "At. Esp."),
    ("spd", "Def. Esp."),
    ("spe", "Velocidad"),
)

SPREAD_ORDER = (
    ("hp", "HP"),
    ("atk", "Atk"),
    ("def", "Def"),
    ("spa", "SpA"),
    ("spd", "SpD"),
    ("spe", "Spe"),
)


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


def _as_int(val) -> int | None:
    try:
        return int(val)
    except Exception:
        return None


def _bar_pct(value: object, *, cap: int = 255) -> int:
    number = _as_int(value)
    if number is None:
        return 0
    return max(4, min(100, int(round(number * 100 / cap))))


def _pokemon_types(p: dict) -> list[str]:
    species = str(p.get("species_name") or p.get("species") or "").strip()
    if not species:
        return []
    try:
        return species_types(
            species_name=species,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            gender=p.get("gender"),
            dex_id=p.get("dex_id"),
        )
    except Exception:
        return []


def _gender_parts(raw_gender: object) -> tuple[str, str]:
    raw = str(raw_gender or "").strip().upper()
    if raw.startswith("F"):
        return "&#9792;", "is-female"
    if raw.startswith("M"):
        return "&#9794;", "is-male"
    return "", ""


def _spread_grid(vals: dict) -> str:
    cells: list[str] = []
    for key, label in SPREAD_ORDER:
        value = _as_int(vals.get(key))
        text = str(value if value is not None else 0)
        cells.append(
            "<span class='pokemon-inspector-spread-cell'>"
            f"<b>{_html.escape(label)}</b><strong>{_html.escape(text)}</strong>"
            "</span>"
        )
    return "<div class='pokemon-inspector-spread'>" + "".join(cells) + "</div>"


def _section(title: str, content: str, *, extra_class: str = "") -> str:
    classes = "pokemon-inspector-panel"
    if extra_class:
        classes += f" {extra_class}"
    return (
        f"<section class='{classes}'>"
        f"<div class='pokemon-inspector-panel-title'>{_html.escape(title)}</div>"
        f"{content}"
        "</section>"
    )


def _move_type(move_name: str, move_id: object | None) -> tuple[str | None, dict]:
    try:
        info = move_info(str(move_name), move_id=_as_int(move_id)) or {}
    except Exception:
        info = {}
    move_type = info.get("type")
    return (str(move_type) if move_type else None), info


def _move_id_from_detail(move: object, detail: dict | None) -> object | None:
    if isinstance(detail, dict):
        found = detail.get("id") or detail.get("MoveId") or detail.get("move_id")
        if found is not None:
            return found
    try:
        match = re.search(r"\d+", str(move))
        if match and str(move).lower().startswith("move"):
            return int(match.group(0))
    except Exception:
        pass
    return None


def _moves_html(p: dict) -> str:
    moves = list(p.get("moves", []) or [])[:4]
    while len(moves) < 4:
        moves.append(None)
    details = p.get("moves_detail") or []

    rows: list[str] = []
    for idx, move in enumerate(moves):
        if not move:
            rows.append(
                "<div class='pokemon-inspector-move-row is-empty'>"
                "<span class='pokemon-inspector-move-type'>---</span>"
                "<span class='pokemon-inspector-move-name'>---</span>"
                "<span class='pokemon-inspector-move-pp'>PP --/--</span>"
                "</div>"
            )
            continue

        detail = details[idx] if idx < len(details) and isinstance(details[idx], dict) else None
        move_id = _move_id_from_detail(move, detail)
        move_type, info = _move_type(str(move), move_id)
        type_html = (
            type_icon_html(
                move_type,
                label=True,
                compact=True,
                class_name="move-type-badge--micro",
            )
            if move_type
            else "<span class='pokemon-inspector-move-type-fallback'>---</span>"
        )
        pp_total = _as_int(info.get("pp")) or 0
        pp_current = _as_int(detail.get("pp")) if detail else None
        if pp_current is None:
            pp_current = pp_total
        pp_text = f"{pp_current}/{pp_total}" if pp_total else "--/--"
        rows.append(
            "<div class='pokemon-inspector-move-row'>"
            f"<span class='pokemon-inspector-move-type'>{type_html}</span>"
            f"<span class='pokemon-inspector-move-name'>{_html.escape(_move_es(str(move)))}</span>"
            f"<span class='pokemon-inspector-move-pp'>PP { _html.escape(pp_text) }</span>"
            "</div>"
        )
    return _section("Movimientos", "".join(rows), extra_class="pokemon-inspector-moves")


def _stats_html(
    *,
    stx: dict,
    hp_text: str,
    hp_pct: int,
    up_key: str | None,
    down_key: str | None,
) -> str:
    rows: list[str] = []
    for key, label in STAT_ORDER:
        value = _fmt_stat(stx, key)
        classes = "pokemon-inspector-stat-row"
        if key == "hp":
            classes += " is-hp"
            pct = hp_pct
            value_text = hp_text
        else:
            pct = _bar_pct(value)
            value_text = value
        if up_key and key == up_key:
            classes += " is-boosted"
        if down_key and key == down_key:
            classes += " is-lowered"
        rows.append(
            f"<div class='{classes}'>"
            f"<span class='pokemon-inspector-stat-label'>{_html.escape(label)}</span>"
            "<span class='pokemon-inspector-stat-bar'>"
            f"<span style='width:{pct}%;'></span>"
            "</span>"
            f"<span class='pokemon-inspector-stat-value'>{_html.escape(value_text)}</span>"
            "</div>"
        )
    return _section("Estadisticas", "".join(rows), extra_class="pokemon-inspector-stats")


def _competitive_html(
    *,
    ability: str | None,
    ability_desc: str,
    nature_txt: str,
    ivs_display: dict,
    evs_display: dict,
) -> str:
    ability_name = _ability_es(str(ability)) if ability else "-"
    desc_html = (
        f"<p class='pokemon-inspector-ability-desc'>{_html.escape(str(ability_desc))}</p>"
        if ability_desc
        else ""
    )
    content = (
        "<div class='pokemon-inspector-data-grid'>"
        "<div class='pokemon-inspector-data-item'>"
        "<span>Naturaleza</span>"
        f"<strong>{_html.escape(str(nature_txt or '-'))}</strong>"
        "</div>"
        "<div class='pokemon-inspector-data-item'>"
        "<span>Habilidad</span>"
        f"<strong>{_html.escape(str(ability_name or '-'))}</strong>"
        f"{desc_html}"
        "</div>"
        "</div>"
        "<div class='pokemon-inspector-spread-block'>"
        "<span>IVs</span>"
        f"{_spread_grid(ivs_display)}"
        "</div>"
        "<div class='pokemon-inspector-spread-block'>"
        "<span>EVs</span>"
        f"{_spread_grid(evs_display)}"
        "</div>"
    )
    return _section("Datos competitivos", content, extra_class="pokemon-inspector-data")


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
    species_raw = str(p.get("species_name") or p.get("species") or "?").strip()
    nickname_raw = str(p.get("nickname") or "").strip()
    display_raw = (
        nickname_raw
        if nickname_raw and nickname_raw.lower() != species_raw.lower()
        else species_raw
    )
    species_line = species_raw if nickname_raw and nickname_raw.lower() != species_raw.lower() else ""
    display_name = _html.escape(display_raw or "?")
    species_name = _html.escape(species_line)

    gender_html, gender_cls = _gender_parts(p.get("gender"))
    gender_badge = (
        f"<span class='pokemon-inspector-gender {gender_cls}'>{gender_html}</span>"
        if gender_html
        else ""
    )

    level_raw = _as_int(p.get("level"))
    level_txt = f"Nv.{level_raw}" if level_raw is not None else "Nv.--"
    img_url = sprite_url_from_p(p, prefer_animated=True)
    raw_item = p.get("held_item") or p.get("item") or "-"
    item = _item_name_es(raw_item)
    item_icon = _item_icon_url(str(raw_item or item))
    item_icon_html = (
        "<img class='pokemon-inspector-item-icon' "
        f"src='{_html.escape(str(item_icon), quote=True)}' alt=''/>"
        if item_icon
        else ""
    )
    types_html = type_icons_html(
        _pokemon_types(p),
        label=True,
        compact=True,
        class_name="pokemon-type-badge type-badge--compact",
    )

    ps = _fmt_stat(stx, "hp")
    hp_max = _as_int(ps)
    hp_current = _as_int(p.get("hp_current") or p.get("current_hp") or p.get("hp")) or hp_max
    if hp_max and hp_current is not None:
        hp_pct = int(max(0, min(100, round(100 * hp_current / hp_max))))
        hp_text = f"{hp_current}/{hp_max}"
    else:
        hp_pct = 100
        hp_text = "--/--"

    ability_desc = ability_desc_es(str(ability)) if ability else ""
    header_subtitle = (
        f"<div class='pokemon-inspector-species'>{species_name}</div>"
        if species_name
        else ""
    )
    private_badge = "Privado" if is_own else "Vista publica"
    root_class = "pokemon-inspector is-own" if is_own else "pokemon-inspector is-public"

    hero_html = (
        "<div class='pokemon-inspector-hero'>"
        "<div class='pokemon-inspector-identity'>"
        "<div class='pokemon-inspector-kicker'>Revision Pokemon</div>"
        f"<div class='pokemon-inspector-name'>{display_name}</div>"
        f"{header_subtitle}"
        "<div class='pokemon-inspector-meta-row'>"
        f"<span class='pokemon-inspector-level'>{_html.escape(level_txt)}</span>"
        f"{gender_badge}"
        f"<span class='pokemon-inspector-visibility'>{private_badge}</span>"
        "</div>"
        f"<div class='pokemon-inspector-types'>{types_html}</div>"
        "<div class='pokemon-inspector-item'>"
        f"{item_icon_html}"
        "<span>Objeto</span>"
        f"<strong>{_html.escape(str(item))}</strong>"
        "</div>"
        "</div>"
        "<div class='pokemon-inspector-sprite'>"
        f"<img src='{_html.escape(str(img_url), quote=True)}' alt='{display_name}'/>"
        "</div>"
        "</div>"
    )

    body_html = (
        "<div class='pokemon-inspector-body'>"
        + _stats_html(
            stx=stx,
            hp_text=hp_text,
            hp_pct=hp_pct,
            up_key=up_key,
            down_key=down_key,
        )
        + (
            _competitive_html(
                ability=ability,
                ability_desc=ability_desc,
                nature_txt=nature_txt,
                ivs_display=ivs_display,
                evs_display=evs_display,
            )
            if is_own
            else ""
        )
        + _moves_html(p)
        + "</div>"
    )
    return f"<div class='{root_class}'>{hero_html}{body_html}</div>"
