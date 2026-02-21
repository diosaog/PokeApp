from __future__ import annotations

import streamlit as st

from app.juicios.forms import render_case_form
from app.juicios.penalties import get_user_penalties
from app.juicios.render import case_header, render_case_info
from app.juicios.repo import (
    can_edit_case,
    create_case,
    list_cases_for_user,
    next_case_number,
    update_case,
)


def _show_active_penalties(user: str) -> None:
    pen = get_user_penalties(user)
    if not pen.get("sources"):
        return
    st.warning("Tienes castigos activos derivados de juicios.")
    if pen.get("store_blocked"):
        st.caption("- Tienda y monedas bloqueadas.")
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
    sent, payload = render_case_form(
        form_key="juicio_new_form",
        case_no=next_case_number(),
        current_user=current_user,
        initial={"is_public": True, "status": "abierto", "priority": "Media"},
        can_edit_status=False,
    )
    if sent and payload:
        create_case(current_user, payload)
        st.success("Juicio creado.")
        st.session_state["juicio_show_new_form"] = False
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()


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
        cid = int(case.get("id") or 0)
        with st.expander(case_header(case), expanded=False):
            render_case_info(case)
            if not can_edit_case(case, current_user):
                st.caption("Solo el creador puede editar este juicio.")
                continue

            edit_key = f"juicio_edit_open_{cid}"
            if not st.session_state.get(edit_key, False):
                if st.button("Editar juicio", key=f"juicio_edit_btn_{cid}"):
                    st.session_state[edit_key] = True
                    st.rerun()
            else:
                sent, payload = render_case_form(
                    form_key=f"juicio_edit_form_{cid}",
                    case_no=int(case.get("case_no") or 0),
                    current_user=current_user,
                    initial=case,
                    can_edit_status=True,
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
                        update_case(cid, current_user, payload)
                        st.success("Juicio actualizado.")
                        st.session_state[edit_key] = False
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))


def page_juicios() -> None:
    st.header("Juicios")
    current_user = st.session_state.get("user") or ""
    if not current_user:
        st.info("Inicia sesion para usar la seccion de juicios.")
        return

    _show_active_penalties(current_user)

    c1, c2 = st.columns([1.2, 3])
    with c1:
        show_new = bool(st.session_state.get("juicio_show_new_form", False))
        label = "Cerrar formulario" if show_new else "Hacer un Juicio"
        if st.button(label, type="primary", use_container_width=True):
            st.session_state["juicio_show_new_form"] = not show_new
            st.rerun()
    with c2:
        st.caption(
            "Ideas incluidas: testigos, prioridad, categoria y solicitud de votacion publica."
        )

    if st.session_state.get("juicio_show_new_form"):
        _render_create_case(current_user)

    _render_case_list(current_user)

