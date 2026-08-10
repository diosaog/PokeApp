from __future__ import annotations

from html import escape
from typing import List
import streamlit as st

from app.entrenadores.cache import cached_box
from app.entrenadores.constants import DEAD_BOX_INDEX, TOTAL_BOXES
from app.entrenadores.sprites import sprite_url_from_p
from app.ui.type_icons import type_icons_html
from conex_pkhex import extract_box, has_pc_data
from dexdata import species_types, type_color


def _pokemon_types(p: dict) -> list[str]:
    species = str(p.get("species_name") or p.get("species") or "")
    if not species:
        return []
    try:
        return species_types(
            species_name=species,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            gender=p.get("gender"),
        )
    except Exception:
        return []


def _box_tile_html(
    *,
    img_url: str,
    title: str,
    subtitle: str,
    level: object,
    types: list[str],
    box_index: int,
    slot_index: int,
    selected: bool = False,
    shiny: bool = False,
) -> str:
    safe_title = escape(str(title or "Pokemon"))
    safe_subtitle = escape(str(subtitle or ""))
    safe_url = escape(str(img_url or ""), quote=True)
    level_txt = "-" if level in (None, "") else str(level)
    type_list = [str(t) for t in (types or [])[:2] if str(t or "").strip()]
    type_labels = ", ".join(type_list) if type_list else "Tipo desconocido"
    title_attr = escape(
        f"{title or 'Pokemon'} | Lv.{level_txt} | {type_labels}",
        quote=True,
    )
    type_html = type_icons_html(type_list, compact=True, label=False, class_name="champ-box-type")
    type_rails = "".join(
        f"<span style='--rail-color:{escape(type_color(t), quote=True)}'></span>"
        for t in type_list
    )
    if not type_rails:
        type_rails = "<span></span>"
    glow = type_color(type_list[0]) if type_list else "#5da2ff"
    classes = ["champ-box-tile"]
    if selected:
        classes.append("is-selected")
    if shiny:
        classes.append("is-shiny")
    href = f"?box_pick={int(box_index)}-{int(slot_index)}"
    return (
        f"<a class='champ-box-tile-link' href='{href}' target='_self' "
        f"title='{title_attr}'>"
        f"<div class='{' '.join(classes)}' style='--box-glow:{escape(glow, quote=True)}'>"
        f"<span class='champ-box-slot-no'>{int(slot_index) + 1:02d}</span>"
        f"<span class='champ-box-level'>Lv.{escape(level_txt)}</span>"
        "<span class='champ-box-sprite-stage'>"
        f"<img src='{safe_url}' alt='{safe_title}'/>"
        "</span>"
        f"<span class='champ-box-name'>{safe_title}</span>"
        f"<span class='champ-box-species'>{safe_subtitle}</span>"
        f"<span class='champ-box-types'>{type_html}</span>"
        f"<span class='champ-box-type-rails'>{type_rails}</span>"
        "</div>"
        "</a>"
    )


def _empty_box_tile_html(slot_index: int) -> str:
    return (
        "<div class='champ-box-tile champ-box-tile-empty' "
        f"title='Slot {int(slot_index) + 1}'>"
        f"<span class='champ-box-slot-no'>{int(slot_index) + 1:02d}</span>"
        "<span class='champ-box-empty-mark'></span>"
        "</div>"
    )


def _select_box_pokemon(p: dict, *, box_index: int, slot_index: int, title: str) -> None:
    st.session_state.selected_pokemon = {
        "from": "box",
        "box": box_index,
        "slot": slot_index + 1,
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
        "ability": p.get("ability") or p.get("Ability"),
        "held_item": p.get("held_item") or p.get("Item"),
    }


def resolve_total_boxes(box_count: int, box_names: List[str]) -> int:
    try:
        if box_count and int(box_count) > 0:
            return min(int(box_count), TOTAL_BOXES)
    except Exception:
        pass
    if box_names:
        return min(len(box_names), TOTAL_BOXES)
    return TOTAL_BOXES


def muertos_box_index(box_count: int) -> int:
    total_boxes = resolve_total_boxes(box_count, [])
    return max(0, min(DEAD_BOX_INDEX, total_boxes - 1))


def boxes_grid_ui(
    sav_json: dict,
    box_count: int,
    box_names: List[str],
    *,
    save_path: str | None = None,
    pc_ok: bool | None = None,
    mtime: float | None = None,
) -> None:
    st.subheader("PC (Cajas)")
    if pc_ok is None:
        try:
            pc_ok = has_pc_data(sav_json, save_path=save_path)
        except Exception:
            pc_ok = False
    if not pc_ok:
        st.warning("PC no disponible. Revisa el Bridge si persiste.")
        return

    total_boxes = resolve_total_boxes(box_count, box_names)
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
            if mtime is None:
                import os
                mtime = os.path.getmtime(str(save_path))
            box_list = cached_box(str(save_path), mtime, int(box_index))
        else:
            box_list = extract_box(sav_json, box_index, save_path=save_path)
    except Exception as e:
        st.error(f"Error al leer la caja: {e}")
        box_list = []

    try:
        raw_pick = st.query_params.get("box_pick", "")
        if isinstance(raw_pick, list):
            raw_pick = raw_pick[0] if raw_pick else ""
        box_raw, slot_raw = str(raw_pick or "").split("-", 1)
        picked_box = int(box_raw)
        picked_slot = int(slot_raw)
        if picked_box == int(box_index) and 0 <= picked_slot < len(box_list):
            p = box_list[picked_slot]
            title = str(p.get("species_name") or p.get("species") or "Pokemon")
            _select_box_pokemon(
                p,
                box_index=int(box_index),
                slot_index=picked_slot,
                title=title,
            )
            try:
                del st.query_params["box_pick"]
            except Exception:
                pass
    except Exception:
        pass

    selected_ref = st.session_state.get("selected_pokemon") or {}
    try:
        selected_box = int(selected_ref.get("box"))
        selected_slot = int(selected_ref.get("slot")) - 1
    except Exception:
        selected_box = -1
        selected_slot = -1

    tiles: list[str] = []
    for idx in range(30):
        if idx < len(box_list):
            p = box_list[idx]
            img_url = sprite_url_from_p(p, prefer_animated=False)
            species = str(p.get("species_name") or p.get("species") or "Pokemon")
            nickname = str(p.get("nickname") or "").strip()
            title = nickname or species
            subtitle = species if nickname and nickname.lower() != species.lower() else ""
            types = _pokemon_types(p)
            tiles.append(
                _box_tile_html(
                    img_url=img_url,
                    title=str(title or "Pokemon"),
                    subtitle=subtitle,
                    level=p.get("level", "-"),
                    types=types,
                    box_index=int(box_index),
                    slot_index=int(idx),
                    selected=(int(box_index) == selected_box and int(idx) == selected_slot),
                    shiny=bool(p.get("is_shiny", False)),
                )
            )
        else:
            tiles.append(_empty_box_tile_html(idx))

    occupied = min(len(box_list), 30)
    free = max(0, 30 - occupied)
    box_name = str(virtual_names[int(box_index)])
    is_dead_box = int(box_index) == muertos_box_index(total_boxes)
    occupancy_pct = int(round((occupied / 30) * 100)) if occupied else 0
    dot_html = "".join(
        f"<span class='{'is-filled' if i < occupied else ''}'></span>"
        for i in range(30)
    )
    shell_classes = "champ-box-grid-shell"
    if is_dead_box:
        shell_classes += " is-dead-box"

    st.markdown(
        f"<div class='{shell_classes}' style='--box-fill:{occupancy_pct}%'>"
        "<div class='champ-box-grid-toolbar champ-box-grid-toolbar-single'>"
        "<div class='champ-box-control champ-box-control-wide'>"
        "<span class='champ-box-kicker'>PC / Cajas</span>"
        f"<strong>{escape(box_name)}</strong>"
        "</div>"
        "<div class='champ-box-meta'>"
        f"<span>{occupied}/30 Pokemon</span>"
        f"<span>{free} libres</span>"
        "</div>"
        "</div>"
        "<div class='champ-box-occupancy'>"
        "<div class='champ-box-occupancy-bar'><span></span></div>"
        f"<div class='champ-box-occupancy-dots'>{dot_html}</div>"
        "</div>"
        "<div class='champ-box-grid'>"
        f"{''.join(tiles)}"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
