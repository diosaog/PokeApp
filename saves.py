from __future__ import annotations
from datetime import datetime
import streamlit as st

from storage import (
    save_upload,
    load_save_bytes,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
)
from utils import ensure_user_dir, ts_name


def page_saves() -> None:
    st.header("PC de Bill 💾")

    current_user = st.session_state.get("user")
    st.caption(f"Este save se registrara a: {current_user}")

    file = st.file_uploader("Sube un archivo .sav", type=["sav"])

    col1, col2 = st.columns(2)
    with col1:
        subir = st.button("Subir y marcar como save actual", use_container_width=True)
    with col2:
        _ = st.button("Refrescar", use_container_width=True)

    if file is not None and subir:
        data = file.getvalue()
        rec = save_upload(data, file.name, current_user)
        set_current_save_for_user(current_user, rec["id"])  # marca como actual
        # Copia adicional al directorio de saves del usuario (para Entrenadores)
        try:
            folder = ensure_user_dir(current_user)
            dest = folder / ts_name(current_user)
            with open(dest, "wb") as f:
                f.write(data)
        except Exception:
            pass
        st.success(f"Guardado por {current_user} y establecido como actual (id={rec['id']}).")

    cur = get_current_save_for_user(current_user)
    st.subheader("Save actual")
    if cur:
        id_, fname, oname, sha, up, ts = cur
        st.info(
            f"ID: {id_} | Nombre: {oname or fname} | Subido por: {up or '-'} | Fecha: {datetime.fromtimestamp(ts)} | SHA: {sha[:8]}"
        )
        if up and current_user and current_user == up:
            st.download_button(
                "Descargar save actual",
                data=load_save_bytes(fname),
                file_name=oname or fname,
                key=f"dl_current_{id_}"
            )
        else:
            st.caption("Descarga no disponible: solo quien subio el save puede descargarlo.")
    else:
        st.warning("No hay save actual establecido.")

    with st.expander("Historial (ultimos 20)"):
        for (id_, fname, oname, sha, up, ts) in list_saves_by_user(current_user, limit=20):
            with st.container(border=True):
                st.write(f"**[{id_}]** {oname or fname}")
                st.caption(f"Por {up or '-'} • {datetime.fromtimestamp(ts)} • SHA {sha[:8]}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Establecer como actual", key=f"set_{id_}"):
                        set_current_save_for_user(current_user, id_)
                        st.success(f"Save actual -> {id_}")
                with c2:
                    if up and current_user and current_user == up:
                        st.download_button(
                            "Descargar",
                            data=load_save_bytes(fname),
                            file_name=oname or fname,
                            key=f"dl_{id_}"
                        )
                    else:
                        st.caption("Solo el autor puede descargar este save.")
