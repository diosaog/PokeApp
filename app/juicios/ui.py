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
          background:linear-gradient(135deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 68%, #12161c 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:14px 16px;
          color:var(--bw2-text);
          box-shadow:0 8px 20px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.08);
          margin-bottom:12px;
        }
        .ju-hero:after{
          content:"";
          position:absolute;
          right:14px; top:10px;
          width:20px; height:20px;
          background:linear-gradient(135deg,var(--accent) 0%, var(--accent-dark) 100%);
          border:1px solid var(--bw2-edge-strong);
          box-shadow:0 0 0 2px rgba(0,0,0,.18);
          transform:rotate(45deg);
        }
        .ju-hero-title{
          font-family:var(--font-pixel);
          font-size:12px;
          line-height:1.3;
          margin-bottom:8px;
          color:#ffffff;
          text-transform:uppercase;
        }
        .ju-hero-sub{
          font-size:18px;
          color:var(--bw2-text-soft);
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
          font-family:var(--font-pixel);
          color:#ffffff;
          background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);
          border:1px solid var(--bw2-edge-strong);
          border-radius:0;
          padding:4px 8px;
          text-transform:uppercase;
        }
        .ju-toolbar{
          background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          margin:8px 0 10px 0;
          color:var(--bw2-text-soft);
          font-size:18px;
          font-weight:400;
        }
        .ju-note{
          background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          border:1px dashed var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          color:var(--bw2-text-soft);
          font-size:18px;
        }
        .ju-sep{
          height:2px;
          background:linear-gradient(90deg,transparent 0,var(--accent) 20%,var(--accent) 80%,transparent 100%);
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
          border:1px solid var(--bw2-edge);
          border-radius:0;
          text-align:center;
          padding:6px 8px;
          background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          color:var(--bw2-text-soft);
          font-weight:400;
          font-size:18px;
          box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
        }
        .ju-stage-on{
          background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);
          border-color:var(--bw2-edge-strong);
          color:#ffffff;
        }
        .ju-docket{
          background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          margin-bottom:8px;
          color:var(--bw2-text);
        }
        .ju-docket-title{
          font-family:var(--font-pixel);
          font-size:10px;
          margin-bottom:5px;
          color:#ffffff;
          text-transform:uppercase;
        }
        .ju-docket-sub{
          font-size:18px;
          color:var(--bw2-text-soft);
        }
        .ju-verdict{
          display:inline-block;
          padding:3px 8px;
          border-radius:0;
          font-size:10px;
          font-weight:700;
          font-family:var(--font-pixel);
          margin-left:6px;
          border:1px solid var(--bw2-edge-strong);
          background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          color:#ffffff;
          text-transform:uppercase;
        }
        .ju-v-guilty{ background:linear-gradient(180deg,#ef5e68 0%, #962d37 100%); border-color:#ffd6da; color:#ffffff; }
        .ju-v-not-guilty{ background:linear-gradient(180deg,#58d18e 0%, #2a8d5c 100%); border-color:#d8ffee; color:#ffffff; }
        .ju-v-pending{ background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%); border-color:#ffe1ca; color:#ffffff; }
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
    _render_juicio_hero()
    current_user = st.session_state.get("user") or ""
    if not current_user:
        st.info("Inicia sesion para usar la seccion de juicios.")
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
