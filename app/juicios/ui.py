from __future__ import annotations

import json

import streamlit as st

from app.juicios.constants import STATUS_FINISHED, STATUS_IN_PROGRESS, STATUS_PROPOSED
from app.juicios.forms import render_case_details_form, render_resolution_form
from app.juicios.penalties import get_user_penalties
from app.juicios.render import case_header, render_case_info
from app.juicios.repo import (
    can_edit_case,
    create_case,
    delete_case,
    list_cases_for_user,
    next_case_number,
    update_case,
)
from storage import settings_get


def _clear_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _show_active_penalties(user: str) -> None:
    pen = get_user_penalties(user)
    if not pen.get("sources"):
        return
    st.warning("Tienes castigos activos derivados de juicios.")
    if pen.get("store_blocked"):
        st.caption("- Tienda y monedas bloqueadas.")
        tramos = list(pen.get("store_ban_tramos") or [])
        if tramos:
            st.caption(f"- Bloqueo por tramo: {', '.join(tramos)}")
    if pen.get("coins_reduction"):
        st.caption(f"- Reduccion de monedas aplicada: {pen.get('coins_reduction')}")
    if pen.get("points_reduction"):
        st.caption(f"- Reduccion de puntos aplicada: {pen.get('points_reduction')}")
    for txt in pen.get("pokemon_release_notes") or []:
        st.caption(f"- Liberacion/Muerte de Pokemon: {txt}")
    for txt in pen.get("other_notes") or []:
        st.caption(f"- Otro castigo: {txt}")


def _render_create_case(current_user: str) -> None:
    st.markdown("---")
    st.subheader("Nuevo juicio")
    sent, payload = render_case_details_form(
        form_key="juicio_new_form",
        case_no=next_case_number(),
        current_user=current_user,
        initial={"is_public": True, "priority": "Media"},
        submit_label="Confirmar y guardar propuesta",
    )
    if sent and payload:
        create_case(current_user, payload)
        st.success("Juicio creado en etapa Propuesto.")
        st.session_state["juicio_show_new_form"] = False
        _clear_cache()
        st.rerun()


def _save_case_update(case_id: int, current_user: str, payload: dict) -> None:
    update_case(case_id, current_user, payload)
    _clear_cache()


def _current_league_tramo() -> int:
    try:
        from_session = int(st.session_state.get("league_tramo") or 0)
        if from_session > 0:
            return from_session
    except Exception:
        pass
    try:
        raw = settings_get("league_state")
        if not raw:
            return 1
        obj = json.loads(raw)
        return max(int(obj.get("tramo") or 1), 1)
    except Exception:
        return 1


def _with_store_ban_window(penalties: list[dict]) -> list[dict]:
    tramo_now = _current_league_tramo()
    out: list[dict] = []
    for p in penalties:
        item = dict(p)
        if str(item.get("type") or "") == "store_ban":
            try:
                start = int(item.get("start_tramo") or 0)
                end = int(item.get("end_tramo") or 0)
            except Exception:
                start, end = 0, 0
            if start <= 0 or end <= 0:
                item["start_tramo"] = tramo_now
                item["end_tramo"] = tramo_now
        out.append(item)
    return out


def _render_proposed_controls(case: dict, current_user: str) -> None:
    cid = int(case.get("id") or 0)
    edit_key = f"juicio_edit_details_{cid}"

    st.markdown("---")
    st.caption("Etapa Propuesto: completa o ajusta la informacion del caso.")
    if not st.session_state.get(edit_key, False):
        if st.button("Editar informacion", key=f"juicio_edit_btn_{cid}"):
            st.session_state[edit_key] = True
            st.rerun()
    else:
        sent, payload = render_case_details_form(
            form_key=f"juicio_edit_form_{cid}",
            case_no=int(case.get("case_no") or 0),
            current_user=current_user,
            initial=case,
            submit_label="Guardar propuesta",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cerrar editor", key=f"juicio_close_edit_{cid}"):
                st.session_state[edit_key] = False
                st.rerun()
        with c2:
            st.caption("Guarda desde el boton del formulario.")

        if sent and payload:
            try:
                _save_case_update(cid, current_user, payload)
                st.success("Informacion del juicio actualizada.")
                st.session_state[edit_key] = False
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.button("Comienza el Juicio", key=f"juicio_start_{cid}", type="primary"):
        try:
            _save_case_update(cid, current_user, {"status": STATUS_IN_PROGRESS})
            st.success("El juicio paso a etapa En proceso.")
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _render_in_progress_controls(case: dict, current_user: str) -> None:
    cid = int(case.get("id") or 0)
    edit_key = f"juicio_edit_resolution_{cid}"

    st.markdown("---")
    st.caption("Etapa En proceso: define castigos propuestos antes de finalizar.")

    if not st.session_state.get(edit_key, False):
        if st.button("Editar castigos propuestos", key=f"juicio_penalties_btn_{cid}"):
            st.session_state[edit_key] = True
            st.rerun()
    else:
        sent, payload = render_resolution_form(
            form_key=f"juicio_resolution_form_{cid}",
            initial=case,
            submit_label="Guardar castigos propuestos",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cerrar castigos", key=f"juicio_close_penalties_{cid}"):
                st.session_state[edit_key] = False
                st.rerun()
        with c2:
            st.caption("Guarda desde el boton del formulario.")

        if sent and payload:
            try:
                _save_case_update(cid, current_user, payload)
                st.success("Castigos propuestos actualizados.")
                st.session_state[edit_key] = False
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.button("Finalizar Juicio", key=f"juicio_finish_{cid}", type="primary"):
        penalties = list(case.get("penalties") or [])
        if not penalties:
            st.error("Debes guardar al menos un castigo antes de finalizar.")
            return
        try:
            penalties_final = _with_store_ban_window(penalties)
            _save_case_update(
                cid,
                current_user,
                {"penalties": penalties_final, "status": STATUS_FINISHED},
            )
            st.success("Juicio finalizado.")
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _render_delete_case_controls(case: dict, current_user: str) -> None:
    cid = int(case.get("id") or 0)
    confirm_key = f"juicio_confirm_delete_{cid}"

    st.markdown("---")
    st.caption("Cancelar Juicio lo elimina permanentemente y reordena la numeracion de casos.")
    confirm_delete = st.checkbox("Confirmo eliminar este juicio", key=confirm_key)
    if st.button("Cancelar Juicio", key=f"juicio_delete_{cid}"):
        if not confirm_delete:
            st.error("Debes confirmar la eliminacion antes de cancelar el juicio.")
            return
        try:
            deleted = delete_case(cid, current_user)
            st.session_state.pop(confirm_key, None)
            st.session_state.pop(f"juicio_edit_details_{cid}", None)
            st.session_state.pop(f"juicio_edit_resolution_{cid}", None)
            _clear_cache()
            st.success(
                f"Juicio #{int(deleted.get('case_no') or 0)} eliminado. "
                "Los casos restantes han sido reordenados."
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _render_case_list(current_user: str) -> None:
    st.markdown("---")
    st.subheader("Juicios")
    scope = st.radio(
        "Vista",
        options=["Publicos y mios", "Solo publicos", "Solo mios"],
        horizontal=True,
        index=0,
    )
    cases = list_cases_for_user(current_user)
    if scope == "Solo publicos":
        cases = [c for c in cases if bool(c.get("is_public"))]
    elif scope == "Solo mios":
        cases = [c for c in cases if str(c.get("creator")) == str(current_user)]

    if not cases:
        st.info("No hay juicios para mostrar.")
        return

    for case in cases:
        with st.expander(case_header(case), expanded=False):
            render_case_info(case)
            if not can_edit_case(case, current_user):
                st.caption("Solo el creador puede editar este juicio.")
                continue

            status = str(case.get("status") or STATUS_PROPOSED)
            if status == STATUS_PROPOSED:
                _render_proposed_controls(case, current_user)
            elif status == STATUS_IN_PROGRESS:
                _render_in_progress_controls(case, current_user)
            else:
                st.markdown("---")
                st.caption("Juicio finalizado en rojo. No hay mas cambios de etapa.")

            _render_delete_case_controls(case, current_user)


def page_juicios() -> None:
    st.header("Juicios")
    current_user = st.session_state.get("user") or ""
    if not current_user:
        st.info("Inicia sesion para usar la seccion de juicios.")
        return
    if current_user != "Anto":
        st.info("No tienes acceso a esta seccion.")
        return

    _show_active_penalties(current_user)

    show_new = bool(st.session_state.get("juicio_show_new_form", False))
    label = "Cerrar formulario" if show_new else "Hacer un Juicio"
    if st.button(label, type="primary", use_container_width=True):
        st.session_state["juicio_show_new_form"] = not show_new
        st.rerun()

    if st.session_state.get("juicio_show_new_form"):
        _render_create_case(current_user)

    _render_case_list(current_user)
