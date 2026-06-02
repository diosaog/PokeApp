from __future__ import annotations
from datetime import datetime
import streamlit as st

from app.interfaz.theme import apply_platinum_ui
from app.saves_support import (
    SAVES_PAGE_CSS,
    bootstrap_latest_save,
    clear_save_related_caches,
    current_save_meta_html,
    refresh_save_snapshot,
    write_uploaded_save_copy,
)
from storage import (
    wipe_all_app_data,
    save_upload,
    load_save_bytes,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
)

_PRIVATE_NEXT_LOCKE_PROMPT = """Ya se ha hecho el WIPE y empieza una temporada nueva. Ajusta PokeApp para que la liga nazca
directamente con 10 jugadores, sin Mario, sin compatibilidad temporal con las jornadas 1/2
de la temporada anterior y con dos divisiones de 5 desde la jornada 1.

Mantener desde la jornada 1 estas tablas definitivas:
MONEDAS: 1=15, 2=14, 3=12, 4=11, 5=10, 6=11, 7=9, 8=8, 9=6, 10=4.
PUNTOS: 1=9, 2=8, 3=7, 4=6, 5=5, 6=5, 7=4, 8=3, 9=2, 10=1.

Retira de una vez toda la transicion que se puso para terminar la jornada 2 antigua:
- Elimina definitivamente a Mario de USERS y cualquier asset o referencia estatica suya.
- En utils.py elimina ROSTER_DEPARTURE_AFTER_ROUND y la logica de roster por jornada/salida
  de Mario; deja los selectores funcionando con el roster fijo de 10.
- En app/liga/state.py elimina roster_transition_complete /
  league_roster_transition_complete y la normalizacion creada solo para retirar a Mario.
  Elimina tambien el parche historico creado solo para esta temporada que fuerza a Mario
  como puesto 5 del tramo 2 y desplaza una posicion la Liga B; en concreto limpia cualquier
  helper tipo _forced_historical_positions, _insert_forced_positions o reparacion especial
  de resultados desde matches que solo exista para conservar las jornadas antiguas.
- En app/liga/ui.py elimina la excepcion visual del historial que trata el tramo 2 con
  Mario en posicion 5 para recalcular el rango de Liga A/B.
- En app/liga/ranking.py elimina la marca de transicion y el clear_user_app_data("Mario")
  al finalizar la jornada 2; en storage.py elimina ese helper si ya no tiene otros usos.
- En app/liga/rewards.py elimina LEGACY_* y FIRST_ROUND_B_* junto con sus condiciones:
  desde la jornada 1 solo deben aplicarse las tablas definitivas de 10 posiciones.
- En app/liga/eligibility.py elimina PLAYER_JOIN_ROUND de Barto: en esta temporada Barto
  participa y cobra desde la jornada 1.
- Revisa liga, login, entrenadores, copa, juicios, tienda, normativa y este prompt para que
  no queden menciones funcionales a Mario, a 11 jugadores, a la jornada 2 transitoria ni
  al alta tardia de Barto.

El WIPE ya elimina estados y datos generados, asi que no hace falta migrar resultados
historicos: simplifica el codigo para el roster fijo de 10, ejecuta pruebas/compilacion,
comprueba que tenga sentido y funcione, y haz commit y push."""


def _clear_runtime_after_wipe(current_user: str | None) -> None:
    auth_ok = bool(st.session_state.get("auth_ok"))
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    st.session_state["auth_ok"] = auth_ok
    st.session_state["user"] = current_user
    st.session_state["_wipe_done"] = True


def _render_admin_wipe(current_user: str | None) -> None:
    if current_user != "Anto":
        return

    st.markdown("---")
    st.markdown("<div class='bill-chip'>Admin Reset / Wipe</div>", unsafe_allow_html=True)
    st.warning(
        "Esto borra todos los datos de temporada: saves, compras, inventarios, flags, liga, copas, "
        "juicios, ajustes y copias locales. No borra codigo ni assets."
    )
    confirm = st.text_input("Escribe WIPE para confirmar", key="admin_wipe_confirm")
    if st.button(
        "Reset / Wipe",
        key="admin_wipe_button",
        type="primary",
        disabled=confirm != "WIPE",
        use_container_width=True,
    ):
        report = wipe_all_app_data()
        if report.get("ok"):
            _clear_runtime_after_wipe(current_user)
            st.rerun()
        else:
            st.error("Wipe incompleto. Revisa estos errores:")
            for err in report.get("errors") or []:
                st.caption(f"- {err}")

    st.markdown("<div class='bill-chip'>Prompt privado siguiente locke</div>", unsafe_allow_html=True)
    st.code(_PRIVATE_NEXT_LOCKE_PROMPT, language="text")


def page_saves() -> None:
    apply_platinum_ui("Saves")
    st.markdown(SAVES_PAGE_CSS, unsafe_allow_html=True)
    st.markdown("<div class='bill-title'>Gestor de Saves</div>", unsafe_allow_html=True)
    st.markdown("<div class='bill-subtitle'>Terminal de almacenamiento Unova</div>", unsafe_allow_html=True)
    st.markdown("<div class='bill-divider'></div>", unsafe_allow_html=True)

    current_user = st.session_state.get("user")
    st.markdown(
        f"<div class='bill-chip'>Entrenador activo: <b>{current_user or '-'}</b></div>",
        unsafe_allow_html=True,
    )
    if st.session_state.pop("_wipe_done", False):
        st.success("Reset / Wipe completado. La temporada queda limpia para empezar otro juego.")

    bootstrap_latest_save(current_user)

    file = st.file_uploader("Sube un archivo .sav o .dsv", type=["sav", "dsv"])

    col1, col2 = st.columns(2)
    with col1:
        subir = st.button("Subir y marcar como save actual", use_container_width=True)
    with col2:
        _ = st.button("Refrescar", use_container_width=True)

    if file is not None and subir:
        data = file.getvalue()
        rec = save_upload(data, file.name, current_user)
        set_current_save_for_user(current_user, rec["id"])
        write_uploaded_save_copy(current_user, file.name, data)
        clear_save_related_caches()
        refresh_save_snapshot(current_user)
        st.success(f"Guardado por {current_user} y establecido como actual (id={rec['id']}).")

    cur = get_current_save_for_user(current_user)
    st.markdown("<div class='bill-chip'>Save actual</div>", unsafe_allow_html=True)
    if cur:
        id_, fname, oname, sha, up, ts = cur
        st.markdown(current_save_meta_html(cur), unsafe_allow_html=True)
        if up and current_user and current_user == up:
            st.download_button(
                "Descargar save actual",
                data=load_save_bytes(fname),
                file_name=oname or fname,
                key=f"dl_current_{id_}",
            )
        else:
            st.caption("Descarga no disponible: solo quien subio el save puede descargarlo.")
    else:
        st.warning("No hay save actual establecido.")

    with st.expander("Historial (ultimos 20)"):
        for (id_, fname, oname, sha, up, ts) in list_saves_by_user(current_user, limit=20):
            with st.container(border=True):
                st.write(f"**[{id_}]** {oname or fname}")
                st.caption(f"Por {up or '-'} - {datetime.fromtimestamp(ts)} - SHA {sha[:8]}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Establecer como actual", key=f"set_{id_}"):
                        set_current_save_for_user(current_user, id_)
                        clear_save_related_caches()
                        refresh_save_snapshot(current_user)
                        st.success(f"Save actual -> {id_}")
                with c2:
                    if up and current_user and current_user == up:
                        st.download_button(
                            "Descargar",
                            data=load_save_bytes(fname),
                            file_name=oname or fname,
                            key=f"dl_{id_}",
                        )
                    else:
                        st.caption("Solo el autor puede descargar este save.")

    _render_admin_wipe(current_user)
