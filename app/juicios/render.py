from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from app.juicios.constants import PENALTY_LABELS, STATUS_LABELS


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def case_header(case: dict[str, Any]) -> str:
    case_no = int(case.get("case_no") or 0)
    title = str(case.get("title") or "Sin titulo").strip()
    status = STATUS_LABELS.get(str(case.get("status") or ""), str(case.get("status") or "-"))
    return f"Caso #{case_no} · {title} · {status}"


def render_case_info(case: dict[str, Any]) -> None:
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
        st.caption(f"Resuelto: {_fmt_ts(case.get('resolved_at'))}")

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
        st.markdown("**Castigos configurados**")
        for p in penalties:
            ptype = str(p.get("type") or "")
            label = PENALTY_LABELS.get(ptype, ptype)
            if "amount" in p:
                st.write(f"- {label}: {p.get('amount')}")
            elif "text" in p:
                st.write(f"- {label}: {p.get('text')}")
            else:
                st.write(f"- {label}")
    else:
        st.caption("Sin castigos configurados todavia.")

