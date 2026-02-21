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
    PENALTY_TEMPLATES,
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


def _default_hearing_date(raw_date: str) -> date:
    try:
        yy, mm, dd = [int(x) for x in str(raw_date).split("-", 2)]
        return date(yy, mm, dd)
    except Exception:
        return date.today()


def _apply_template_to_map(
    penalty_map: dict[str, dict[str, Any]],
    template_name: str | None,
) -> dict[str, dict[str, Any]]:
    if not template_name:
        return penalty_map
    tpl = list(PENALTY_TEMPLATES.get(template_name) or [])
    if not tpl:
        return penalty_map
    out: dict[str, dict[str, Any]] = {}
    for item in tpl:
        ptype = str(item.get("type") or "").strip()
        if not ptype:
            continue
        out[ptype] = dict(item)
    return out


def render_case_details_form(
    *,
    form_key: str,
    case_no: int,
    current_user: str,
    initial: dict[str, Any] | None = None,
    submit_label: str,
) -> tuple[bool, dict[str, Any] | None]:
    base = dict(initial or {})
    users = list(USERS.keys())
    default_accused = str(base.get("accused") or (users[0] if users else ""))
    if default_accused not in users and users:
        default_accused = users[0]

    date_default = _default_hearing_date(str(base.get("hearing_date") or date.today().isoformat()))

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
        jury_size = int(base.get("jury_size") or 5)
        jury_size = st.number_input(
            "Tamano del jurado (impar)",
            min_value=3,
            max_value=9,
            step=2,
            value=(jury_size if jury_size in (3, 5, 7, 9) else 5),
        )

        submitted = st.form_submit_button(submit_label, type="primary")

    if not submitted:
        return False, None

    errors: list[str] = []
    if not (title or "").strip():
        errors.append("El titulo del juicio es obligatorio.")
    if not (summary or "").strip():
        errors.append("La razon resumida del juicio es obligatoria.")
    if not accused:
        errors.append("Debes indicar un acusado.")
    if int(jury_size) not in (3, 5, 7, 9):
        errors.append("El jurado debe ser impar: 3, 5, 7 o 9.")

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
        "jury_size": int(jury_size),
    }
    return True, payload


def render_resolution_form(
    *,
    form_key: str,
    initial: dict[str, Any] | None = None,
    submit_label: str = "Guardar castigos",
    template_name: str | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    base = dict(initial or {})
    penalty_map = _penalty_defaults(list(base.get("penalties") or []))
    penalty_map = _apply_template_to_map(penalty_map, template_name)
    penalty_selected_default = [p for p in PENALTY_ORDER if p in penalty_map]

    with st.form(form_key):
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
        )
        submitted = st.form_submit_button(submit_label, type="primary")

    if not submitted:
        return False, None

    penalties, errors = _build_penalties(
        selected=penalties_selected,
        coin_amount=int(coin_amount),
        points_amount=float(points_amount),
        pokemon_text=pokemon_text,
        other_text=other_text,
    )
    if not penalties:
        errors.append("Debes proponer al menos un castigo para iniciar/finalizar el juicio.")
    if errors:
        for err in errors:
            st.error(err)
        return True, None

    payload = {
        "penalties": penalties,
        "resolution_notes": (resolution_notes or "").strip(),
    }
    return True, payload
