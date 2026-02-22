from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from app.juicios.constants import (
    PENALTY_LABELS,
    STATUS_COLORS,
    STATUS_FINISHED,
    STATUS_LABELS,
    STATUS_ORDER,
    STATUS_PROPOSED,
    VERDICT_LABELS,
    VOTE_GUILTY,
    VOTE_NOT_GUILTY,
)


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def _normalize_status(raw: Any) -> str:
    status = str(raw or "").strip()
    if status in STATUS_LABELS:
        return status
    return STATUS_PROPOSED


def _stage_boxes_html(status: str) -> str:
    current = _normalize_status(status)
    current_idx = STATUS_ORDER.index(current)
    boxes: list[str] = []
    for idx, stage in enumerate(STATUS_ORDER):
        color = STATUS_COLORS.get(stage, "#6c757d")
        label = STATUS_LABELS.get(stage, stage)
        reached_cls = " ju-stage-on" if idx <= current_idx else ""
        boxes.append(
            "<div class='ju-stage{reached}' style='--stage-color:{color};'>{label}</div>".format(
                reached=reached_cls,
                color=color,
                label=label,
            )
        )
    return "<div class='ju-stage-wrap'>{}</div>".format("".join(boxes))


def _verdict_css_class(verdict_raw: Any) -> str:
    verdict = str(verdict_raw or "").strip().lower()
    if verdict == "culpable":
        return "ju-v-guilty"
    if verdict == "no_culpable":
        return "ju-v-not-guilty"
    return "ju-v-pending"


def case_header(case: dict[str, Any]) -> str:
    case_no = int(case.get("case_no") or 0)
    title = str(case.get("title") or "Sin titulo").strip()
    status = STATUS_LABELS.get(str(case.get("status") or ""), str(case.get("status") or "-"))
    return f"Caso #{case_no} | {title} | {status}"


def render_case_info(case: dict[str, Any]) -> None:
    status = _normalize_status(case.get("status"))
    case_no = int(case.get("case_no") or 0)
    title = str(case.get("title") or "Sin titulo").strip()
    verdict = VERDICT_LABELS.get(str(case.get("verdict") or ""), "Pendiente")
    verdict_cls = _verdict_css_class(case.get("verdict"))
    st.markdown(
        (
            "<div class='ju-docket'>"
            f"<div class='ju-docket-title'>EXPEDIENTE #{case_no}</div>"
            f"<div class='ju-docket-sub'>{title} <span class='ju-verdict {verdict_cls}'>{verdict}</span></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_stage_boxes_html(status), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption(f"Creador: {case.get('creator') or '-'}")
        st.caption(f"Acusado: {case.get('accused') or '-'}")
        st.caption(f"Prioridad: {case.get('priority') or '-'}")
    with c2:
        st.caption(f"Fecha juicio: {case.get('hearing_date') or '-'}")
        st.caption(f"Publico: {'Si' if case.get('is_public') else 'No'}")
        st.caption(f"Categoria: {case.get('category') or '-'}")
    with c3:
        st.caption(f"Creado: {_fmt_ts(case.get('created_at'))}")
        st.caption(f"Actualizado: {_fmt_ts(case.get('updated_at'))}")
        st.caption(f"Finalizado: {_fmt_ts(case.get('resolved_at'))}")

    jury_size = int(case.get("jury_size") or 5)
    votes = list(case.get("jury_votes") or [])
    guilty_votes = sum(1 for v in votes if str(v.get("vote") or "") == VOTE_GUILTY)
    not_guilty_votes = sum(1 for v in votes if str(v.get("vote") or "") == VOTE_NOT_GUILTY)
    majority = jury_size // 2 + 1
    verdict = VERDICT_LABELS.get(str(case.get("verdict") or ""), "Pendiente")
    st.caption(
        f"Jurado: {jury_size} | Mayoria: {majority} | "
        f"Culpable: {guilty_votes} | No culpable: {not_guilty_votes} | Veredicto: {verdict}"
    )

    if votes:
        with st.expander("Ver votos del jurado", expanded=False):
            for v in votes:
                jury = str(v.get("jury") or "-")
                vote = "Culpable" if str(v.get("vote") or "") == VOTE_GUILTY else "No culpable"
                st.caption(f"- {jury}: {vote}")

    st.markdown("**Razon resumida**")
    st.write(case.get("summary") or "-")

    st.markdown("**Pruebas e informacion relevante**")
    st.write(case.get("evidence") or "-")

    st.markdown("**Extras**")
    st.write(f"Testigos: {case.get('witnesses') or '-'}")
    st.write(f"Votacion publica solicitada: {'Si' if case.get('public_vote') else 'No'}")

    if case.get("resolution_notes"):
        st.markdown("**Resolucion**")
        st.write(case.get("resolution_notes"))

    penalties = list(case.get("penalties") or [])
    if penalties:
        title = "**Castigos aplicados**" if status == STATUS_FINISHED else "**Castigos propuestos**"
        st.markdown(title)
        for p in penalties:
            ptype = str(p.get("type") or "")
            label = PENALTY_LABELS.get(ptype, ptype)
            if ptype == "store_ban":
                try:
                    start = int(p.get("start_tramo") or 0)
                    end = int(p.get("end_tramo") or 0)
                except Exception:
                    start, end = 0, 0
                if start > 0 and end > 0:
                    st.write(f"- {label}: tramo {start}-{end}")
                else:
                    st.write(f"- {label}")
                continue
            if "amount" in p:
                st.write(f"- {label}: {p.get('amount')}")
            elif "text" in p:
                st.write(f"- {label}: {p.get('text')}")
            else:
                st.write(f"- {label}")
    else:
        st.caption("Sin castigos propuestos todavia.")
