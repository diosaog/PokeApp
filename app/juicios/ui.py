from __future__ import annotations

import streamlit as st

from app.juicios.constants import (
    PENALTY_TEMPLATE_LABELS,
    PENALTY_TEMPLATE_ORDER,
    STATUS_FINISHED,
    STATUS_IN_PROGRESS,
    STATUS_PROPOSED,
    VERDICT_LABELS,
    VOTE_LABELS,
    VOTE_ORDER,
)
from app.juicios.forms import render_case_details_form, render_resolution_form
from app.juicios.penalties import get_user_penalties
from app.juicios.render import case_header, render_case_info
from app.juicios.repo import (
    can_edit_case,
    create_case,
    delete_case,
    list_cases_for_user,
    next_case_number,
    register_jury_vote,
    update_case,
)
from app.interfaz.theme import apply_section_theme
from utils import USERS


def _clear_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _apply_juicio_theme() -> None:
    st.markdown(
        """
        <style>
        .ju-hero{
          position:relative;
          background:linear-gradient(135deg,#f5e5bf 0%,#e8cf96 52%,#c48f42 100%);
          border:3px solid #6f4312;
          border-radius:10px;
          padding:14px 16px;
          color:#2a190b;
          box-shadow:0 8px 20px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.32);
          margin-bottom:12px;
        }
        .ju-hero:after{
          content:"";
          position:absolute;
          right:14px; top:10px;
          width:28px; height:28px; border-radius:50%;
          background:
            radial-gradient(circle at 50% 50%, #ffffff 0 4px, transparent 5px),
            linear-gradient(180deg,#f04646 0 50%,#f6f1e8 50% 100%);
          border:2px solid #1a1a1a;
          box-shadow:0 0 0 2px rgba(0,0,0,.18);
        }
        .ju-hero-title{
          font-family:"Press Start 2P", monospace;
          font-size:14px;
          line-height:1.3;
          margin-bottom:8px;
          color:#2a190b;
        }
        .ju-hero-sub{
          font-size:12px;
          color:#35210f;
        }
        .ju-hero-chips{
          display:flex;
          gap:6px;
          flex-wrap:wrap;
          margin-top:10px;
        }
        .ju-chip{
          font-size:10px;
          font-weight:700;
          color:#2a190b;
          background:#f7f1df;
          border:1px solid #8b642f;
          border-radius:999px;
          padding:3px 8px;
        }
        .ju-toolbar{
          background:#f7f1df;
          border:2px solid #8b642f;
          border-radius:8px;
          padding:8px 10px;
          margin:8px 0 10px 0;
          color:#2b1d0e;
          font-size:11px;
          font-weight:700;
        }
        .ju-note{
          background:#f9f5e9;
          border:1px dashed #9a7237;
          border-radius:7px;
          padding:8px 10px;
          color:#342110;
          font-size:11px;
        }
        .ju-sep{
          height:2px;
          background:linear-gradient(90deg,transparent 0,#8b642f 15%,#8b642f 85%,transparent 100%);
          margin:10px 0 12px;
        }
        .ju-stage-wrap{
          display:flex;
          gap:8px;
          margin:8px 0 12px;
        }
        .ju-stage{
          flex:1;
          min-width:0;
          border:1px solid var(--stage-color,#6c757d);
          border-radius:8px;
          text-align:center;
          padding:6px 8px;
          background:#f0ede5;
          color:#605548;
          font-weight:700;
          font-size:12px;
          box-shadow:inset 0 1px 0 rgba(255,255,255,.45);
        }
        .ju-stage-on{
          background:var(--stage-color,#6c757d);
          color:#ffffff;
        }
        .ju-docket{
          background:#f8f2e4;
          border:2px solid #8b642f;
          border-radius:8px;
          padding:8px 10px;
          margin-bottom:8px;
          color:#2a1b0d;
        }
        .ju-docket-title{
          font-family:"Press Start 2P", monospace;
          font-size:10px;
          margin-bottom:5px;
        }
        .ju-docket-sub{
          font-size:11px;
          color:#46301a;
        }
        .ju-verdict{
          display:inline-block;
          padding:3px 8px;
          border-radius:999px;
          font-size:10px;
          font-weight:700;
          margin-left:6px;
          border:1px solid #6d4b1f;
          background:#f1e5c5;
          color:#2a1c0d;
        }
        .ju-v-guilty{ background:#f2c0b8; border-color:#a85345; color:#55170f; }
        .ju-v-not-guilty{ background:#c8efc7; border-color:#4f8e4f; color:#1e4b1d; }
        .ju-v-pending{ background:#f0e4c1; border-color:#9f823e; color:#4b3a14; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_juicio_hero() -> None:
    st.markdown(
        """
        <div class='ju-hero'>
          <div class='ju-hero-title'>TRIBUNAL POKEMON</div>
          <div class='ju-hero-sub'>Sala de Audiencias: registro de casos, jurado, veredicto y sanciones.</div>
          <div class='ju-hero-chips'>
            <span class='ju-chip'>Expedientes</span>
            <span class='ju-chip'>Jurado</span>
            <span class='ju-chip'>Veredicto</span>
            <span class='ju-chip'>Castigos</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    st.markdown("<div class='ju-sep'></div>", unsafe_allow_html=True)


def _render_create_case(current_user: str) -> None:
    st.markdown("---")
    st.subheader("Nuevo juicio")
    sent, payload = render_case_details_form(
        form_key="juicio_new_form",
        case_no=next_case_number(),
        current_user=current_user,
        initial={"is_public": True, "priority": "Media", "jury_size": 5},
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


def _render_jury_vote_controls(case: dict, current_user: str) -> None:
    if str(case.get("status") or "") != STATUS_IN_PROGRESS:
        return

    cid = int(case.get("id") or 0)
    st.markdown("---")
    st.caption("Votacion del jurado (cierre automatico por mayoria)")

    can_proxy_vote = can_edit_case(case, current_user)
    jury_options = list(USERS.keys())
    default_jury = current_user if current_user in jury_options else (jury_options[0] if jury_options else "")

    if can_proxy_vote and jury_options:
        jury_member = st.selectbox(
            "Jurado que vota",
            options=jury_options,
            index=jury_options.index(default_jury),
            key=f"juicio_vote_jury_{cid}",
        )
    else:
        jury_member = current_user
        st.caption(f"Jurado: {jury_member}")

    vote_value = st.radio(
        "Voto",
        options=VOTE_ORDER,
        format_func=lambda x: VOTE_LABELS.get(x, x),
        horizontal=True,
        key=f"juicio_vote_choice_{cid}",
    )

    if st.button("Registrar voto", key=f"juicio_vote_btn_{cid}"):
        try:
            before_status = str(case.get("status") or "")
            updated = register_jury_vote(cid, current_user, jury_member, vote_value)
            _clear_cache()
            if before_status != STATUS_FINISHED and str(updated.get("status") or "") == STATUS_FINISHED:
                verdict_label = VERDICT_LABELS.get(str(updated.get("verdict") or ""), "Pendiente")
                st.success(f"Mayoria alcanzada. Juicio finalizado por votacion ({verdict_label}).")
            else:
                st.success("Voto registrado.")
            st.rerun()
        except Exception as e:
            st.error(str(e))


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
    template_key = f"juicio_penalty_template_{cid}"

    st.markdown("---")
    st.caption("Etapa En proceso: define castigos propuestos antes de finalizar.")

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        if st.button(PENALTY_TEMPLATE_LABELS[PENALTY_TEMPLATE_ORDER[0]], key=f"juicio_tpl_{cid}_0"):
            st.session_state[template_key] = PENALTY_TEMPLATE_ORDER[0]
            st.rerun()
    with t2:
        if st.button(PENALTY_TEMPLATE_LABELS[PENALTY_TEMPLATE_ORDER[1]], key=f"juicio_tpl_{cid}_1"):
            st.session_state[template_key] = PENALTY_TEMPLATE_ORDER[1]
            st.rerun()
    with t3:
        if st.button(PENALTY_TEMPLATE_LABELS[PENALTY_TEMPLATE_ORDER[2]], key=f"juicio_tpl_{cid}_2"):
            st.session_state[template_key] = PENALTY_TEMPLATE_ORDER[2]
            st.rerun()
    with t4:
        if st.button("Limpiar plantilla", key=f"juicio_tpl_{cid}_clear"):
            st.session_state.pop(template_key, None)
            st.rerun()

    selected_template = st.session_state.get(template_key)
    if selected_template:
        label = PENALTY_TEMPLATE_LABELS.get(str(selected_template), str(selected_template))
        st.caption(f"Plantilla activa: {label}")

    if not st.session_state.get(edit_key, False):
        if st.button("Editar castigos propuestos", key=f"juicio_penalties_btn_{cid}"):
            st.session_state[edit_key] = True
            st.rerun()
    else:
        sent, payload = render_resolution_form(
            form_key=f"juicio_resolution_form_{cid}",
            initial=case,
            submit_label="Guardar castigos propuestos",
            template_name=(str(selected_template) if selected_template else None),
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
                st.session_state.pop(template_key, None)
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.button("Finalizar Juicio", key=f"juicio_finish_{cid}", type="primary"):
        penalties = list(case.get("penalties") or [])
        if not penalties:
            st.error("Debes guardar al menos un castigo antes de finalizar.")
            return
        try:
            _save_case_update(cid, current_user, {"status": STATUS_FINISHED})
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
            st.session_state.pop(f"juicio_penalty_template_{cid}", None)
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
    st.markdown(
        "<div class='ju-toolbar'>Archivo judicial: filtra expedientes por visibilidad y estado.</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        scope = st.radio(
            "Vista",
            options=["Publicos y mios", "Solo publicos", "Solo mios"],
            horizontal=True,
            index=0,
        )
    with c2:
        state_scope = st.radio(
            "Estado",
            options=["Activos", "Archivados", "Todos"],
            horizontal=True,
            index=0,
        )

    cases = list_cases_for_user(current_user)
    if scope == "Solo publicos":
        cases = [c for c in cases if bool(c.get("is_public"))]
    elif scope == "Solo mios":
        cases = [c for c in cases if str(c.get("creator")) == str(current_user)]

    if state_scope == "Activos":
        cases = [c for c in cases if str(c.get("status") or "") != STATUS_FINISHED]
    elif state_scope == "Archivados":
        cases = [c for c in cases if str(c.get("status") or "") == STATUS_FINISHED]

    if not cases:
        st.info("No hay juicios para mostrar.")
        return

    for case in cases:
        with st.expander(case_header(case), expanded=False):
            render_case_info(case)

            _render_jury_vote_controls(case, current_user)

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
                st.caption("Juicio finalizado (archivado).")

            _render_delete_case_controls(case, current_user)


def page_juicios() -> None:
    apply_section_theme("Juicios")
    _apply_juicio_theme()
    st.header("Juicios")
    _render_juicio_hero()
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
