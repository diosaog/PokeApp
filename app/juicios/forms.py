from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from app.juicios.constants import (
    PENALTY_COINS_REDUCTION,
    PENALTY_LABELS,
    PENALTY_ORDER,
    PENALTY_OTHER,
    PENALTY_POKEMON_RELEASE,
    PENALTY_POINTS_REDUCTION,
    PENALTY_STORE_BAN,
    STATUS_LABELS,
    STATUS_ORDER,
)
from utils import USERS


def _penalty_defaults(penalties: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in penalties or []:
        ptype = str(p.get("type") or "").strip()
        if ptype:
            out[ptype] = dict(p)
    return out


def _build_penalties(
    *,
    selected: list[str],
    coin_amount: int,
    points_amount: float,
    pokemon_text: str,
    other_text: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    penalties: list[dict[str, Any]] = []
    errors: list[str] = []

    for ptype in selected:
        if ptype == PENALTY_STORE_BAN:
            penalties.append({"type": ptype})
            continue
        if ptype == PENALTY_COINS_REDUCTION:
            if int(coin_amount) <= 0:
                errors.append("La reduccion de monedas debe ser mayor que 0.")
            else:
                penalties.append({"type": ptype, "amount": int(coin_amount)})
            continue
        if ptype == PENALTY_POINTS_REDUCTION:
            if float(points_amount) <= 0:
                errors.append("La reduccion de puntos debe ser mayor que 0.")
            else:
                penalties.append({"type": ptype, "amount": float(points_amount)})
            continue
        if ptype == PENALTY_POKEMON_RELEASE:
            txt = (pokemon_text or "").strip()
            if not txt:
                errors.append("Describe el Pokemon a liberar/matar para aplicar ese castigo.")
            else:
                penalties.append({"type": ptype, "text": txt})
            continue
        if ptype == PENALTY_OTHER:
            txt = (other_text or "").strip()
            if not txt:
                errors.append("El castigo 'Otro' requiere una descripcion.")
            else:
                penalties.append({"type": ptype, "text": txt})
            continue
    return penalties, errors


def render_case_form(
    *,
    form_key: str,
    case_no: int,
    current_user: str,
    initial: dict[str, Any] | None = None,
    can_edit_status: bool,
) -> tuple[bool, dict[str, Any] | None]:
    base = dict(initial or {})
    users = list(USERS.keys())
    default_accused = str(base.get("accused") or (users[0] if users else ""))
    if default_accused not in users and users:
        default_accused = users[0]

    default_date = str(base.get("hearing_date") or date.today().isoformat())
    try:
        yy, mm, dd = [int(x) for x in default_date.split("-", 2)]
        date_default = date(yy, mm, dd)
    except Exception:
        date_default = date.today()

    selected_status = str(base.get("status") or "abierto")
    if selected_status not in STATUS_LABELS:
        selected_status = "abierto"

    penalty_map = _penalty_defaults(list(base.get("penalties") or []))
    penalty_selected_default = [p for p in PENALTY_ORDER if p in penalty_map]

    with st.form(form_key):
        st.markdown(f"**Caso del Juicio:** #{case_no}")
        st.caption(f"Creador: {current_user}")

        title = st.text_input("Titulo del juicio", value=str(base.get("title") or ""))
        accused = st.selectbox(
            "Nombre del acusado",
            users,
            index=(users.index(default_accused) if default_accused in users else 0),
        )
        summary = st.text_area("Razon del juicio (resumido)", value=str(base.get("summary") or ""), height=80)
        hearing_date = st.date_input("Fecha posible para la realizacion", value=date_default)
        is_public = st.toggle("Juicio visible/publico", value=bool(base.get("is_public", True)))
        evidence = st.text_area(
            "Pruebas e informacion relevante",
            value=str(base.get("evidence") or ""),
            height=140,
        )

        st.markdown("**Ideas adicionales**")
        witnesses = st.text_input("Testigos o participantes (opcional)", value=str(base.get("witnesses") or ""))
        priority_options = ["Baja", "Media", "Alta"]
        priority_default = str(base.get("priority") or "Media")
        if priority_default not in priority_options:
            priority_default = "Media"
        priority = st.selectbox("Prioridad", priority_options, index=priority_options.index(priority_default))
        category = st.text_input("Categoria o etiqueta (opcional)", value=str(base.get("category") or ""))
        public_vote = st.toggle("Solicitar votacion publica (opcional)", value=bool(base.get("public_vote", False)))

        if can_edit_status:
            status_labels = [STATUS_LABELS[s] for s in STATUS_ORDER]
            status_idx = STATUS_ORDER.index(selected_status)
            status_label = st.selectbox("Estado del juicio", status_labels, index=status_idx)
            status = next(k for k, v in STATUS_LABELS.items() if v == status_label)
        else:
            status = "abierto"
            st.caption("Estado inicial: Abierto")

        st.markdown("**Castigos predefinidos**")
        penalties_selected = st.multiselect(
            "Puedes aplicar uno o mas castigos",
            options=PENALTY_ORDER,
            default=penalty_selected_default,
            format_func=lambda x: PENALTY_LABELS.get(x, x),
        )
        coin_amount = st.number_input(
            "Monedas a reducir",
            min_value=0,
            step=1,
            value=int(penalty_map.get(PENALTY_COINS_REDUCTION, {}).get("amount") or 0),
            disabled=PENALTY_COINS_REDUCTION not in penalties_selected,
        )
        points_amount = st.number_input(
            "Puntos a reducir",
            min_value=0.0,
            step=0.5,
            value=float(penalty_map.get(PENALTY_POINTS_REDUCTION, {}).get("amount") or 0.0),
            disabled=PENALTY_POINTS_REDUCTION not in penalties_selected,
        )
        pokemon_text = st.text_area(
            "Detalle de liberacion/muerte de Pokemon",
            value=str(penalty_map.get(PENALTY_POKEMON_RELEASE, {}).get("text") or ""),
            height=80,
            disabled=PENALTY_POKEMON_RELEASE not in penalties_selected,
        )
        other_text = st.text_area(
            "Castigo personalizado (Otro)",
            value=str(penalty_map.get(PENALTY_OTHER, {}).get("text") or ""),
            height=80,
            disabled=PENALTY_OTHER not in penalties_selected,
        )

        resolution_notes = st.text_area(
            "Resolucion / observaciones finales",
            value=str(base.get("resolution_notes") or ""),
            height=90,
            disabled=(status not in ("resuelto", "cancelado")),
        )

        submitted = st.form_submit_button("Guardar juicio", type="primary")

    if not submitted:
        return False, None

    errors: list[str] = []
    if not (title or "").strip():
        errors.append("El titulo del juicio es obligatorio.")
    if not (summary or "").strip():
        errors.append("La razon resumida del juicio es obligatoria.")
    if not accused:
        errors.append("Debes indicar un acusado.")

    penalties, penalty_errors = _build_penalties(
        selected=penalties_selected,
        coin_amount=int(coin_amount),
        points_amount=float(points_amount),
        pokemon_text=pokemon_text,
        other_text=other_text,
    )
    errors.extend(penalty_errors)

    if status == "resuelto" and not penalties:
        errors.append("Un juicio resuelto debe tener al menos un castigo.")

    if errors:
        for err in errors:
            st.error(err)
        return True, None

    payload = {
        "title": (title or "").strip(),
        "accused": accused,
        "summary": (summary or "").strip(),
        "hearing_date": hearing_date.isoformat(),
        "is_public": bool(is_public),
        "evidence": (evidence or "").strip(),
        "witnesses": (witnesses or "").strip(),
        "priority": priority,
        "category": (category or "").strip(),
        "public_vote": bool(public_vote),
        "status": status,
        "resolution_notes": (resolution_notes or "").strip(),
        "penalties": penalties,
    }
    return True, payload

