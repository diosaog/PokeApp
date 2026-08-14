from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape

import streamlit as st

from app.discord_notify import (
    discord_notifications_enabled,
    notify_league_match_results_async,
    notify_league_round_finished_detail,
    notify_missing_team_locks_async,
)
from app.entrenadores.trainer_flags import is_trainer_retired, status_labels_for
from app.liga.divisions import division_a_size_for_count, movement_count_for_divisions
from app.liga.league_styles import ensure_league_css
from app.liga.permissions import is_league_admin
from app.liga.ranking import (
    all_filled,
    clear_ranking_caches,
    final_podium,
    finalize,
    general_table_sorted,
    get_matches_for,
    max_jornadas,
    recompute_round,
)
from app.liga.snapshots import (
    ROUND_SNAPSHOTS_STATE_KEY,
    snapshot_for_round,
    snapshot_standings,
)
from app.liga.state import ensure_state, persist_state, restore_state
from app.liga.table_summary import (
    coins_for_user as _coins_for_user,
    fmt_points as _fmt_points,
    league_round_result_groups as _league_round_result_groups,
    league_round_summary_lines as _league_round_summary_lines,
    league_table_html as _league_table_html,
    league_table_notification_rows as _league_table_notification_rows,
    players_from_match_map as _players_from_match_map,
)
from app.juicios.penalties import clear_penalty_caches
from app.tienda.catalog import get_catalog
from app.tienda.discounts import schedule_shop_promotions
from app.tienda.money import clear_money_caches
from storage import (
    clear_purchases,
    expire_shop_discounts_through_jornada,
    list_team_locks,
    settings_get,
    settings_clear_cache,
    settings_get_uncached,
    settings_set,
)
from utils import active_users, users_with_retired_last


_NOTIFY_SENT_KEY_PREFIX = "league_round_notify_sent"
_NOTIFY_STATUS_KEY_PREFIX = "league_round_notify_status"
_FLASH_MESSAGES_KEY = "_league_flash_messages"
_CLEAR_EDIT_BUFFERS_NEXT_KEY = "_league_clear_edit_buffers_next"
_TEAM_LOCKS_MISSING_NOTIFY_PREFIX = "team_locks_missing_notify"
def _clear_league_page_caches() -> None:
    try:
        settings_clear_cache("league_state")
    except Exception:
        pass
    clear_penalty_caches()
    clear_money_caches()
    clear_ranking_caches()


def _queue_flash(kind: str, message: str) -> None:
    messages = st.session_state.setdefault(_FLASH_MESSAGES_KEY, [])
    messages.append((str(kind or "info"), str(message or "")))


def _render_flash_messages() -> None:
    messages = st.session_state.pop(_FLASH_MESSAGES_KEY, [])
    for kind, message in messages:
        if not message:
            continue
        fn = getattr(st, kind, st.info)
        try:
            fn(message)
        except Exception:
            st.info(message)


def _clear_league_edit_buffers() -> None:
    for key in (
        "league_tmp",
        "league_tmp_prev",
        "league_prev_edit_active",
        "league_div_A",
        "league_div_B",
    ):
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        key_s = str(key)
        if (
            key_s.startswith("A_")
            or key_s.startswith("B_")
            or key_s.startswith("PREV_A_")
            or key_s.startswith("PREV_B_")
            or key_s.startswith("_league_round_notify_attempted_")
        ):
            st.session_state.pop(key, None)


def _schedule_clear_league_edit_buffers() -> None:
    st.session_state[_CLEAR_EDIT_BUFFERS_NEXT_KEY] = True


def _clear_local_league_state() -> None:
    for key in (
        "league_tramo",
        "league_active",
        "league_divisions",
        "league_results",
        "league_matches",
        "league_movements",
        "league_round_snapshots",
        "league_temp_order",
        "_league_state_hash",
        "_league_state_error",
    ):
        st.session_state.pop(key, None)
    _clear_league_edit_buffers()


def _sync_hall_of_fame_silent() -> None:
    try:
        from app.interfaz.hall_of_fame import sync_hall_of_fame_from_sources

        sync_hall_of_fame_from_sources()
    except Exception:
        pass


def _current_user_can_resend_summary() -> bool:
    return str(st.session_state.get("user") or "").strip().lower() == "anto"


def _current_user_can_manage_league() -> bool:
    return is_league_admin(st.session_state.get("user"))


def _require_league_admin_ui() -> bool:
    if _current_user_can_manage_league():
        return True
    st.error("Solo Anto puede modificar el estado oficial de Liga.")
    return False


def _notify_missing_team_locks_once(round_no: int) -> None:
    if not discord_notifications_enabled():
        return
    key = f"{_TEAM_LOCKS_MISSING_NOTIFY_PREFIX}:{int(round_no)}"
    try:
        if settings_get(key):
            return
    except Exception:
        pass
    locks = list_team_locks(int(round_no))
    locked_users = {
        str(lock.get("user") or "")
        for lock in locks
        if lock.get("team")
    }
    missing = [
        user
        for user in active_users().keys()
        if user not in locked_users
    ]
    notify_missing_team_locks_async(jornada=int(round_no), missing=missing)
    try:
        settings_set(key, "1")
    except Exception:
        pass


def _notify_sent_key(round_no: int) -> str:
    return f"{_NOTIFY_SENT_KEY_PREFIX}:{int(round_no)}"


def _notify_status_key(round_no: int) -> str:
    return f"{_NOTIFY_STATUS_KEY_PREFIX}:{int(round_no)}"


def _latest_closed_round() -> int | None:
    try:
        current = int(st.session_state.get("league_tramo") or 1)
    except Exception:
        current = 1
    last_round = current - 1
    if last_round <= 0:
        return None
    data = (st.session_state.get("league_matches") or {}).get(last_round)
    if not data:
        return None
    try:
        if all_filled(data.get("A", {})) and all_filled(data.get("B", {})):
            return int(last_round)
    except Exception:
        return None
    return None


def _notification_already_sent(round_no: int) -> bool:
    try:
        raw = settings_get_uncached(_notify_sent_key(round_no))
        return raw not in (None, "", "0", "false", "False")
    except Exception:
        return False


def _store_notification_status(round_no: int, *, ok: bool, message: str) -> None:
    payload = {
        "round": int(round_no),
        "ok": bool(ok),
        "message": str(message or ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        settings_set(
            _notify_status_key(round_no), json.dumps(payload, ensure_ascii=False)
        )
        if ok:
            settings_set(_notify_sent_key(round_no), payload["updated_at"])
    except Exception:
        pass


def _send_league_round_notification(
    round_no: int, *, force: bool = False
) -> tuple[bool, str]:
    if not force and _notification_already_sent(round_no):
        return True, "El resumen de esta jornada ya constaba como enviado."

    round_data = (st.session_state.get("league_matches") or {}).get(int(round_no))
    if not round_data:
        return False, "No hay datos de enfrentamientos para esa jornada."

    table = general_table_sorted()
    podium = table[:3] if int(round_no) >= max_jornadas(round_no) else None
    ok, message = notify_league_round_finished_detail(
        round_no=int(round_no),
        rows=_league_table_notification_rows(table),
        round_results=_league_round_result_groups(round_data),
        summary_lines=_league_round_summary_lines(
            table=table,
            movements=st.session_state.get("league_movements", {}).get(
                int(round_no), {}
            ),
            podium=podium,
        ),
    )
    _store_notification_status(int(round_no), ok=ok, message=message)
    return ok, message


def _auto_notify_latest_closed_round() -> None:
    if not discord_notifications_enabled():
        return
    round_no = _latest_closed_round()
    if round_no is None:
        return
    attempt_key = f"_league_round_notify_attempted_{round_no}"
    if st.session_state.get(attempt_key) or _notification_already_sent(round_no):
        return
    st.session_state[attempt_key] = True
    ok, message = _send_league_round_notification(round_no)
    if ok:
        st.success(f"Aaron Avisa ha enviado el resumen de la jornada {round_no}.")
    else:
        st.warning(f"Aaron Avisa no pudo enviar la jornada {round_no}: {message}")


def _render_final_podium() -> None:
    podium = final_podium()
    if not podium:
        return
    st.markdown(
        _section_heading_html("Clasificacion final"),
        unsafe_allow_html=True,
    )
    labels = ["Ganador", "Segundo puesto", "Tercer puesto"]
    cols = st.columns(3)
    for idx, col in enumerate(cols):
        with col:
            if idx < len(podium):
                user, pts = podium[idx]
                st.markdown(
                    (
                        "<div class='panel-ghost'>"
                        f"<div class='title'>{labels[idx]}</div>"
                        f"<div class='value'>{user}</div>"
                        f"<div style='margin-top:6px; color:#9aa3ab;'>Puntos: {_fmt_points(pts)}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    (
                        "<div class='panel-dashed'>"
                        f"<div class='title'>{labels[idx]}</div>"
                        "<div style='margin-top:6px;'>-</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )


def _league_header_html(
    *,
    tramo: int,
    max_rounds: int,
    player_count: int,
    division_a_size: int,
    division_b_size: int,
    is_active: bool,
    read_only: bool,
    finalized: bool,
) -> str:
    status = "Finalizada" if finalized else ("En edicion" if is_active else "Lista")
    if read_only:
        status = "Consulta"
    status_cls = " is-live" if is_active else ""
    visible_round = min(int(tramo), int(max_rounds)) if max_rounds else int(tramo)
    return f"""
<div class="league-hero">
  <div class="league-hero-main">
    <div class="league-kicker">Competicion</div>
    <div class="league-title">Liga</div>
    <div class="league-subtitle">Jornada {int(visible_round)} de {int(max_rounds)} - {escape(status)}</div>
  </div>
  <div class="league-hero-grid">
    <div class="league-status-card{status_cls}">
      <span>Estado</span>
      <strong>{escape(status)}</strong>
    </div>
    <div class="league-status-card">
      <span>Entrenadores activos</span>
      <strong>{int(player_count)}</strong>
    </div>
    <div class="league-status-card">
      <span>Liga A</span>
      <strong>{int(division_a_size)} plazas</strong>
    </div>
    <div class="league-status-card">
      <span>Liga B</span>
      <strong>{int(division_b_size)} plazas</strong>
    </div>
  </div>
</div>
"""


def _section_heading_html(title: str, subtitle: str = "") -> str:
    subtitle_html = (
        f"<div class='league-section-copy'>{escape(subtitle)}</div>" if subtitle else ""
    )
    return (
        "<div class='league-section-heading'>"
        f"<div class='league-section-title'>{escape(title)}</div>"
        f"{subtitle_html}"
        "</div>"
    )


def _league_status_badges_html(user: str) -> str:
    labels = status_labels_for(user)
    if not labels:
        return ""
    badges = []
    for label in labels:
        slug = str(label or "").strip().lower()
        badges.append(
            "<span class='league-trainer-badge "
            f"league-trainer-badge--{escape(slug)}'>"
            f"{escape(str(label))}"
            "</span>"
        )
    return "<span class='league-trainer-badges'>" + "".join(badges) + "</span>"


def _division_card_html(
    title: str,
    players: list[str],
    *,
    start_pos: int = 1,
    range_label: str | None = None,
    variant: str = "a",
    badges: dict[str, str] | None = None,
    points_by_user: dict[str, str] | None = None,
    coins_by_user: dict[str, int] | None = None,
    current_user: str | None = None,
) -> str:
    badges = badges or {}
    points_by_user = points_by_user or {}
    coins_by_user = coins_by_user or {}
    current_key = str(current_user or "").strip().lower()
    rows: list[str] = []
    for offset, user in enumerate(players):
        pos = start_pos + offset
        user_text = str(user)
        user_key = user_text.strip().lower()
        badge = badges.get(str(user), "")
        badge_html = ""
        if badge:
            badge_cls = "up" if badge.lower() == "sube" else "down"
            badge_html = (
                "<span class='league-movement-badge "
                f"league-movement-badge--{badge_cls}'>"
                f"{escape(badge)}"
                "</span>"
            )
        row_classes = ["league-card-player"]
        if current_key and user_key == current_key:
            row_classes.append("is-current-player")
        labels = [str(label).strip().lower() for label in status_labels_for(user_text)]
        if "retirado" in labels:
            row_classes.append("is-retired-player")
        if "robado" in labels:
            row_classes.append("is-robbed-player")
        points = points_by_user.get(user_text, "0.0")
        coins = coins_by_user.get(user_text, 0)
        rows.append(
            f"<div class='{' '.join(row_classes)}'>"
            f"<div class='league-card-pos'>{int(pos)}</div>"
            "<div class='league-card-main'>"
            f"<div class='league-card-player-name'>{escape(user_text)}</div>"
            f"{_league_status_badges_html(user_text)}"
            "</div>"
            "<div class='league-card-score'>"
            f"<strong>{escape(points)}</strong><span>pts</span>"
            "</div>"
            "<div class='league-card-coins'>"
            f"<strong>{int(coins)}</strong><span>mon</span>"
            "</div>"
            f"{badge_html}"
            "</div>"
        )

    if not rows:
        rows.append("<div class='league-card-empty'>Sin jugadores</div>")

    safe_range = range_label or f"{start_pos}-{start_pos + len(players) - 1}"
    return (
        f"<div class='league-division-card is-{escape(variant)}'>"
        "<div class='league-division-head'>"
        f"<div class='league-division-name'>{escape(title)}</div>"
        f"<div class='league-division-range'>{escape(safe_range)}</div>"
        "</div>"
        "<div class='league-card-list'>"
        + "".join(rows)
        + "</div></div>"
    )


def _division_grid_html(
    players_a: list[str],
    players_b: list[str],
    *,
    start_b: int,
    title_a: str = "Liga A",
    title_b: str = "Liga B",
    badges_a: dict[str, str] | None = None,
    badges_b: dict[str, str] | None = None,
    points_by_user: dict[str, str] | None = None,
    coins_by_user: dict[str, int] | None = None,
    current_user: str | None = None,
) -> str:
    end_a = len(players_a)
    end_b = start_b + len(players_b) - 1 if players_b else start_b - 1
    return (
        "<div class='league-division-grid'>"
        + _division_card_html(
            title_a,
            players_a,
            start_pos=1,
            range_label=f"1-{end_a}" if end_a else "Sin plazas",
            variant="a",
            badges=badges_a,
            points_by_user=points_by_user,
            coins_by_user=coins_by_user,
            current_user=current_user,
        )
        + _division_card_html(
            title_b,
            players_b,
            start_pos=start_b,
            range_label=f"{start_b}-{end_b}" if players_b else "Sin plazas",
            variant="b",
            badges=badges_b,
            points_by_user=points_by_user,
            coins_by_user=coins_by_user,
            current_user=current_user,
        )
        + "</div>"
    )


def _history_round_html(
    *,
    round_no: int,
    rows_a: list[tuple[str, int, str]],
    rows_b: list[tuple[str, int, str]],
    a_len: int,
    b_start: int,
    b_end: int,
) -> str:
    def _history_card(
        title: str,
        rows: list[tuple[str, int, str]],
        *,
        range_label: str,
        variant: str,
    ) -> str:
        row_html: list[str] = []
        for user, pos, movement in rows:
            badge_html = ""
            if movement:
                cls = "up" if movement == "Sube" else "down"
                badge_html = (
                    "<span class='league-movement-badge "
                    f"league-movement-badge--{cls}'>"
                    f"{escape(movement)}"
                    "</span>"
                )
            row_html.append(
                "<div class='league-card-player is-history-row'>"
                f"<div class='league-card-pos'>{int(pos)}</div>"
                f"<div class='league-card-player-name'>{escape(str(user))}</div>"
                f"{badge_html}"
                "</div>"
            )
        if not row_html:
            row_html.append("<div class='league-card-empty'>Sin jugadores</div>")
        return (
            f"<div class='league-division-card is-{escape(variant)}'>"
            "<div class='league-division-head'>"
            f"<div class='league-division-name'>{escape(title)}</div>"
            f"<div class='league-division-range'>{escape(range_label)}</div>"
            "</div>"
            "<div class='league-card-list'>"
            + "".join(row_html)
            + "</div></div>"
        )

    card_a = _history_card(
        "Liga A",
        rows_a,
        range_label=f"1-{int(a_len)}",
        variant="a",
    )
    card_b = _history_card(
        "Liga B",
        rows_b,
        range_label=f"{int(b_start)}-{int(b_end)}" if rows_b else "Sin plazas",
        variant="b",
    )
    return (
        f"<div class='league-history-title'>Tramo {int(round_no)}</div>"
        "<div class='league-history-grid'>"
        f"{card_a}{card_b}"
        "</div>"
    )


def _changed_match_notifications(
    round_no: int, data: dict, tmp_divs: dict
) -> list[dict]:
    notifications: list[dict] = []
    for div_key, div_label in (("A", "Liga A"), ("B", "Liga B")):
        for (p1, p2), old_winner in (data.get(div_key, {}) or {}).items():
            key = f"{p1} vs {p2}"
            new_winner = (tmp_divs.get(div_key, {}) or {}).get(key)
            if new_winner not in (p1, p2) or new_winner == old_winner:
                continue
            notifications.append(
                {
                    "round_no": int(round_no),
                    "division": div_label,
                    "player1": p1,
                    "player2": p2,
                    "winner": new_winner,
                }
            )
    return notifications


def _render_previous_round_editor(
    *, prev_tramo: int, current_tramo: int, read_only: bool = False
) -> None:
    data = st.session_state.get("league_matches", {}).get(prev_tramo)
    st.markdown(
        _section_heading_html(
            f"Modificar jornada anterior (Tramo {prev_tramo})",
            "Recalcula puntos, monedas y divisiones desde ese cierre.",
        ),
        unsafe_allow_html=True,
    )
    if not data:
        st.info("No hay datos guardados para la jornada anterior.")
        return

    tmp_all = st.session_state.setdefault("league_tmp_prev", {})
    tmp_divs = tmp_all.setdefault(prev_tramo, {"A": {}, "B": {}})

    for div in ("A", "B"):
        for (p1, p2), winner in data.get(div, {}).items():
            key = f"{p1} vs {p2}"
            default_winner = winner if winner in (p1, p2) else p1
            tmp_divs[div].setdefault(key, default_winner)

    a_len = len(_players_from_match_map(data.get("A", {})))
    b_len = len(_players_from_match_map(data.get("B", {})))
    b_start = a_len + 1
    b_end = b_start + b_len - 1 if b_len else b_start - 1

    with st.form(f"form_prev_results_{prev_tramo}"):
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**Liga A (jornada anterior)**")
            for (p1, p2), _winner in data.get("A", {}).items():
                key = f"{p1} vs {p2}"
                current = tmp_divs["A"].get(key, p1)
                opts = [p1, p2]
                idx = 0 if current == p1 else 1
                pick = st.selectbox(
                    key, opts, index=idx, key=f"PREV_A_{prev_tramo}_{p1}_{p2}"
                )
                tmp_divs["A"][key] = pick
        with cB:
            st.markdown(f"**Liga B (posiciones {b_start}-{b_end})**")
            for (p1, p2), _winner in data.get("B", {}).items():
                key = f"{p1} vs {p2}"
                current = tmp_divs["B"].get(key, p1)
                opts = [p1, p2]
                idx = 0 if current == p1 else 1
                pick = st.selectbox(
                    key, opts, index=idx, key=f"PREV_B_{prev_tramo}_{p1}_{p2}"
                )
                tmp_divs["B"][key] = pick

        submitted = st.form_submit_button(
            "Guardar cambios jornada anterior",
            disabled=read_only,
        )
        if submitted:
            if read_only or not _require_league_admin_ui():
                return
            match_notifications = _changed_match_notifications(
                prev_tramo, data, tmp_divs
            )
            for p1, p2 in list(data.get("A", {}).keys()):
                data["A"][(p1, p2)] = tmp_divs["A"].get(f"{p1} vs {p2}")
            for p1, p2 in list(data.get("B", {}).keys()):
                data["B"][(p1, p2)] = tmp_divs["B"].get(f"{p1} vs {p2}")

            try:
                is_immediate_previous = (
                    prev_tramo == (current_tramo - 1)
                    and current_tramo <= max_jornadas(current_tramo)
                )
                recompute_round(
                    prev_tramo,
                    apply_divisions_from_round=is_immediate_previous,
                    admin_user=str(st.session_state.get("user") or ""),
                )
                if is_immediate_previous:
                    current_matches = st.session_state.get("league_matches", {})
                    if current_tramo in current_matches:
                        del current_matches[current_tramo]
                persist_state()
                clear_money_caches()
                if prev_tramo >= max_jornadas(prev_tramo):
                    _sync_hall_of_fame_silent()
                if discord_notifications_enabled():
                    notify_league_match_results_async(match_notifications)
                st.success(
                    "Jornada anterior actualizada. Puntos y monedas recalculados."
                )
                st.rerun()
            except Exception as e:
                st.error(str(e))


def page_tabla() -> None:
    ensure_league_css()
    if st.session_state.pop(_CLEAR_EDIT_BUFFERS_NEXT_KEY, False):
        _clear_league_edit_buffers()

    _clear_league_page_caches()
    state_reloaded = restore_state()
    ensure_state()
    if state_reloaded:
        st.session_state.pop("league_tmp", None)
        st.session_state.pop("league_tmp_prev", None)
    st.session_state.setdefault("league_prev_edit_active", False)
    if st.session_state.get("league_active"):
        st.session_state["league_prev_edit_active"] = False

    if st.session_state.get("_league_state_error"):
        error_msg = str(st.session_state.get("_league_state_error") or "")
        st.error(f"No se pudo leer el estado compartido de la liga: {error_msg}")
        if (
            "settings.key='league_state'" in error_msg
            and _current_user_can_resend_summary()
        ):
            st.info(
                "No hay estado de liga en Supabase. Anto puede crear uno inicial en la nube."
            )
            if st.button(
                "Crear estado inicial de liga en Supabase", use_container_width=True
            ):
                try:
                    persist_state()
                    _queue_flash(
                        "success", "Estado inicial de liga creado en Supabase."
                    )
                    _clear_local_league_state()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info(
                "No se muestran controles de liga para evitar guardar encima con una copia antigua."
            )
        return
    _render_flash_messages()
    current_user = st.session_state.get("user")
    read_only = is_trainer_retired(current_user)
    can_manage_league = is_league_admin(current_user) and not read_only
    if read_only:
        st.info("Entrenador retirado.")

    _auto_notify_latest_closed_round()
    resend_round = _latest_closed_round()
    if (
        resend_round is not None
        and _current_user_can_resend_summary()
        and discord_notifications_enabled()
    ):
        if st.button(
            f"Reenviar resumen jornada {resend_round} a Discord",
            use_container_width=True,
            key=f"resend_league_round_{resend_round}",
        ):
            if not _current_user_can_resend_summary():
                st.error("Solo Anto puede reenviar el resumen de jornada.")
            else:
                ok, message = _send_league_round_notification(resend_round, force=True)
                if ok:
                    st.success(f"Resumen de jornada {resend_round} enviado a Discord.")
                else:
                    st.error(
                        f"No se pudo enviar el resumen de jornada {resend_round}: {message}"
                    )

    tramo = st.session_state.league_tramo
    league_players = users_with_retired_last(active_users())
    division_a_size = division_a_size_for_count(len(league_players), int(tramo))
    division_b_size = max(len(league_players) - division_a_size, 0)
    current_max_jornadas = max_jornadas(int(tramo))
    liga_finalizada = tramo > current_max_jornadas
    prev_tramo = tramo - 1 if tramo > 1 else None
    has_prev_closed = bool(
        prev_tramo and prev_tramo in st.session_state.get("league_matches", {})
    )

    st.markdown(
        _league_header_html(
            tramo=int(tramo),
            max_rounds=int(current_max_jornadas),
            player_count=len(league_players),
            division_a_size=int(division_a_size),
            division_b_size=int(division_b_size),
            is_active=bool(st.session_state.league_active),
            read_only=bool(read_only),
            finalized=bool(liga_finalizada),
        ),
        unsafe_allow_html=True,
    )
    if st.button(
        "Actualizar datos de liga",
        use_container_width=True,
        key="refresh_league_table",
    ):
        _clear_league_page_caches()
        _clear_local_league_state()
        _queue_flash("success", "Datos de liga recargados desde el estado compartido.")
        st.rerun()

    st.markdown(
        _section_heading_html(
            "Control de jornada",
            "Abre, modifica o cierra resultados de la jornada activa.",
        ),
        unsafe_allow_html=True,
    )
    colA, colB = st.columns([2, 2])
    with colA:
        estado = "En edicion" if st.session_state.league_active else "Cerrado"
        badge_cls = "status-warn" if st.session_state.league_active else "status-ok"
        st.markdown(
            f"Tramo actual: <strong>{tramo}</strong> "
            f"<span class='status-badge {badge_cls}'>{estado}</span>",
            unsafe_allow_html=True,
        )
    with colB:
        if st.session_state.league_active:
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "Finalizar jornada",
                    use_container_width=True,
                    disabled=not can_manage_league,
                ):
                    try:
                        if not _require_league_admin_ui():
                            return
                        closing_tramo = int(tramo)
                        get_matches_for(closing_tramo)
                        finalize(closing_tramo, admin_user=str(current_user or ""))
                        try:
                            expire_shop_discounts_through_jornada(closing_tramo)
                            if closing_tramo < max_jornadas(closing_tramo):
                                promotions = schedule_shop_promotions(
                                    get_catalog(), closed_round=closing_tramo
                                )
                                if promotions and discord_notifications_enabled():
                                    _queue_flash(
                                        "success",
                                        f"Aaron ha anunciado {len(promotions)} promociones "
                                        "para la próxima jornada.",
                                    )
                        except Exception as promotion_error:
                            _queue_flash(
                                "error",
                                "La jornada se cerró, pero no se pudieron preparar "
                                f"las promociones: {promotion_error}",
                            )
                        clear_money_caches()
                        clear_ranking_caches()
                        tabla_actualizada = general_table_sorted()
                        podium = (
                            tabla_actualizada[:3]
                            if closing_tramo >= max_jornadas(closing_tramo)
                            else None
                        )
                        if closing_tramo >= max_jornadas(closing_tramo):
                            _sync_hall_of_fame_silent()
                        if discord_notifications_enabled():
                            notified, notify_message = _send_league_round_notification(
                                closing_tramo, force=True
                            )
                            if notified:
                                _queue_flash(
                                    "success",
                                    "Aaron Avisa ha enviado el resumen de la jornada a Discord.",
                                )
                            else:
                                _queue_flash(
                                    "error",
                                    f"Jornada cerrada, pero Aaron Avisa no pudo enviar a Discord: {notify_message}",
                                )
                        else:
                            _queue_flash(
                                "info",
                                "Jornada cerrada sin aviso de Discord: Aaron Avisa esta silenciado.",
                            )
                        if closing_tramo >= max_jornadas(closing_tramo):
                            if podium:
                                labels = ["Ganador", "Segundo puesto", "Tercer puesto"]
                                summary = " | ".join(
                                    f"{labels[i]}: {user}"
                                    for i, (user, _pts) in enumerate(podium)
                                )
                                _queue_flash(
                                    "success", f"Jornada final cerrada. {summary}."
                                )
                            else:
                                _queue_flash(
                                    "success",
                                    "Jornada final cerrada. La liga ha terminado.",
                                )
                        else:
                            _queue_flash(
                                "success",
                                "Jornada cerrada: rankings calculados y ascensos/descensos aplicados.",
                            )
                        _schedule_clear_league_edit_buffers()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button(
                    "Cancelar jornada",
                    use_container_width=True,
                    disabled=not can_manage_league,
                ):
                    if not _require_league_admin_ui():
                        return
                    st.session_state.league_active = False
                    if tramo in st.session_state.league_matches:
                        del st.session_state.league_matches[tramo]
                    persist_state()
                    clear_money_caches()
                    _queue_flash(
                        "info", "Edicion cancelada. No se guardara ningun resultado."
                    )
                    _schedule_clear_league_edit_buffers()
                    st.rerun()
        else:
            c1, c2 = st.columns(2)
            with c1:
                if liga_finalizada:
                    st.info("La liga ha finalizado. No se pueden crear mas jornadas.")
                else:
                    if st.button(
                        "Editar jornada",
                        use_container_width=True,
                        disabled=not can_manage_league,
                    ):
                        if not _require_league_admin_ui():
                            return
                        st.session_state.league_prev_edit_active = False
                        st.session_state.league_active = True
                        get_matches_for(tramo)
                        persist_state()
                        _notify_missing_team_locks_once(int(tramo))
                        _schedule_clear_league_edit_buffers()
                        st.rerun()
            with c2:
                prev_label = (
                    f"Cerrar edicion tramo {prev_tramo}"
                    if st.session_state.get("league_prev_edit_active") and prev_tramo
                    else "Modificar jornada anterior"
                )
                if st.button(
                    prev_label,
                    use_container_width=True,
                    disabled=(not has_prev_closed) or not can_manage_league,
                ):
                    if not _require_league_admin_ui():
                        return
                    st.session_state.league_prev_edit_active = not st.session_state.get(
                        "league_prev_edit_active", False
                    )
                    st.rerun()
                if not has_prev_closed:
                    st.caption("No hay jornada anterior cerrada para editar.")

    st.markdown(
        _section_heading_html(
            "Gestion de divisiones",
            "Ajusta los grupos activos antes de abrir una jornada.",
        ),
        unsafe_allow_html=True,
    )
    with st.expander(
        f"Divisiones ({division_a_size} y {division_b_size})",
        expanded=False,
    ):
        players = league_players
        cur_divs = (
            st.session_state.league_divisions
            if isinstance(st.session_state.league_divisions, dict)
            else {"A": [], "B": []}
        )

        def _normalize_players(values: list) -> list[str]:
            canon = {str(u).strip().lower(): u for u in players}
            out: list[str] = []
            for v in values or []:
                key = str(v).strip().lower()
                if not key:
                    continue
                name = canon.get(key)
                if name and name not in out:
                    out.append(name)
            return out

        key_A = "league_div_A"
        if key_A in st.session_state:
            st.session_state[key_A] = _normalize_players(st.session_state.get(key_A))

        default_A = _normalize_players(cur_divs.get("A", []))[:division_a_size]
        sel_A = st.multiselect(
            f"Liga A ({division_a_size} jugadores)",
            players,
            default=default_A,
            max_selections=division_a_size,
            key=key_A,
        )
        remaining = [p for p in players if p not in sel_A]
        key_B = "league_div_B"
        if key_B in st.session_state:
            st.session_state[key_B] = _normalize_players(st.session_state.get(key_B))
            st.session_state[key_B] = [
                p for p in st.session_state[key_B] if p in remaining
            ]

        default_B = [
            p for p in _normalize_players(cur_divs.get("B", [])) if p in remaining
        ][:division_b_size]
        sel_B = st.multiselect(
            f"Liga B ({division_b_size} jugadores)",
            remaining,
            default=default_B,
            max_selections=division_b_size,
            key=key_B,
        )
        if st.button("Guardar divisiones", disabled=not can_manage_league):
            if not _require_league_admin_ui():
                return
            if len(sel_A) == division_a_size and len(sel_B) == division_b_size:
                st.session_state.league_divisions = {"A": sel_A, "B": sel_B}
                st.session_state.league_tramo = 1
                st.session_state.league_active = False
                st.session_state.league_matches = {}
                st.session_state.league_results = {}
                st.session_state.league_movements = {}
                st.session_state[ROUND_SNAPSHOTS_STATE_KEY] = {}
                persist_state()
                clear_money_caches()
                clear_ranking_caches()
                _queue_flash("success", "Divisiones actualizadas.")
                _schedule_clear_league_edit_buffers()
                st.rerun()
            else:
                st.error(
                    f"Selecciona exactamente {division_a_size} en A "
                    f"y {division_b_size} en B."
                )

    if st.session_state.get("league_prev_edit_active") and prev_tramo:
        _render_previous_round_editor(
            prev_tramo=prev_tramo,
            current_tramo=tramo,
            read_only=not can_manage_league,
        )

    A = st.session_state.league_divisions["A"]
    B = st.session_state.league_divisions["B"]
    pos_b_start = len(A) + 1
    pos_b_end = pos_b_start + len(B) - 1 if B else pos_b_start - 1
    tabla = general_table_sorted()
    current_user = st.session_state.get("user")
    points_by_user = {str(user): _fmt_points(pts) for user, pts in tabla}
    division_players = [str(user) for user in (A + B)]
    coins_by_user = {user: _coins_for_user(user) for user in division_players}

    if st.session_state.league_active:
        st.markdown(
            _section_heading_html(
                "Resultados",
                "Marca ganadores y guarda antes de cerrar la jornada.",
            ),
            unsafe_allow_html=True,
        )
        data = get_matches_for(tramo)

        def _ensure_tmp_results():
            tmp = st.session_state.setdefault("league_tmp", {})
            divs = tmp.setdefault(tramo, {"A": {}, "B": {}})
            for div in ("A", "B"):
                for (p1, p2), winner in data[div].items():
                    key = f"{p1} vs {p2}"
                    divs[div].setdefault(key, winner)
            return divs

        tmp_divs = _ensure_tmp_results()

        with st.form(f"form_results_{tramo}"):
            cA, cB = st.columns(2)
            with cA:
                st.markdown(f"**Liga A (posiciones 1-{len(A)})**")
                for (p1, p2), winner in data["A"].items():
                    key = f"{p1} vs {p2}"
                    current = tmp_divs["A"].get(key)
                    opts = ["(sin marcar)", p1, p2]
                    try:
                        idx = opts.index(current) if current in opts else 0
                    except Exception:
                        idx = 0
                    pick = st.selectbox(key, opts, index=idx, key=f"A_{p1}_{p2}")
                    tmp_divs["A"][key] = None if pick == "(sin marcar)" else pick
            with cB:
                rango_b = (
                    f"{pos_b_start}-{pos_b_end}"
                    if pos_b_start <= pos_b_end
                    else f"{pos_b_start}-?"
                )
                st.markdown(f"**Liga B (posiciones {rango_b})**")
                for (p1, p2), winner in data["B"].items():
                    key = f"{p1} vs {p2}"
                    current = tmp_divs["B"].get(key)
                    opts = ["(sin marcar)", p1, p2]
                    try:
                        idx = opts.index(current) if current in opts else 0
                    except Exception:
                        idx = 0
                    pick = st.selectbox(key, opts, index=idx, key=f"B_{p1}_{p2}")
                    tmp_divs["B"][key] = None if pick == "(sin marcar)" else pick

            submitted = st.form_submit_button(
                "Guardar resultados de la jornada",
                disabled=not can_manage_league,
            )
            if submitted:
                if not _require_league_admin_ui():
                    return
                match_notifications = _changed_match_notifications(
                    tramo, data, tmp_divs
                )
                for p1, p2 in list(data["A"].keys()):
                    k = f"{p1} vs {p2}"
                    data["A"][(p1, p2)] = tmp_divs["A"].get(k)
                for p1, p2 in list(data["B"].keys()):
                    k = f"{p1} vs {p2}"
                    data["B"][(p1, p2)] = tmp_divs["B"].get(k)
                persist_state()
                clear_money_caches()
                if discord_notifications_enabled():
                    notify_league_match_results_async(match_notifications)
                if match_notifications:
                    if discord_notifications_enabled():
                        st.success(
                            "Resultados guardados. Aaron Avisa notificara los enfrentamientos actualizados."
                        )
                    else:
                        st.success("Resultados guardados. Discord esta silenciado.")
                else:
                    st.success("Resultados guardados.")

        if all_filled(data["A"]) and all_filled(data["B"]):
            st.markdown(
                _section_heading_html(
                    "Ranking estimado",
                    "Previsualizacion antes de finalizar la jornada.",
                ),
                unsafe_allow_html=True,
            )
            from app.liga.ranking import _rank

            rankA = _rank(A, data["A"])
            rankB = _rank(B, data["B"])
            movement_count = movement_count_for_divisions(
                len(rankA),
                len(rankB),
                int(tramo),
            )
            badges_a = {user: "Baja" for user in rankA[-movement_count:]} if movement_count else {}
            badges_b = {user: "Sube" for user in rankB[:movement_count]} if movement_count else {}
            st.markdown(
                _division_grid_html(
                    rankA,
                    rankB,
                    start_b=pos_b_start,
                    badges_a=badges_a,
                    badges_b=badges_b,
                    points_by_user=points_by_user,
                    coins_by_user=coins_by_user,
                    current_user=current_user,
                ),
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            _section_heading_html(
                "Divisiones actuales",
                "Orden vigente para los emparejamientos de la proxima jornada.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            _division_grid_html(
                A,
                B,
                start_b=pos_b_start,
                points_by_user=points_by_user,
                coins_by_user=coins_by_user,
                current_user=current_user,
            ),
            unsafe_allow_html=True,
        )

    if liga_finalizada and not st.session_state.league_active:
        _render_final_podium()
    if st.session_state.league_active:
        st.markdown(
            _section_heading_html("Tabla general"),
            unsafe_allow_html=True,
        )
        st.markdown(
            _league_table_html(tabla, current_user=current_user),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            _section_heading_html("Tabla general", "Incluye monedas actuales."),
            unsafe_allow_html=True,
        )
        st.markdown(
            _league_table_html(
                tabla,
                include_coins=True,
                current_user=current_user,
            ),
            unsafe_allow_html=True,
        )

    round_snapshots = st.session_state.get(ROUND_SNAPSHOTS_STATE_KEY, {})
    if (
        st.session_state.get("league_movements")
        or st.session_state.get("league_results")
        or round_snapshots
    ):
        st.markdown(
            _section_heading_html(
                "Historial",
                "Cierres anteriores con marcas de ascenso y descenso.",
            ),
            unsafe_allow_html=True,
        )
        lr = st.session_state.get("league_results", {})
        tramos = set()
        for _u, mp in lr.items():
            try:
                tramos.update(int(k) for k in mp.keys())
            except Exception:
                tramos |= set(mp.keys())
        try:
            tramos.update(int(k) for k in (round_snapshots or {}).keys())
        except Exception:
            pass
        for t in sorted(tramos):
            snapshot = snapshot_for_round(round_snapshots, int(t))
            snapshot_rows = snapshot_standings(round_snapshots, int(t)) if snapshot else []
            if snapshot_rows:
                entries = [
                    (str(row.get("user") or ""), int(row.get("position") or 0))
                    for row in snapshot_rows
                    if str(row.get("user") or "").strip()
                ]
                division_snapshot = (
                    snapshot.get("division_snapshot")
                    if isinstance(snapshot.get("division_snapshot"), dict)
                    else {}
                )
                a_len = len(division_snapshot.get("A") or [])
                b_len = len(division_snapshot.get("B") or [])
                if a_len <= 0:
                    a_len = len([row for row in snapshot_rows if row.get("division") == "A"])
                config_snapshot = (
                    snapshot.get("season_config_version")
                    if isinstance(snapshot.get("season_config_version"), dict)
                    else {}
                )
                movement_count = int(config_snapshot.get("movement_count") or 0)
            else:
                entries = []
                for u, mp in lr.items():
                    try:
                        pos = mp.get(t)
                        if pos is not None:
                            entries.append((u, int(pos)))
                    except Exception:
                        continue
                if not entries:
                    continue
                entries.sort(key=lambda x: x[1])
                round_matches = (st.session_state.get("league_matches") or {}).get(t, {})
                a_len = len(
                    _players_from_match_map((round_matches or {}).get("A", {}) or {})
                )
                if a_len <= 0:
                    a_len = 5
                b_len = len(
                    _players_from_match_map((round_matches or {}).get("B", {}) or {})
                )
                movement_count = movement_count_for_divisions(a_len, b_len, int(t))
            b_start = a_len + 1
            b_positions = [pos for _u, pos in entries if pos >= b_start]
            b_end = (
                max(b_positions)
                if b_positions
                else (b_start + b_len - 1 if b_len else b_start - 1)
            )
            show_movement_tags = int(t) < max_jornadas(int(t)) and movement_count > 0
            rowsA, rowsB = [], []
            for u, pos in entries:
                movement = ""
                if (
                    show_movement_tags
                    and pos <= a_len
                    and pos > max(a_len - movement_count, 0)
                ):
                    movement = "Baja"
                elif show_movement_tags and b_start <= pos < b_start + movement_count:
                    movement = "Sube"
                row = (u, pos, movement)
                if pos <= a_len:
                    rowsA.append(row)
                else:
                    rowsB.append(row)
            st.markdown(
                _history_round_html(
                    round_no=int(t),
                    rows_a=rowsA,
                    rows_b=rowsB,
                    a_len=int(a_len),
                    b_start=int(b_start),
                    b_end=int(b_end),
                ),
                unsafe_allow_html=True,
            )

    st.markdown(
        _section_heading_html(
            "Zona critica",
            "Reinicia solo cuando quieras borrar el progreso de liga actual.",
        ),
        unsafe_allow_html=True,
    )
    confirm = st.selectbox(
        "Seguro que quieres reiniciar la Liga?",
        ["No", "Si"],
        key="reset_league_ligatabla",
    )
    if st.button(
        "Reiniciar liga",
        key="btn_reset_league_ligatabla",
        disabled=not can_manage_league,
    ):
        if not _require_league_admin_ui():
            return
        if confirm == "Si":
            players = users_with_retired_last(active_users())
            division_a_size = division_a_size_for_count(len(players), 1)
            st.session_state.league_tramo = 1
            st.session_state.league_active = False
            st.session_state.league_results = {}
            st.session_state.league_matches = {}
            st.session_state.league_temp_order = {"A": [], "B": []}
            st.session_state.league_divisions = {
                "A": players[:division_a_size],
                "B": players[division_a_size:],
            }
            st.session_state.league_movements = {}
            st.session_state[ROUND_SNAPSHOTS_STATE_KEY] = {}
            try:
                clear_purchases()
            except Exception:
                pass
            persist_state()
            clear_money_caches()
            clear_ranking_caches()
            _queue_flash("success", "Liga reiniciada.")
            _schedule_clear_league_edit_buffers()
            st.rerun()
        else:
            st.info("Operacion cancelada. La liga sigue igual.")
