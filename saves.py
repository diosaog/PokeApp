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
    save_upload,
    load_save_bytes,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
)


def _render_header(current_user: str | None, retired: bool) -> None:
    mode = "Modo consulta" if retired else "Gestion activa"
    user_label = escape(str(current_user or "-"))
    st.markdown(
        (
            "<div class='saves-hero'>"
            "<div>"
            f"<div class='saves-kicker'>{mode} - {user_label}</div>"
            "<div class='saves-title'>Saves</div>"
            "</div>"
            "<div class='saves-hero-side'>Archivo actual e historial</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_upload_panel(current_user: str | None, *, disabled: bool) -> None:
    st.markdown("<div class='saves-section-title'>Subir nuevo save</div>", unsafe_allow_html=True)
    file = st.file_uploader(
        "Archivo .sav o .dsv",
        type=["sav", "dsv"],
        disabled=disabled,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        subir = st.button(
            "Subir y marcar actual",
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
        st.markdown(
            (
                "<div class='saves-empty-state'>"
                "<strong>Sin save actual</strong>"
                "<span>Sube un .sav o .dsv para marcarlo como archivo activo.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown(current_save_meta_html(current), unsafe_allow_html=True)
    owner = save_owner_label(current)
    if owner and current_user and current_user == owner:
        _render_download(current, label="Descargar save actual", key=f"dl_current_{save_row_id(current)}")
    else:
        st.caption("Solo puede descargarlo quien lo subio.")


def _render_history(current_user: str | None, history: list[tuple], current: tuple | None, *, disabled: bool) -> None:
    current_id = save_row_id(current)
    st.markdown("<div class='saves-section-title'>Historial</div>", unsafe_allow_html=True)
    if not history:
        st.markdown(
            (
                "<div class='saves-empty-state'>"
                "<strong>Sin historial</strong>"
                "<span>Aun no hay archivos subidos para este entrenador.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    prepared_key = "saves_download_ready_id"
    with st.expander("Ultimos saves", expanded=True):
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
                    st.caption("Solo el autor puede descargarlo.")


def page_saves() -> None:
    apply_platinum_ui("Saves")
    st.markdown(SAVES_PAGE_CSS, unsafe_allow_html=True)

    current_user = st.session_state.get("user")

    bootstrap_latest_save(current_user)
    user_retired = is_trainer_retired(current_user)
    _render_header(current_user, user_retired)
    if user_retired:
        st.warning("Entrenador retirado.")

    cur = get_current_save_for_user(current_user)
    history = list_saves_by_user(current_user, limit=20) if current_user else []
    st.markdown(saves_summary_html(current_user, cur, history, retired=user_retired), unsafe_allow_html=True)

    _render_current_save(current_user, cur)
    _render_upload_panel(current_user, disabled=user_retired or not bool(current_user))
    st.markdown("<div class='saves-divider'></div>", unsafe_allow_html=True)
    _render_history(current_user, history, cur, disabled=user_retired or not bool(current_user))
