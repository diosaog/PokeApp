from __future__ import annotations
from html import escape
import streamlit as st

from app.entrenadores.trainer_flags import is_trainer_retired
from app.interfaz.theme import apply_platinum_ui
from app.saves_support import (
    SAVES_PAGE_CSS,
    bootstrap_latest_save,
    clear_save_related_caches,
    current_save_meta_html,
    refresh_save_snapshot,
    save_card_html,
    save_file_label,
    save_row_filename,
    save_row_id,
    save_owner_label,
    saves_summary_html,
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

_PRIVATE_NEXT_LOCKE_PROMPT = """PokeApp 2.0 - notas privadas de temporada

La temporada actual nace limpia con 10 jugadores activos, dos divisiones de 5 y reglas
definitivas desde la jornada 1.

MONEDAS: 1=15, 2=14, 3=12, 4=11, 5=10, 6=11, 7=9, 8=8, 9=6, 10=4.
PUNTOS: 1=9, 2=8, 3=7, 4=6, 5=5, 6=5, 7=4, 8=3, 9=2, 10=1.

Siguiente objetivo grande:
- Crear sistema de temporadas configurable solo para Anto.
- Permitir configurar jugadores, numero de jornadas, divisiones, ascensos, descensos,
  puntos y monedas.
- Aplicar cambios de configuracion solo desde el momento en que se guardan.
- Enviar aviso de Aaron cuando se publique o modifique la configuracion de temporada.
- Rework visual 2.0: menu principal, login premium ligero, entrenadores, tienda, copa,
  juicios simplificados, Hall of Fame y panel admin.
- Optimizar al final: snapshots, caches, menos recalculos y consultas mas concretas."""


def _render_header(current_user: str | None, retired: bool) -> None:
    mode = "Modo consulta" if retired else "Gestion activa"
    user_label = escape(str(current_user or "-"))
    st.markdown(
        (
            "<div class='saves-hero'>"
            f"<div class='saves-kicker'>{mode} - {user_label}</div>"
            "<div class='saves-title'>Gestor de Saves</div>"
            "<div class='saves-subtitle'>Subidas, save actual, historial personal y reset privado de temporada.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


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
    st.markdown("<div class='saves-section-title'>Admin Reset / Wipe</div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div class='saves-admin-panel'>"
            "<div class='saves-admin-title'>Zona privada de Anto</div>"
            "<div class='saves-admin-body'>"
            "Borra datos de temporada y deja la app lista para empezar otro juego. "
            "No toca codigo ni assets del proyecto."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
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

    st.markdown("<div class='saves-section-title'>Notas privadas de temporada</div>", unsafe_allow_html=True)
    st.code(_PRIVATE_NEXT_LOCKE_PROMPT, language="text")


def _render_upload_panel(current_user: str | None, *, disabled: bool) -> None:
    st.markdown("<div class='saves-section-title'>Subir save</div>", unsafe_allow_html=True)
    file = st.file_uploader(
        "Archivo .sav o .dsv",
        type=["sav", "dsv"],
        disabled=disabled,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        subir = st.button(
            "Subir y marcar como save actual",
            use_container_width=True,
            disabled=disabled or file is None,
        )
    with col2:
        refrescar = st.button("Refrescar", use_container_width=True)

    if refrescar:
        clear_save_related_caches()
        st.rerun()

    if file is None or not subir:
        return

    data = file.getvalue()
    rec = save_upload(data, file.name, current_user)
    save_id = rec.get("id")
    if save_id is None:
        st.error("No se pudo registrar la subida. Revisa la conexion con Supabase.")
        return

    set_current_save_for_user(current_user, save_id)
    write_uploaded_save_copy(current_user, file.name, data)
    clear_save_related_caches()
    refresh_save_snapshot(current_user)
    st.success(f"{file.name} guardado y marcado como save actual.")
    st.rerun()


def _render_download(row: tuple, *, label: str, key: str) -> None:
    filename = save_row_filename(row)
    data = load_save_bytes(filename) if filename else b""
    st.download_button(
        label,
        data=data,
        file_name=save_file_label(row),
        key=key,
        disabled=not bool(data),
        use_container_width=True,
    )


def _render_current_save(current_user: str | None, current: tuple | None) -> None:
    st.markdown("<div class='saves-section-title'>Save actual</div>", unsafe_allow_html=True)
    if not current:
        st.warning("No hay save actual establecido.")
        return

    st.markdown(current_save_meta_html(current), unsafe_allow_html=True)
    owner = save_owner_label(current)
    if owner and current_user and current_user == owner:
        _render_download(current, label="Descargar save actual", key=f"dl_current_{save_row_id(current)}")
    else:
        st.caption("Descarga no disponible: solo quien subio el save puede descargarlo.")


def _render_history(current_user: str | None, history: list[tuple], current: tuple | None, *, disabled: bool) -> None:
    current_id = save_row_id(current)
    st.markdown("<div class='saves-section-title'>Historial personal</div>", unsafe_allow_html=True)
    if not history:
        st.info("Todavia no hay saves subidos por este entrenador.")
        return

    prepared_key = "saves_download_ready_id"
    with st.expander("Ultimos 20 saves", expanded=True):
        for idx, row in enumerate(history):
            row_id = save_row_id(row)
            row_key = row_id if row_id is not None else f"row_{idx}"
            st.markdown(save_card_html(row, current_id=current_id), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                is_current = row_id is not None and current_id == row_id
                if st.button(
                    "Save actual" if is_current else "Establecer como actual",
                    key=f"set_{row_key}",
                    disabled=disabled or is_current or row_id is None,
                    use_container_width=True,
                ):
                    set_current_save_for_user(current_user, row_id)
                    clear_save_related_caches()
                    refresh_save_snapshot(current_user)
                    st.success(f"Save actual actualizado: {save_file_label(row)}")
                    st.rerun()
            with c2:
                if save_owner_label(row) == current_user:
                    if st.button("Preparar descarga", key=f"prep_dl_{row_key}", use_container_width=True):
                        st.session_state[prepared_key] = row_id
                    if st.session_state.get(prepared_key) == row_id:
                        _render_download(row, label="Descargar", key=f"dl_{row_key}")
                else:
                    st.caption("Solo el autor puede descargar este save.")


def page_saves() -> None:
    apply_platinum_ui("Saves")
    st.markdown(SAVES_PAGE_CSS, unsafe_allow_html=True)

    current_user = st.session_state.get("user")
    if st.session_state.pop("_wipe_done", False):
        st.success("Reset / Wipe completado. La temporada queda limpia para empezar otro juego.")

    bootstrap_latest_save(current_user)
    user_retired = is_trainer_retired(current_user)
    _render_header(current_user, user_retired)
    if user_retired:
        st.warning("Entrenador retirado: puedes consultar saves, pero no subir ni cambiar el actual.")

    cur = get_current_save_for_user(current_user)
    history = list_saves_by_user(current_user, limit=20) if current_user else []
    st.markdown(saves_summary_html(current_user, cur, history, retired=user_retired), unsafe_allow_html=True)

    _render_upload_panel(current_user, disabled=user_retired or not bool(current_user))
    st.markdown("<div class='saves-divider'></div>", unsafe_allow_html=True)
    _render_current_save(current_user, cur)
    _render_history(current_user, history, cur, disabled=user_retired or not bool(current_user))

    _render_admin_wipe(current_user)
