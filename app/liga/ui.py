from __future__ import annotations

import streamlit as st

from app.discord_notify import notify_league_round_finished
from app.liga.ranking import (
    MAX_JORNADAS,
    all_filled,
    clear_ranking_caches,
    final_podium,
    finalize,
    general_table_sorted,
    get_matches_for,
    recompute_round,
)
from app.liga.state import ensure_state, persist_state, restore_state
from app.liga.table_summary import (
    fmt_points as _fmt_points,
    league_round_result_groups as _league_round_result_groups,
    league_round_summary_lines as _league_round_summary_lines,
    league_table_notification_rows as _league_table_notification_rows,
    league_table_rows as _league_table_rows,
    players_from_match_map as _players_from_match_map,
)
from app.juicios.penalties import clear_penalty_caches
from app.tienda.money import clear_money_caches
from storage import clear_purchases, settings_clear_cache
from utils import USERS


def _clear_league_page_caches() -> None:
    try:
        settings_clear_cache("league_state")
    except Exception:
        pass
    clear_penalty_caches()
    clear_money_caches()
    clear_ranking_caches()
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _render_final_podium() -> None:
    podium = final_podium()
    if not podium:
        return
    st.markdown("---")
    st.subheader("Clasificacion final")
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


def _render_previous_round_editor(*, prev_tramo: int, current_tramo: int) -> None:
    data = st.session_state.get("league_matches", {}).get(prev_tramo)
    st.markdown("---")
    st.subheader(f"Modificar jornada anterior (Tramo {prev_tramo})")
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
                pick = st.selectbox(key, opts, index=idx, key=f"PREV_A_{prev_tramo}_{p1}_{p2}")
                tmp_divs["A"][key] = pick
        with cB:
            st.markdown(f"**Liga B (posiciones {b_start}-{b_end})**")
            for (p1, p2), _winner in data.get("B", {}).items():
                key = f"{p1} vs {p2}"
                current = tmp_divs["B"].get(key, p1)
                opts = [p1, p2]
                idx = 0 if current == p1 else 1
                pick = st.selectbox(key, opts, index=idx, key=f"PREV_B_{prev_tramo}_{p1}_{p2}")
                tmp_divs["B"][key] = pick

        submitted = st.form_submit_button("Guardar cambios jornada anterior")
        if submitted:
            for (p1, p2) in list(data.get("A", {}).keys()):
                data["A"][(p1, p2)] = tmp_divs["A"].get(f"{p1} vs {p2}")
            for (p1, p2) in list(data.get("B", {}).keys()):
                data["B"][(p1, p2)] = tmp_divs["B"].get(f"{p1} vs {p2}")

            try:
                is_immediate_previous = prev_tramo == (current_tramo - 1) and current_tramo <= MAX_JORNADAS
                recompute_round(prev_tramo, apply_divisions_from_round=is_immediate_previous)
                if is_immediate_previous:
                    current_matches = st.session_state.get("league_matches", {})
                    if current_tramo in current_matches:
                        del current_matches[current_tramo]
                persist_state()
                clear_money_caches()
                st.success("Jornada anterior actualizada. Puntos y monedas recalculados.")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def page_tabla() -> None:
    _clear_league_page_caches()
    state_reloaded = restore_state()
    ensure_state()
    if state_reloaded:
        st.session_state.pop("league_tmp", None)
        st.session_state.pop("league_tmp_prev", None)
    st.session_state.setdefault("league_prev_edit_active", False)
    if st.session_state.get("league_active"):
        st.session_state["league_prev_edit_active"] = False

    st.header("Liga A/B - Jornada")
    if st.session_state.get("_league_state_error"):
        st.error(f"No se pudo leer el estado compartido de la liga: {st.session_state.get('_league_state_error')}")
    if st.button("Actualizar datos de liga", use_container_width=True, key="refresh_league_table"):
        _clear_league_page_caches()
        st.session_state.pop("_league_state_hash", None)
        st.rerun()

    tramo = st.session_state.league_tramo
    liga_finalizada = tramo > MAX_JORNADAS
    prev_tramo = tramo - 1 if tramo > 1 else None
    has_prev_closed = bool(prev_tramo and prev_tramo in st.session_state.get("league_matches", {}))

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
                if st.button("Finalizar jornada", use_container_width=True):
                    try:
                        round_results = _league_round_result_groups(get_matches_for(tramo))
                        finalize(tramo)
                        clear_money_caches()
                        clear_ranking_caches()
                        tabla_actualizada = general_table_sorted()
                        podium = tabla_actualizada[:3] if tramo >= MAX_JORNADAS else None
                        summary_lines = _league_round_summary_lines(
                            table=tabla_actualizada,
                            movements=st.session_state.get("league_movements", {}).get(tramo, {}),
                            podium=podium,
                        )
                        notified = notify_league_round_finished(
                            round_no=tramo,
                            rows=_league_table_notification_rows(tabla_actualizada),
                            round_results=round_results,
                            summary_lines=summary_lines,
                        )
                        if not notified:
                            st.warning("Jornada cerrada, pero Aaron Avisa no pudo enviar el mensaje a Discord.")
                        if tramo >= MAX_JORNADAS:
                            if podium:
                                labels = ["Ganador", "Segundo puesto", "Tercer puesto"]
                                summary = " | ".join(
                                    f"{labels[i]}: {user}"
                                    for i, (user, _pts) in enumerate(podium)
                                )
                                st.success(f"Jornada final cerrada. {summary}.")
                            else:
                                st.success("Jornada final cerrada. La liga ha terminado.")
                        else:
                            st.success("Jornada cerrada: rankings calculados y ascensos/descensos aplicados.")
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Cancelar jornada", use_container_width=True):
                    st.session_state.league_active = False
                    if tramo in st.session_state.league_matches:
                        del st.session_state.league_matches[tramo]
                    persist_state()
                    clear_money_caches()
                    st.info("Edicion cancelada. No se guardara ningun resultado.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if liga_finalizada:
                    st.info("La liga ha finalizado. No se pueden crear mas jornadas.")
                else:
                    if st.button("Editar jornada", use_container_width=True):
                        st.session_state.league_prev_edit_active = False
                        st.session_state.league_active = True
                        get_matches_for(tramo)
                        persist_state()
            with c2:
                prev_label = (
                    f"Cerrar edicion tramo {prev_tramo}"
                    if st.session_state.get("league_prev_edit_active") and prev_tramo
                    else "Modificar jornada anterior"
                )
                if st.button(prev_label, use_container_width=True, disabled=not has_prev_closed):
                    st.session_state.league_prev_edit_active = not st.session_state.get("league_prev_edit_active", False)
                    st.rerun()
                if not has_prev_closed:
                    st.caption("No hay jornada anterior cerrada para editar.")

    st.markdown("---")
    st.subheader("Editar divisiones")
    with st.expander("Divisiones (5 y 5)", expanded=False):
        players = list(USERS.keys())
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

        default_A = _normalize_players(cur_divs.get("A", []))[:5]
        sel_A = st.multiselect("Liga A (5 jugadores)", players, default=default_A, max_selections=5, key=key_A)
        remaining = [p for p in players if p not in sel_A]
        key_B = "league_div_B"
        if key_B in st.session_state:
            st.session_state[key_B] = _normalize_players(st.session_state.get(key_B))
            st.session_state[key_B] = [p for p in st.session_state[key_B] if p in remaining]

        default_B = [p for p in _normalize_players(cur_divs.get("B", [])) if p in remaining][:5]
        sel_B = st.multiselect("Liga B (5 jugadores)", remaining, default=default_B, max_selections=5, key=key_B)
        if st.button("Guardar divisiones"):
            if len(sel_A) == 5 and len(sel_B) == 5:
                st.session_state.league_divisions = {"A": sel_A, "B": sel_B}
                st.session_state.league_tramo = 1
                st.session_state.league_active = False
                st.session_state.league_matches = {}
                st.session_state.league_results = {}
                st.session_state.league_movements = {}
                st.success("Divisiones actualizadas.")
                persist_state()
                clear_money_caches()
                clear_ranking_caches()
            else:
                st.error("Selecciona exactamente 5 en A y 5 en B.")

    if st.session_state.get("league_prev_edit_active") and prev_tramo:
        _render_previous_round_editor(prev_tramo=prev_tramo, current_tramo=tramo)

    st.markdown("---")
    A = st.session_state.league_divisions["A"]
    B = st.session_state.league_divisions["B"]
    pos_b_start = len(A) + 1
    pos_b_end = pos_b_start + len(B) - 1 if B else pos_b_start - 1

    if st.session_state.league_active:
        st.subheader("Resultados - marca el ganador de cada enfrentamiento")
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
                st.markdown("**Liga A (posiciones 1-5)**")
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
                rango_b = f"{pos_b_start}-{pos_b_end}" if pos_b_start <= pos_b_end else f"{pos_b_start}-?"
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

            submitted = st.form_submit_button("Guardar resultados de la jornada")
            if submitted:
                for (p1, p2) in list(data["A"].keys()):
                    k = f"{p1} vs {p2}"
                    data["A"][(p1, p2)] = tmp_divs["A"].get(k)
                for (p1, p2) in list(data["B"].keys()):
                    k = f"{p1} vs {p2}"
                    data["B"][(p1, p2)] = tmp_divs["B"].get(k)
                persist_state()
                clear_money_caches()
                st.success("Resultados guardados.")

        if all_filled(data["A"]) and all_filled(data["B"]):
            st.markdown("---")
            st.subheader("Previa ranking estimado")
            from app.liga.ranking import _rank
            rankA = _rank(A, data["A"])
            rankB = _rank(B, data["B"])
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Liga A**")
                for i, u in enumerate(rankA, start=1):
                    st.write(f"{i}. {u}")
            with cb:
                st.markdown("**Liga B**")
                for j, u in enumerate(rankB, start=pos_b_start):
                    st.write(f"{j}. {u}")
    else:
        st.subheader("Divisiones actuales")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Liga A**")
            for i, u in enumerate(A, start=1):
                st.write(f"{i}. {u}")
        with c2:
            st.markdown("**Liga B**")
            for j, u in enumerate(B, start=pos_b_start):
                st.write(f"{j}. {u}")

    st.markdown("---")
    tabla = general_table_sorted()
    if liga_finalizada and not st.session_state.league_active:
        _render_final_podium()
    if st.session_state.league_active:
        st.subheader("Tabla general")
        st.dataframe(
            _league_table_rows(tabla),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.subheader("Tabla general (con monedas)")
        st.dataframe(_league_table_rows(tabla, include_coins=True), use_container_width=True, hide_index=True)

    if st.session_state.get("league_movements") or st.session_state.get("league_results"):
        st.markdown("---")
        st.subheader("Historial")
        lr = st.session_state.get("league_results", {})
        tramos = set()
        for _u, mp in lr.items():
            try:
                tramos.update(int(k) for k in mp.keys())
            except Exception:
                tramos |= set(mp.keys())
        for t in sorted(tramos):
            st.markdown(f"**Tramo {t}**")
            mv = st.session_state.get("league_movements", {}).get(t, {})
            up_set = set(mv.get("up") or [])
            down_set = set(mv.get("down") or [])
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
            a_len = len(st.session_state.league_divisions.get("A", [])) if isinstance(st.session_state.league_divisions, dict) else 4
            if a_len <= 0:
                a_len = 4
            b_len = len(st.session_state.league_divisions.get("B", [])) if isinstance(st.session_state.league_divisions, dict) else 0
            b_start = a_len + 1
            b_end = b_start + b_len - 1 if b_len else b_start - 1
            rowsA, rowsB = [], []
            for u, pos in entries:
                tag = "UP " if u in up_set else ("DOWN " if u in down_set else "")
                row = {"Pos": pos, "Jugador": f"{tag}{u}"}
                if pos <= a_len:
                    rowsA.append(row)
                else:
                    rowsB.append(row)
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"Liga A (1-{a_len})")
                st.dataframe(rowsA or [], use_container_width=True)
            with c2:
                st.caption(f"Liga B ({b_start}-{b_end})")
                st.dataframe(rowsB or [], use_container_width=True)

    st.markdown("---")
    st.subheader("Reiniciar Liga")
    confirm = st.selectbox("Seguro que quieres reiniciar la Liga?", ["No", "Si"], key="reset_league_ligatabla")
    if st.button("Reiniciar liga", help="Borra jornadas, resultados y divisiones", key="btn_reset_league_ligatabla"):
        if confirm == "Si":
            players = list(USERS.keys())
            st.session_state.league_tramo = 1
            st.session_state.league_active = False
            st.session_state.league_results = {}
            st.session_state.league_matches = {}
            st.session_state.league_temp_order = {"A": [], "B": []}
            st.session_state.league_divisions = {"A": players[:5], "B": players[5:10]}
            st.session_state.league_movements = {}
            try:
                clear_purchases()
            except Exception:
                pass
            persist_state()
            clear_money_caches()
            clear_ranking_caches()
            st.success("Liga reiniciada.")
        else:
            st.info("Operacion cancelada. La liga sigue igual.")
