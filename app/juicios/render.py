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
        reached = idx <= current_idx
        bg = color if reached else "#f2f2f2"
        fg = "#ffffff" if reached else "#5f6368"
        boxes.append(
            "<div style='flex:1; min-width:0; border:1px solid {color}; border-radius:8px; "
            "padding:6px 8px; text-align:center; background:{bg}; color:{fg}; font-weight:700; font-size:12px;'>"
            "{label}</div>".format(color=color, bg=bg, fg=fg, label=label)
        )
    return "<div style='display:flex; gap:8px; margin:6px 0 12px 0;'>{}</div>".format("".join(boxes))


def case_header(case: dict[str, Any]) -> str:
    case_no = int(case.get("case_no") or 0)
    title = str(case.get("title") or "Sin titulo").strip()
    status = STATUS_LABELS.get(str(case.get("status") or ""), str(case.get("status") or "-"))
    return f"Caso #{case_no} | {title} | {status}"


def render_case_info(case: dict[str, Any]) -> None:
    status = _normalize_status(case.get("status"))
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
