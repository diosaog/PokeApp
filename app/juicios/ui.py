from __future__ import annotations

from datetime import datetime
import html as _html

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
from app.juicios.penalties import clear_penalty_caches
from app.juicios.penalties import get_user_penalties
from app.juicios.render import render_case_info
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
from app.tienda.money import clear_money_caches
from utils import active_users, users_with_retired_last


STATUS_BADGE_LABELS = {
    STATUS_PROPOSED: "Propuesto",
    STATUS_IN_PROGRESS: "En proceso",
    STATUS_FINISHED: "Archivado",
}


def _clear_cache() -> None:
    clear_penalty_caches()
    clear_money_caches()


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
          font-size:clamp(16px, 2.4vw, 26px);
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
        .ju-metric-grid{
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:10px;
          margin:10px 0 14px;
        }
        .ju-metric{
          min-height:82px;
          background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:10px 12px;
          color:var(--bw2-text);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 0 0 1px rgba(0,0,0,.28);
        }
        .ju-metric-label,
        .ju-metric-value,
        .ju-action-title,
        .ju-status-badge{
          font-family:var(--font-pixel);
          text-transform:uppercase;
        }
        .ju-metric-label{
          color:var(--bw2-text-soft);
          font-size:8px;
        }
        .ju-metric-value{
          margin-top:9px;
          color:#ffffff;
          font-size:16px;
          line-height:1.15;
        }
        .ju-action-grid{
          display:grid;
          grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);
          gap:10px;
          margin:10px 0 12px;
        }
        .ju-action-card,
        .ju-penalty-card{
          background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:12px;
          color:var(--bw2-text-soft);
          box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 0 0 1px rgba(0,0,0,.28);
        }
        .ju-action-title{
          color:#ffffff;
          font-size:11px;
          line-height:1.25;
        }
        .ju-action-sub,
        .ju-penalty-line{
          margin-top:8px;
          color:var(--bw2-text-soft);
          font-family:var(--font-ui);
          font-size:18px;
          line-height:1.2;
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
        .ju-filter-grid{
          display:grid;
          grid-template-columns:repeat(2,minmax(0,1fr));
          gap:10px;
          margin:10px 0;
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
        .ju-status-badge{
          display:inline-flex;
          align-items:center;
          min-height:24px;
          padding:4px 8px;
          border:1px solid var(--bw2-edge);
          background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          color:#ffffff;
          font-size:8px;
        }
        .ju-status-badge.is-active{
          border-color:var(--bw2-edge-strong);
          background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);
        }
        @media (max-width: 900px){
          .ju-metric-grid,
          .ju-action-grid,
          .ju-filter-grid{
            grid-template-columns:1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_juicio_hero() -> None:
    st.markdown(
        """
        <div class='ju-hero'>
          <div class='ju-hero-title'>Tribunal Pokemon</div>
          <div class='ju-hero-sub'>Expedientes, votos y sanciones en una vista mas directa.</div>
          <div class='ju-hero-chips'>
            <span class='ju-chip'>Casos</span>
            <span class='ju-chip'>Jurado</span>
            <span class='ju-chip'>Sanciones</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_case_ts(value: object) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def _case_status(case: dict) -> str:
    status = str(case.get("status") or STATUS_PROPOSED)
    if status in STATUS_BADGE_LABELS:
        return status
    return STATUS_PROPOSED


def _render_metric(label: str, value: str) -> str:
    return (
        "<div class='ju-metric'>"
        f"<div class='ju-metric-label'>{_html.escape(label)}</div>"
        f"<div class='ju-metric-value'>{_html.escape(value)}</div>"
        "</div>"
    )


def _render_case_metrics(cases: list[dict], current_user: str) -> None:
    total = len(cases)
    proposed = sum(1 for case in cases if _case_status(case) == STATUS_PROPOSED)
    progress = sum(1 for case in cases if _case_status(case) == STATUS_IN_PROGRESS)
    mine = sum(1 for case in cases if str(case.get("creator") or "") == str(current_user))
    html = "".join(
        [
            _render_metric("Expedientes", str(total)),
            _render_metric("Propuestos", str(proposed)),
            _render_metric("En proceso", str(progress)),
            _render_metric("Mios", str(mine)),
        ]
    )
    st.markdown(f"<div class='ju-metric-grid'>{html}</div>", unsafe_allow_html=True)


def _status_badge_html(status: str) -> str:
    label = STATUS_BADGE_LABELS.get(status, status)
    active = " is-active" if status != STATUS_FINISHED else ""
    return f"<span class='ju-status-badge{active}'>{_html.escape(label)}</span>"


def _case_summary_rows(cases: list[dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        status = _case_status(case)
        rows.append(
            {
                "#": int(case.get("case_no") or 0),
                "Estado": STATUS_BADGE_LABELS.get(status, status),
                "Titulo": str(case.get("title") or "Sin titulo"),
                "Acusado": str(case.get("accused") or "-"),
                "Prioridad": str(case.get("priority") or "-"),
                "Fecha": str(case.get("hearing_date") or "-"),
                "Actualizado": _fmt_case_ts(case.get("updated_at")),
            }
        )
    return rows


def _case_option_label(case: dict) -> str:
    status = STATUS_BADGE_LABELS.get(_case_status(case), "-")
    case_no = int(case.get("case_no") or 0)
    title = str(case.get("title") or "Sin titulo").strip()
    accused = str(case.get("accused") or "-")
    return f"#{case_no} | {status} | {accused} | {title}"


def _show_active_penalties(user: str) -> None:
    pen = get_user_penalties(user)
    if not pen.get("sources"):
        return
    lines = ["Tienes castigos activos derivados de juicios."]
    if pen.get("store_blocked"):
        lines.append("Tienda y monedas bloqueadas.")
        tramos = list(pen.get("store_ban_tramos") or [])
        if tramos:
            tramos_text = ", ".join(str(tramo) for tramo in tramos)
            lines.append(f"Bloqueo por tramo: {tramos_text}.")
    if pen.get("coins_reduction"):
        lines.append(f"Reduccion de monedas: {pen.get('coins_reduction')}.")
    if pen.get("points_reduction"):
        lines.append(f"Reduccion de puntos: {pen.get('points_reduction')}.")
    for txt in pen.get("pokemon_release_notes") or []:
        lines.append(f"Liberacion/Muerte de Pokemon: {txt}")
    for txt in pen.get("other_notes") or []:
        lines.append(f"Otro castigo: {txt}")
    body = "".join(
        f"<div class='ju-penalty-line'>{_html.escape(str(line))}</div>"
        for line in lines
    )
    st.markdown(
        (
            "<div class='ju-penalty-card'>"
            "<div class='ju-action-title'>Sanciones activas</div>"
            f"{body}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("<div class='ju-sep'></div>", unsafe_allow_html=True)


def _render_create_case(current_user: str) -> None:
    st.markdown(
        (
            "<div class='ju-action-card'>"
            "<div class='ju-action-title'>Nuevo expediente</div>"
            "<div class='ju-action-sub'>Define acusado, motivo, pruebas y jurado.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
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
    jury_options = users_with_retired_last(active_users())
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
    st.markdown("<div class='ju-sep'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='ju-toolbar'>Bandeja judicial: filtra, revisa y abre un expediente.</div>",
        unsafe_allow_html=True,
    )

    all_cases = list_cases_for_user(current_user)
    _render_case_metrics(all_cases, current_user)

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

    cases = list(all_cases)
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

    cases.sort(
        key=lambda case: (
            _case_status(case) == STATUS_FINISHED,
            -int(case.get("updated_at") or case.get("created_at") or 0),
            int(case.get("case_no") or 0),
        )
    )
    rows = _case_summary_rows(cases)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    case_by_id = {int(case.get("id") or 0): case for case in cases}
    case_ids = [cid for cid in case_by_id if cid]
    if not case_ids:
        st.info("No se encontro ningun expediente valido.")
        return
    previous_id = int(st.session_state.get("juicio_selected_case_id") or 0)
    if previous_id not in case_ids:
        st.session_state["juicio_selected_case_id"] = case_ids[0]
        previous_id = case_ids[0]
    selected_index = case_ids.index(previous_id)
    selected_id = st.selectbox(
        "Abrir expediente",
        options=case_ids,
        index=selected_index,
        format_func=lambda cid: _case_option_label(case_by_id[int(cid)]),
        key="juicio_selected_case_id",
    )
    case = case_by_id[int(selected_id)]
    status = _case_status(case)
    title = _html.escape(_case_option_label(case))
    st.markdown(
        (
            "<div class='ju-action-card'>"
            f"{_status_badge_html(status)}"
            f"<div class='ju-action-title' style='margin-top:10px;'>{title}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        render_case_info(case)

        _render_jury_vote_controls(case, current_user)

        if not can_edit_case(case, current_user):
            st.caption("Solo el creador puede editar este juicio.")
            return

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
    action_title = "Cerrar nuevo expediente" if show_new else "Nuevo expediente"
    action_sub = (
        "El formulario esta abierto."
        if show_new
        else "Crea un caso y dejalo en etapa Propuesto."
    )
    st.markdown(
        (
            "<div class='ju-action-grid'>"
            "<div class='ju-action-card'>"
            f"<div class='ju-action-title'>{action_title}</div>"
            f"<div class='ju-action-sub'>{action_sub}</div>"
            "</div>"
            "<div class='ju-action-card'>"
            "<div class='ju-action-title'>Flujo</div>"
            "<div class='ju-action-sub'>Propuesto -> En proceso -> Archivado.</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    label = "Cerrar formulario" if show_new else "Abrir nuevo juicio"
    if st.button(label, type="primary", use_container_width=True):
        st.session_state["juicio_show_new_form"] = not show_new
        st.rerun()

    if st.session_state.get("juicio_show_new_form"):
        _render_create_case(current_user)

    _render_case_list(current_user)
