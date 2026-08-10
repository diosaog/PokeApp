from __future__ import annotations

from datetime import datetime
import html as _html
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
                label=_html.escape(label),
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


def _meta_cell(label: str, value: Any) -> str:
    text = "-" if value in (None, "") else str(value)
    return (
        "<div class='ju-docket-cell'>"
        f"<span>{_html.escape(label)}</span>"
        f"<strong>{_html.escape(text)}</strong>"
        "</div>"
    )


def _detail_block(title: str, body: Any) -> str:
    text = "-" if body in (None, "") else str(body)
    return (
        "<div class='ju-detail-block'>"
        f"<span>{_html.escape(title)}</span>"
        f"{_html.escape(text)}"
        "</div>"
    )


def _penalty_text(penalty: dict[str, Any]) -> str:
    ptype = str(penalty.get("type") or "")
    label = PENALTY_LABELS.get(ptype, ptype)
    if ptype == "store_ban":
        try:
            start = int(penalty.get("start_tramo") or 0)
            end = int(penalty.get("end_tramo") or 0)
        except Exception:
            start, end = 0, 0
        if start > 0 and end > 0:
            return f"{label}: tramo {start}-{end}"
        return label
    if "amount" in penalty:
        return f"{label}: {penalty.get('amount')}"
    if "text" in penalty:
        return f"{label}: {penalty.get('text')}"
    return label


def render_case_info(case: dict[str, Any]) -> None:
    status = _normalize_status(case.get("status"))
    case_no = int(case.get("case_no") or 0)
    title = _html.escape(str(case.get("title") or "Sin titulo").strip())
    verdict = _html.escape(VERDICT_LABELS.get(str(case.get("verdict") or ""), "Pendiente"))
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

    jury_size = int(case.get("jury_size") or 5)
    votes = list(case.get("jury_votes") or [])
    guilty_votes = sum(1 for v in votes if str(v.get("vote") or "") == VOTE_GUILTY)
    not_guilty_votes = sum(1 for v in votes if str(v.get("vote") or "") == VOTE_NOT_GUILTY)
    majority = jury_size // 2 + 1
    verdict = VERDICT_LABELS.get(str(case.get("verdict") or ""), "Pendiente")
    st.markdown(
        (
            "<div class='ju-docket-meta'>"
            + _meta_cell("Creador", case.get("creator") or "-")
            + _meta_cell("Acusado", case.get("accused") or "-")
            + _meta_cell("Prioridad", case.get("priority") or "-")
            + _meta_cell("Fecha juicio", case.get("hearing_date") or "-")
            + _meta_cell("Publico", "Si" if case.get("is_public") else "No")
            + _meta_cell("Categoria", case.get("category") or "-")
            + _meta_cell("Creado", _fmt_ts(case.get("created_at")))
            + _meta_cell("Actualizado", _fmt_ts(case.get("updated_at")))
            + _meta_cell("Finalizado", _fmt_ts(case.get("resolved_at")))
            + "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            "<div class='ju-detail-block'>"
            "<span>Jurado y veredicto</span>"
            f"Jurado: {jury_size} | Mayoria: {majority} | "
            f"Culpable: {guilty_votes} | No culpable: {not_guilty_votes} | "
            f"Veredicto: {_html.escape(verdict)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if votes:
        with st.expander("Ver votos del jurado", expanded=False):
            for v in votes:
                jury = str(v.get("jury") or "-")
                vote = "Culpable" if str(v.get("vote") or "") == VOTE_GUILTY else "No culpable"
                st.caption(f"- {jury}: {vote}")

    details = [
        _detail_block("Razon resumida", case.get("summary") or "-"),
        _detail_block("Pruebas", case.get("evidence") or "-"),
        _detail_block("Testigos", case.get("witnesses") or "-"),
        _detail_block("Votacion publica", "Si" if case.get("public_vote") else "No"),
    ]
    st.markdown(
        "<div class='ju-detail-grid'>" + "".join(details) + "</div>",
        unsafe_allow_html=True,
    )

    if case.get("resolution_notes"):
        st.markdown(
            _detail_block("Resolucion", case.get("resolution_notes")),
            unsafe_allow_html=True,
        )

    penalties = list(case.get("penalties") or [])
    if penalties:
        title = "Castigos aplicados" if status == STATUS_FINISHED else "Castigos propuestos"
        lines = "<br/>".join(_html.escape(_penalty_text(p)) for p in penalties)
        st.markdown(
            (
                "<div class='ju-detail-block'>"
                f"<span>{_html.escape(title)}</span>"
                f"{lines}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='ju-note'>Sin castigos propuestos todavia.</div>",
            unsafe_allow_html=True,
        )
