from __future__ import annotations

import base64
import mimetypes
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

import streamlit as st

from app.entrenadores.bridge import try_auto_load_bridge
from app.entrenadores.profile import find_trainer_image
from app.entrenadores.snapshot import get_trainer_snapshot
from app.juicios.penalties import get_user_penalties
from app.liga.context import current_jornada
from app.liga.matchup_styles import ensure_matchup_css
from app.tienda.money import money_breakdown_from_parts
from dexdata import (
    ability_desc_es,
    ability_name_es,
    item_name_es,
    move_desc_es,
    move_info,
    species_types,
    type_color,
)
from i18n import nature_display_es, translate_type_es
from showdown_sprites import showdown_sprite_url
from storage import get_team_lock
from utils import USERS, users_with_retired_last


IV_LABELS: tuple[tuple[str, str], ...] = (
    ("hp", "PS"),
    ("atk", "Atk"),
    ("def", "Def"),
    ("spa", "At. Esp"),
    ("spd", "Def. Esp"),
    ("spe", "Vel"),
)


@dataclass(frozen=True)
class MovePreview:
    name: str
    raw_name: str
    move_id: int | None
    type_name: str
    category: str
    power: str
    accuracy: str
    pp: str


def _cache_data(ttl: int = 20):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


@_cache_data(ttl=120)
def _img_uri(path: str, mtime: float | None = None) -> str:
    try:
        if not path:
            return ""
        mime = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def _division_for_player(player: str) -> str:
    divisions = st.session_state.get("league_divisions")
    if not isinstance(divisions, dict):
        return "-"
    if player in (divisions.get("A") or []):
        return "Liga A"
    if player in (divisions.get("B") or []):
        return "Liga B"
    return "-"


def _head_to_head(player_a: str, player_b: str) -> tuple[int, int]:
    wins_a = 0
    wins_b = 0
    matches = st.session_state.get("league_matches") or {}
    for divs in matches.values():
        if not isinstance(divs, dict):
            continue
        for division in ("A", "B"):
            for pair, winner in (divs.get(division) or {}).items():
                if not isinstance(pair, tuple) or len(pair) != 2:
                    continue
                p1, p2 = pair
                if {p1, p2} != {player_a, player_b}:
                    continue
                if winner == player_a:
                    wins_a += 1
                elif winner == player_b:
                    wins_b += 1
    return wins_a, wins_b


def _move_names(mon: dict) -> list[str]:
    moves = list(mon.get("moves") or [])
    if moves:
        return [str(move).strip() for move in moves if str(move).strip()][:4]

    detailed = []
    for move in list(mon.get("moves_detail") or []):
        if not isinstance(move, dict):
            continue
        name = str(move.get("name") or "").strip()
        if name:
            detailed.append(name)
    return detailed[:4]


def _safe_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def _move_id_from_detail(detail: dict | None) -> int | None:
    if not isinstance(detail, dict):
        return None
    for key in ("id", "MoveId", "move_id"):
        move_id = _safe_int(detail.get(key))
        if move_id:
            return move_id
    return None


def _fmt_power(value) -> str:
    power = _safe_int(value)
    return str(power) if power and power > 0 else "-"


def _fmt_accuracy(value) -> str:
    if value is True:
        return "-"
    accuracy = _safe_int(value)
    return f"{accuracy}%" if accuracy is not None else "-"


def _fmt_pp(total, current=None) -> str:
    pp_total = _safe_int(total)
    pp_current = _safe_int(current)
    if pp_total is None:
        return "-"
    if pp_current is None:
        return str(pp_total)
    return f"{pp_current}/{pp_total}"


def _category_es(category: str | None) -> str:
    return {
        "Physical": "Fisico",
        "Special": "Especial",
        "Status": "Estado",
    }.get(str(category or ""), str(category or "-"))


def _category_key(category: str | None) -> str:
    raw = str(category or "").strip().lower()
    if raw.startswith("phys"):
        return "physical"
    if raw.startswith("spec"):
        return "special"
    if raw.startswith("stat"):
        return "status"
    return "unknown"


def _move_entries(mon: dict) -> list[MovePreview]:
    raw_names = _move_names(mon)
    details = [d for d in list(mon.get("moves_detail") or []) if isinstance(d, dict)]
    count = min(4, max(len(raw_names), len(details)))
    entries: list[MovePreview] = []

    for idx in range(count):
        detail = details[idx] if idx < len(details) else {}
        raw = (
            raw_names[idx]
            if idx < len(raw_names)
            else str(detail.get("name") or "").strip()
        )
        move_id = _move_id_from_detail(detail)
        info = move_info(raw, move_id=move_id) or {}
        display_name = str(info.get("name") or raw or "Movimiento").strip()
        pp_current = detail.get("pp") if isinstance(detail, dict) else None
        entries.append(
            MovePreview(
                name=display_name,
                raw_name=raw or display_name,
                move_id=move_id,
                type_name=str(info.get("type") or "Normal").title(),
                category=str(info.get("category") or "-"),
                power=_fmt_power(info.get("power")),
                accuracy=_fmt_accuracy(info.get("accuracy")),
                pp=_fmt_pp(info.get("pp"), pp_current),
            )
        )
    return entries


def _pokemon_types(mon: dict) -> list[str]:
    species = str(mon.get("species_name") or mon.get("species") or "")
    try:
        return species_types(
            species_name=species,
            form_index=mon.get("form_index"),
            form_name=mon.get("form_name"),
            gender=mon.get("gender"),
            dex_id=mon.get("dex_id"),
        )
    except Exception:
        return []


def _text_color(hex_color: str) -> str:
    try:
        if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
            return "#ffffff"
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        lum = (r * 299 + g * 587 + b * 114) / 1000
        return "#10141a" if lum > 150 else "#ffffff"
    except Exception:
        return "#ffffff"


def _type_dot_html(type_name: str | None) -> str:
    t = str(type_name or "Normal").title()
    color = type_color(t)
    label = translate_type_es(t)
    return (
        f"<span class='battle-type-dot' title='{escape(label)}' "
        f"style='background:{color}; color:{_text_color(color)}'>{escape(label[:2].upper())}</span>"
    )


def _type_badge_html(type_name: str | None) -> str:
    t = str(type_name or "Normal").title()
    color = type_color(t)
    label = translate_type_es(t)
    return (
        f"<span class='battle-type-pill' style='background:{color}; "
        f"border-color:{color}; color:{_text_color(color)}'>{escape(label)}</span>"
    )


def _category_badge_html(category: str | None) -> str:
    key = _category_key(category)
    label = _category_es(category)
    return (
        f"<span class='battle-category-value battle-category-value-{key}'>"
        f"<span class='battle-category-icon battle-category-icon-{key}' aria-hidden='true'></span>"
        f"<span class='battle-category-text'>{escape(label)}</span>"
        "</span>"
    )


def _gender_html(gender: str | None) -> str:
    g = str(gender or "").strip().upper()
    if g.startswith("M"):
        return "<span class='battle-gender battle-gender-m'>M</span>"
    if g.startswith("F"):
        return "<span class='battle-gender battle-gender-f'>F</span>"
    return ""


def _held_item_name(mon: dict) -> str:
    found_numeric_item = False
    no_item_names = {
        "-",
        "0",
        "#0",
        "none",
        "no item",
        "(ningun objeto)",
        "(ningún objeto)",
    }
    for raw in (
        mon.get("held_item_id"),
        mon.get("ItemId"),
        mon.get("item_id"),
        mon.get("held_item"),
        mon.get("Item"),
        mon.get("item"),
    ):
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        if text.lower() in no_item_names:
            continue
        raw_id = text.lstrip("#")
        found_numeric_item = found_numeric_item or raw_id.isdigit()
        resolved = item_name_es(text)
        if not resolved or resolved.lower() in no_item_names:
            continue
        if raw_id.isdigit() and resolved in {text, raw_id}:
            continue
        if resolved:
            return resolved
    return "Objeto desconocido" if found_numeric_item else "-"


def _mon_ability(mon: dict) -> str:
    for key in ("ability", "Ability"):
        raw = mon.get(key)
        if raw is None:
            continue
        ability = str(raw).strip()
        if ability:
            return ability
    return ""


def _ability_display_es(name: str) -> str:
    if not name:
        return "-"
    resolved = ability_name_es(name)
    if resolved and resolved != name:
        return resolved
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ").strip()
    if spaced and spaced != name:
        resolved_spaced = ability_name_es(spaced)
        if resolved_spaced and resolved_spaced != spaced:
            return resolved_spaced
    return resolved or name


def _fmt_iv(value) -> str:
    try:
        return str(int(value))
    except Exception:
        return "-"


def _private_mon_info_html(mon: dict) -> str:
    ability = _mon_ability(mon)
    ability_name = _ability_display_es(ability) if ability else "-"
    ability_html = (
        "<div class='battle-private-line'>"
        "<span>Habilidad</span>"
        "<strong>-</strong>"
        "</div>"
    )
    if ability:
        ability_desc = ability_desc_es(ability)
        if not ability_desc:
            ability_desc = "Descripcion no disponible en espanol."
        ability_html = (
            "<details class='battle-ability-row'>"
            "<summary>"
            "<span>Habilidad</span>"
            f"<strong>{escape(ability_name)}</strong>"
            "</summary>"
            f"<div class='battle-ability-desc'>{escape(ability_desc)}</div>"
            "</details>"
        )

    nature = nature_display_es(mon.get("nature") or mon.get("Nature") or "") or "-"
    ivs = mon.get("ivs") if isinstance(mon.get("ivs"), dict) else {}
    ivs_html = "".join(
        (
            "<div class='battle-iv'>"
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(_fmt_iv(ivs.get(key)))}</strong>"
            "</div>"
        )
        for key, label in IV_LABELS
    )

    return (
        "<div class='battle-private-info'>"
        f"{ability_html}"
        "<div class='battle-private-line'>"
        "<span>Naturaleza</span>"
        f"<strong>{escape(nature)}</strong>"
        "</div>"
        "<div class='battle-ivs'>"
        "<span>IVs</span>"
        f"<div class='battle-ivs-grid'>{ivs_html}</div>"
        "</div>"
        "</div>"
    )


def _summary_snapshot(player: str) -> dict:
    from app.liga.ranking import current_points_total

    snapshot = get_trainer_snapshot(player)
    jornada = current_jornada()
    team_lock = get_team_lock(jornada, player)
    locked_team = list(team_lock.get("team") or []) if team_lock else []

    penalties = get_user_penalties(player)
    raw_dead_count = int(snapshot.get("dead_count") or 0)
    badges = int(snapshot.get("badge_count") or snapshot.get("badges") or 0)
    breakdown = money_breakdown_from_parts(
        player,
        badge_coins=4 * badges,
        penalties=penalties,
    )
    portrait = find_trainer_image(player)
    portrait_mtime = None
    try:
        if portrait:
            portrait_mtime = Path(portrait).stat().st_mtime
    except Exception:
        portrait_mtime = None

    return {
        "player": player,
        "division": _division_for_player(player),
        "points": current_points_total(
            player, raw_dead_count=raw_dead_count, penalties=penalties
        ),
        "coins": int(breakdown.get("available") or 0),
        "badges": badges,
        "dead_count": raw_dead_count,
        "team": locked_team or list(snapshot.get("team") or []),
        "save_name": str(snapshot.get("save_name") or "Sin save"),
        "team_lock": team_lock,
        "team_lock_jornada": jornada,
        "store_blocked": bool(penalties.get("store_blocked")),
        "portrait_uri": _img_uri(portrait, portrait_mtime) if portrait else "",
    }


def _summary_card_html(snapshot: dict) -> str:
    portrait_html = (
        f"<img src='{snapshot['portrait_uri']}' alt='{escape(snapshot['player'])}'/>"
        if snapshot.get("portrait_uri")
        else "<div class='matchup-avatar-fallback'>SIN<br/>RETRATO</div>"
    )
    status_chip = (
        "<span class='matchup-alert'>Tienda bloqueada</span>"
        if snapshot.get("store_blocked")
        else "<span class='matchup-ok'>Sin castigos de tienda</span>"
    )
    lock = snapshot.get("team_lock")
    if lock:
        lock_chip = (
            "<span class='matchup-alert'>Fijado tarde</span>"
            if lock.get("is_late")
            else "<span class='matchup-ok'>Equipo fijado</span>"
        )
    else:
        lock_chip = "<span class='matchup-alert'>Sin fijar</span>"
    return (
        "<div class='matchup-summary'>"
        "<div class='matchup-summary-head'>"
        f"<div class='matchup-avatar'>{portrait_html}</div>"
        "<div class='matchup-summary-meta'>"
        f"<div class='matchup-player'>{escape(snapshot['player'])}</div>"
        f"<div class='matchup-division'>{escape(snapshot['division'])}</div>"
        f"<div class='matchup-save'>{escape(snapshot['save_name'])}</div>"
        f"<div class='matchup-status-row'>{status_chip} {lock_chip}</div>"
        "</div>"
        "</div>"
        "<div class='matchup-metric-grid'>"
        f"<div class='matchup-metric'><span>Puntos</span><strong>{snapshot['points']:.1f}</strong></div>"
        f"<div class='matchup-metric'><span>Monedas</span><strong>{snapshot['coins']}</strong></div>"
        f"<div class='matchup-metric'><span>Medallas</span><strong>{snapshot['badges']}</strong></div>"
        f"<div class='matchup-metric'><span>Muertos</span><strong>{snapshot['dead_count']}</strong></div>"
        "</div>"
        "</div>"
    )


def _team_card_html(snapshot: dict) -> str:
    mons_html: list[str] = []
    team = list(snapshot.get("team") or [])[:6]
    for mon in team:
        species = str(mon.get("species_name") or mon.get("species") or "Pokemon")
        nickname = str(mon.get("nickname") or "").strip()
        title = nickname or species
        subtitle = species if nickname else f"Lv. {mon.get('level', '-')}"
        sprite = showdown_sprite_url(
            species_name=species,
            form_index=mon.get("form_index"),
            form_name=mon.get("form_name"),
            is_shiny=bool(mon.get("is_shiny")),
            gender=mon.get("gender"),
            prefer_animated=False,
        )
        item = _held_item_name(mon)
        moves = _move_entries(mon)
        moves_html = (
            "".join(
                (
                    "<div class='matchup-move'>"
                    f"{_type_dot_html(move.type_name)}"
                    f"<span>{escape(move.name)}</span>"
                    "</div>"
                )
                for move in moves
            )
            or "<div class='matchup-move matchup-move-empty'>(sin movimientos visibles)</div>"
        )
        mons_html.append(
            "<div class='matchup-mon'>"
            "<div class='matchup-mon-head'>"
            f"<img class='matchup-sprite' src='{sprite}' alt='{escape(species)}'/>"
            "<div class='matchup-mon-meta'>"
            f"<div class='matchup-mon-title'>{escape(title)}</div>"
            f"<div class='matchup-mon-sub'>{escape(subtitle)}</div>"
            f"<div class='matchup-mon-extra matchup-mon-item'>Objeto: {escape(item)}</div>"
            "</div>"
            "</div>"
            "<div class='matchup-move-list'>"
            f"{moves_html}"
            "</div>"
            "</div>"
        )

    while len(mons_html) < 6:
        mons_html.append(
            "<div class='matchup-mon matchup-mon-empty'>"
            "<div class='matchup-mon-title'>Slot vacio</div>"
            "<div class='matchup-mon-sub'>Sin Pokemon detectado</div>"
            "</div>"
        )

    return f"<div class='matchup-team-grid'>{''.join(mons_html)}</div>"


def _battle_team_html(
    snapshot: dict, *, board_label: str = "Rival", reveal_private: bool = False
) -> str:
    player = str(snapshot.get("player") or "")
    lock = snapshot.get("team_lock")
    lock_label = "Sin fijar"
    if lock:
        lock_label = "Fijado tarde" if lock.get("is_late") else "Equipo fijado"
    jornada = int(snapshot.get("team_lock_jornada") or current_jornada())
    team = list(snapshot.get("team") or [])[:6]
    cards: list[str] = []

    for idx in range(6):
        if idx >= len(team):
            cards.append(
                "<div class='battle-mon-card battle-empty-card'>"
                f"<div class='battle-slot-mark'>{idx + 1}</div>"
                "<div class='battle-empty-title'>Slot vacio</div>"
                "<div class='battle-empty-sub'>Sin Pokemon detectado</div>"
                "</div>"
            )
            continue

        mon = team[idx]
        species = str(mon.get("species_name") or mon.get("species") or "Pokemon")
        nickname = str(mon.get("nickname") or "").strip()
        title = nickname or species
        sprite = showdown_sprite_url(
            species_name=species,
            form_index=mon.get("form_index"),
            form_name=mon.get("form_name"),
            is_shiny=bool(mon.get("is_shiny")),
            gender=mon.get("gender"),
            prefer_animated=False,
        )
        types_html = "".join(_type_dot_html(t) for t in _pokemon_types(mon))
        item = _held_item_name(mon)
        level = escape(str(mon.get("level") or "-"))
        moves_html: list[str] = []
        for move_idx, move in enumerate(_move_entries(mon)):
            moves_html.append(
                "<details class='battle-move-row'>"
                "<summary class='battle-move-link'>"
                f"{_type_dot_html(move.type_name)}"
                f"<span>{escape(move.name)}</span>"
                "</summary>"
                f"{_move_detail_html(mon, move, player, inline=True)}"
                "</details>"
            )
        moves_block = (
            "".join(moves_html)
            or "<div class='battle-no-move'>Sin movimientos visibles</div>"
        )

        subtitle = (
            f"<div class='battle-species'>{escape(species)}</div>" if nickname else ""
        )
        private_html = _private_mon_info_html(mon) if reveal_private else ""
        cards.append(
            "<div class='battle-mon-card'>"
            f"<div class='battle-slot-mark'>{idx + 1}</div>"
            "<div class='battle-card-left'>"
            "<div class='battle-name-row'>"
            f"<span class='battle-mon-name'>{escape(title)}</span>"
            f"<span class='battle-types'>{types_html}</span>"
            "</div>"
            f"{subtitle}"
            f"<div class='battle-level'>Lv. {level} {_gender_html(mon.get('gender'))}</div>"
            f"<div class='battle-item'>Item: {escape(item)}</div>"
            f"{private_html}"
            "</div>"
            "<div class='battle-sprite-wrap'>"
            f"<img class='battle-sprite' src='{sprite}' alt='{escape(species)}'/>"
            "</div>"
            f"<div class='battle-moves'>{moves_block}</div>"
            "</div>"
        )

    return (
        "<div class='battle-board'>"
        "<div class='battle-board-top'>"
        f"<div><span>{escape(board_label)}</span><strong>{escape(player)}</strong></div>"
        f"<div><span>Jornada {jornada}</span><strong>{escape(lock_label)}</strong></div>"
        "</div>"
        "<div class='battle-team-grid'>"
        f"{''.join(cards)}"
        "</div>"
        "</div>"
    )


def _move_detail_html(
    mon: dict, move: MovePreview, player: str, *, inline: bool = False
) -> str:
    species = str(mon.get("species_name") or mon.get("species") or "Pokemon")
    nickname = str(mon.get("nickname") or "").strip()
    owner = escape(player)
    mon_name = escape(nickname or species)
    desc = move_desc_es(move.raw_name or move.name, move_id=move.move_id)
    if not desc:
        desc = "Descripcion no disponible en espanol."
    extra_class = " battle-move-detail-inline" if inline else ""
    return (
        f"<div class='battle-move-detail{extra_class}'>"
        "<div class='battle-detail-kicker'>Movimiento seleccionado</div>"
        "<div class='battle-detail-head'>"
        f"<div><strong>{escape(move.name)}</strong><span>{mon_name} | {owner}</span></div>"
        "</div>"
        "<div class='battle-detail-stats'>"
        f"<div><span>Tipo</span><strong>{_type_badge_html(move.type_name)}</strong></div>"
        f"<div><span>Clase</span><strong>{_category_badge_html(move.category)}</strong></div>"
        f"<div><span>Potencia</span><strong>{escape(move.power)}</strong></div>"
        f"<div><span>Precision</span><strong>{escape(move.accuracy)}</strong></div>"
        f"<div><span>PP</span><strong>{escape(move.pp)}</strong></div>"
        "</div>"
        f"<div class='battle-detail-desc'>{escape(desc)}</div>"
        "</div>"
    )


def _render_spectator_tab(available: list[str]) -> None:
    current_user = st.session_state.get("user")
    left_default = current_user if current_user in available else available[0]
    right_default = next(
        (player for player in available if player != left_default), available[1]
    )

    col_left, col_right = st.columns(2)
    with col_left:
        left_player = st.selectbox(
            "Entrenador A",
            available,
            index=available.index(left_default),
            key="matchup_left_player",
        )
    right_choices = [player for player in available if player != left_player]
    with col_right:
        right_player = st.selectbox(
            "Entrenador B",
            right_choices,
            index=right_choices.index(right_default)
            if right_default in right_choices
            else 0,
            key="matchup_right_player",
        )

    left_snapshot = _summary_snapshot(left_player)
    right_snapshot = _summary_snapshot(right_player)
    wins_left, wins_right = _head_to_head(left_player, right_player)
    st.markdown(
        (
            "<div class='matchup-versus'>"
            f"<strong>{escape(left_player)}</strong> vs <strong>{escape(right_player)}</strong>"
            f" | Duelo directo en liga: {wins_left} - {wins_right}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    summary_left, summary_right = st.columns(2, gap="large")
    with summary_left:
        st.markdown(_summary_card_html(left_snapshot), unsafe_allow_html=True)
        st.markdown(_team_card_html(left_snapshot), unsafe_allow_html=True)
    with summary_right:
        st.markdown(_summary_card_html(right_snapshot), unsafe_allow_html=True)
        st.markdown(_team_card_html(right_snapshot), unsafe_allow_html=True)


def _render_battle_tab(available: list[str]) -> None:
    current_user = str(st.session_state.get("user") or "").strip()
    own_player = next(
        (player for player in available if player.lower() == current_user.lower()),
        "",
    )
    previous_player = (
        st.session_state.get("battle_player")
        or st.session_state.get("battle_rival_player")
        or st.session_state.get("matchup_right_player")
    )
    default_player = (
        previous_player
        if previous_player in available
        else (own_player if own_player else available[0])
    )

    selected_player = st.selectbox(
        "Entrenador",
        available,
        index=available.index(default_player),
        key="battle_player",
    )

    is_own_selection = bool(own_player) and selected_player == own_player
    snapshot = _summary_snapshot(selected_player)
    st.markdown(
        _battle_team_html(
            snapshot,
            board_label="Tu equipo" if is_own_selection else "Rival",
            reveal_private=is_own_selection,
        ),
        unsafe_allow_html=True,
    )


def render_matchup_preview(players: list[str] | None = None) -> None:
    ensure_matchup_css()
    st.markdown(
        "<div class='matchup-shell'>Team Preview</div>", unsafe_allow_html=True
    )

    if not try_auto_load_bridge():
        st.warning(
            "No se ha podido cargar el Bridge para leer los saves. La previa necesita acceso al lector DS."
        )
        return

    known_users = set(USERS.keys())
    available = [
        player
        for player in users_with_retired_last(players or list(USERS.keys()))
        if player in known_users
    ]
    if len(available) < 2:
        st.info("No hay suficientes jugadores para generar una previa.")
        return

    mode_options = ["Espectador", "Combate"]
    if "matchup_preview_mode" not in st.session_state:
        st.session_state.matchup_preview_mode = "Espectador"
    mode = st.radio(
        "Modo de Team Preview",
        mode_options,
        horizontal=True,
        key="matchup_preview_mode",
        label_visibility="collapsed",
    )
    if mode == "Espectador":
        _render_spectator_tab(available)
    else:
        _render_battle_tab(available)
