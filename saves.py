from __future__ import annotations
from datetime import datetime
import html as _html
import streamlit as st

from app.liga.ranking import clear_ranking_caches
from app.interfaz.theme import apply_platinum_ui
from app.tienda.money import clear_money_caches
from storage import (
    save_upload,
    load_save_bytes,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
)
from utils import ensure_user_dir, ts_name


def _clear_save_related_caches() -> None:
    clear_money_caches()
    clear_ranking_caches()
    try:
        import utils as _utils
        cache_fn = getattr(_utils, "_list_user_saves_cached", None)
        if cache_fn is not None:
            cache_fn.clear()
    except Exception:
        pass


def page_saves() -> None:
    apply_platinum_ui("Saves")
    st.markdown(
        """
        <style>
        .bill-title {
          display:inline-block;
          background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);
          border:1px solid var(--bw2-edge-strong);
          border-radius:0;
          padding:10px 12px;
          color:#fff;
          font-family:var(--font-pixel);
          font-size:12px;
          font-weight:700;
          letter-spacing:0.4px;
          text-transform:uppercase;
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        }
        .bill-subtitle {
          margin-top:8px;
          display:inline-block;
          background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          color:var(--bw2-text);
          font-family:var(--font-pixel);
          font-size:10px;
          font-weight:700;
          text-transform:uppercase;
        }
        .bill-divider { height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:12px 0 16px; }
        .bill-chip {
          display:inline-block;
          background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          color:var(--bw2-text);
          font-family:var(--font-pixel);
          font-size:10px;
          font-weight:700;
          text-transform:uppercase;
        }
        .bill-chip b { color:#fff; }
        .bill-save-meta {
          margin-top:8px;
          background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          border:1px solid var(--bw2-edge);
          border-radius:0;
          padding:8px 10px;
          color:var(--bw2-text-soft);
          font-family:var(--font-ui);
          font-size:18px;
          font-weight:400;
          line-height:1.45;
          letter-spacing:0.1px;
        }
        .bill-save-meta b { color:#fff; font-weight:700; font-family:var(--font-pixel); font-size:10px; }
        div[data-testid="stFileUploaderDropzone"] {
          background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%) !important;
          border:1px dashed var(--bw2-edge) !important;
          border-radius:0 !important;
        }
        div[data-testid="stFileUploaderDropzone"] * {
          font-family:var(--font-ui) !important;
          font-weight:400 !important;
          color:var(--bw2-text-soft) !important;
        }
        div[data-testid="stAlert"] {
          border:1px solid var(--bw2-edge) !important;
          border-radius:0 !important;
        }
        div[data-testid="stAlert"] * {
          font-family:var(--font-ui) !important;
          font-weight:400 !important;
        }
        details[data-testid="stExpander"] > summary {
          font-family:var(--font-pixel) !important;
          font-weight:700 !important;
          font-size:10px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='bill-title'>Gestor de Saves</div>", unsafe_allow_html=True)
    st.markdown("<div class='bill-subtitle'>Terminal de almacenamiento Unova</div>", unsafe_allow_html=True)
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
        _clear_save_related_caches()
        st.success(f"Guardado por {current_user} y establecido como actual (id={rec['id']}).")

    cur = get_current_save_for_user(current_user)
    st.markdown("<div class='bill-chip'>Save actual</div>", unsafe_allow_html=True)
    if cur:
        id_, fname, oname, sha, up, ts = cur
        meta = (
            f"<div class='bill-save-meta'><b>ID:</b> {_html.escape(str(id_))} | "
            f"<b>Nombre:</b> {_html.escape(str(oname or fname))} | "
            f"<b>Subido por:</b> {_html.escape(str(up or '-'))} | "
            f"<b>Fecha:</b> {_html.escape(str(datetime.fromtimestamp(ts)))} | "
            f"<b>SHA:</b> {_html.escape(str(sha[:8]))}</div>"
        )
        st.markdown(meta, unsafe_allow_html=True)
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
                        _clear_save_related_caches()
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
