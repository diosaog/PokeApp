from __future__ import annotations
from datetime import datetime
import streamlit as st

from app.interfaz.theme import apply_platinum_ui
from storage import (
    save_upload,
    load_save_bytes,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
)
from utils import ensure_user_dir, ts_name


def page_saves() -> None:
    apply_platinum_ui("Saves")
    st.markdown(
        """
        <style>
        .bill-title {
          display:inline-block;
          background:linear-gradient(180deg,#f2cc62 0%,#e4b84a 100%);
          border:2px solid #c28f27;
          border-radius:8px;
          padding:10px 12px;
          color:#222;
          font-family:"Press Start 2P", monospace;
          font-size:16px;
          font-weight:900;
          letter-spacing:0.4px;
          text-shadow:0 0 1px rgba(0,0,0,0.25);
        }
        .bill-subtitle {
          margin-top:8px;
          display:inline-block;
          background:#10263f;
          border:2px solid #2a75bb;
          border-radius:8px;
          padding:8px 10px;
          color:#e8f2ff;
          font-family:"Press Start 2P", monospace;
          font-size:11px;
          font-weight:900;
          text-transform:uppercase;
        }
        .bill-divider { height:2px; background:#2a75bb; margin:12px 0 16px; }
        .bill-chip {
          display:inline-block;
          background:#f7f6ef;
          border:2px solid #9a9680;
          border-radius:6px;
          padding:8px 10px;
          color:#2b2b2b;
          font-family:"Press Start 2P", monospace;
          font-size:11px;
          font-weight:900;
        }
        .bill-chip b { color:#10263f; }
        div[data-testid="stFileUploaderDropzone"] {
          background:#0f2033 !important;
          border:2px dashed #2a75bb !important;
          border-radius:10px !important;
        }
        div[data-testid="stFileUploaderDropzone"] * {
          font-family:"Press Start 2P", monospace !important;
          font-weight:900 !important;
          color:#dcecff !important;
        }
        div[data-testid="stAlert"] {
          border:2px solid #2a75bb !important;
          border-radius:8px !important;
        }
        div[data-testid="stAlert"] * {
          font-family:"Press Start 2P", monospace !important;
          font-weight:900 !important;
        }
        details[data-testid="stExpander"] > summary {
          font-family:"Press Start 2P", monospace !important;
          font-weight:900 !important;
          font-size:11px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='bill-title'>PC de Bill</div>", unsafe_allow_html=True)
    st.markdown("<div class='bill-subtitle'>Sistema de almacenamiento Pokemon</div>", unsafe_allow_html=True)
    st.markdown("<div class='bill-divider'></div>", unsafe_allow_html=True)

    current_user = st.session_state.get("user")
    st.markdown(
        f"<div class='bill-chip'>Entrenador activo: <b>{current_user or '-'}</b></div>",
        unsafe_allow_html=True,
    )

    def _bootstrap_latest_save():
        """If there is no current save, use the latest from storage and cache locally."""
        if not current_user:
            return
        cur = get_current_save_for_user(current_user)
        if cur:
            try:
                folder = ensure_user_dir(current_user)
                dest = folder / cur[1]
                if not dest.exists():
                    data = load_save_bytes(cur[1])
                    if data:
                        dest.write_bytes(data)
            except Exception:
                pass
            return
        try:
            lst = list_saves_by_user(current_user, limit=1)
            if lst:
                last_id, fname, oname, sha, up, ts = lst[0]
                set_current_save_for_user(current_user, last_id)
                try:
                    folder = ensure_user_dir(current_user)
                    dest = folder / fname
                    data = load_save_bytes(fname)
                    if data:
                        dest.write_bytes(data)
                except Exception:
                    pass
        except Exception:
            pass

    _bootstrap_latest_save()

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
        try:
            from pathlib import Path
            folder = ensure_user_dir(current_user)
            ext = Path(file.name).suffix or ".sav"
            dest = folder / ts_name(current_user, ext=ext)
            with open(dest, "wb") as f:
                f.write(data)
        except Exception:
            pass
        st.success(f"Guardado por {current_user} y establecido como actual (id={rec['id']}).")

    cur = get_current_save_for_user(current_user)
    st.markdown("<div class='bill-chip'>Save actual</div>", unsafe_allow_html=True)
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
