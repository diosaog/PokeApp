from __future__ import annotations

from html import escape
from typing import List
import streamlit as st

from app.entrenadores.cache import cached_box
from app.entrenadores.constants import DEAD_BOX_INDEX, TOTAL_BOXES
from app.entrenadores.sprites import sprite_url_from_p
from conex_pkhex import extract_box, has_pc_data


def _box_tile_html(*, img_url: str, title: str, box_index: int, slot_index: int) -> str:
    safe_title = escape(str(title or "Pokemon"))
    safe_url = escape(str(img_url or ""), quote=True)
    href = f"?box_pick={int(box_index)}-{int(slot_index)}"
    return (
        f"<a class='champ-box-tile-link' href='{href}' target='_self' "
        f"title='Ver {safe_title}'>"
        "<div class='champ-box-tile'>"
        f"<img src='{safe_url}' alt='{safe_title}'/>"
        "</div>"
        "</a>"
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

    rows, cols = 5, 6
    idx = 0
    for _ in range(rows):
        row_cols = st.columns(cols)
        for cell in row_cols:
            with cell:
                if idx < len(box_list):
                    p = box_list[idx]
                    img_url = sprite_url_from_p(p, prefer_animated=False)
                    title = p.get("species_name") or p.get("species")
                    html = _box_tile_html(
                        img_url=img_url,
                        title=str(title or "Pokemon"),
                        box_index=int(box_index),
                        slot_index=int(idx),
                    )
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div class='champ-box-tile champ-box-tile-empty' title='Slot {idx + 1}'></div>",
                        unsafe_allow_html=True,
                    )
                idx += 1
