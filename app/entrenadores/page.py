from __future__ import annotations

from pathlib import Path
import streamlit as st

from app.entrenadores.bridge import try_auto_load_bridge
from app.entrenadores.cache import cached_team
from app.entrenadores.detail import pokemon_detail_panel
from app.entrenadores.inventory import _purchases_inventory_ui, _inventory_cached, _render_purchase_cards, _category_for_item
from app.entrenadores.pokepaste import ensure_pokepaste_state
from app.entrenadores.state import ensure_local_save_for
from app.entrenadores.summary import trainer_summary_with_portrait_ui
from app.entrenadores.boxes import boxes_grid_ui
from app.ui.team_grid import team_grid_ui
from conex_pkhex import PKHeXRuntime, extract_team, get_box_meta_quick, get_bridge_path, open_sav_cached
from utils import USERS, DEFAULT_DLL_HINT, list_user_saves


def page_entrenadores_setup() -> None:
    is_own_profile = st.session_state.get("trainer_selected") == st.session_state.get("user")
    if not is_own_profile:
        return
    with st.expander(
        "Configurar lector de .sav (Bridge)",
        expanded=not st.session_state.get("pkhex_loaded", False),
    ):
        bridge_hint = st.session_state.get("pkhex_dll_path") or DEFAULT_DLL_HINT
        exe_in = st.text_input("Ruta a PKHeXBridge.exe (o carpeta)", value=bridge_hint)
        st.session_state.pkhex_mode = "auto"
        if st.button("Cargar lector", type="primary"):
            try:
                PKHeXRuntime.load(exe_in)
                st.session_state.pkhex_loaded = True
                st.session_state.pkhex_dll_path = exe_in
                st.success("Lector cargado correctamente.")
            except Exception as e:
                st.session_state.pkhex_loaded = False
                st.error(f"No se pudo cargar el lector: {e}")


def page_entrenadores_view() -> None:
    trainer = st.session_state.get("trainer_selected")
    current_user = st.session_state.get("user")
    is_own_profile = trainer == current_user
    ensure_pokepaste_state()

    ensure_local_save_for(trainer or "")

    saves = list_user_saves(trainer) if trainer else []
    active_path = saves[0] if saves else None
    st.info(
        f"Guardado detectado para {trainer or '-'}: {Path(active_path).name if active_path else '(sin guardados)'}"
    )

    if not st.session_state.get("pkhex_loaded", False):
        if is_own_profile:
            st.warning("Configura el lector (bridge) para poder leer el .sav.")
        else:
            st.info("El guardado no esta disponible en este momento.")
        return

    if not active_path:
        if is_own_profile:
            st.warning("Sube un .sav en la pestana Saves.")
        else:
            st.info("Este entrenador no tiene guardados.")
        return

    try:
        save_path = Path(active_path)
        if not save_path.exists():
            st.error("El archivo .sav del entrenador no existe.")
            return
        sav_json = open_sav_cached(save_path)
    except Exception as e:
        st.error(f"No se pudo abrir el guardado: {e}")
        try:
            st.caption(f"Ruta del bridge actual: {get_bridge_path() or ''}")
        except Exception:
            pass
        return

    try:
        box_count, box_names = get_box_meta_quick(sav_json, save_path=str(save_path))
    except Exception:
        box_count, box_names = 0, []

    trainer_summary_with_portrait_ui(sav_json, box_count, is_own_profile=is_own_profile)

    st.markdown("---")
    st.subheader("Inventario")
    tab_shop, tab_como = st.tabs(["Compras (tienda)", "Comodines"])
    with tab_shop:
        _purchases_inventory_ui(trainer or "", allow_use=False)
    with tab_como:
        inv = _inventory_cached(trainer or "")
        comos = [r for r in inv if _category_for_item(r[1]) == "Comodines"] if inv else []
        _render_purchase_cards(comos, "Comodines", key_prefix="comos", allow_use=True)

    ctx = st.session_state.get("redeem_ctx")
    if ctx:
        try:
            from tienda2 import _render_redeem_flow  # wrapper keeps API
            _render_redeem_flow(ctx, current_user)
        except Exception:
            st.error("No se pudo cargar el flujo de uso de comodines. Ve a la pestana Tienda.")

    st.markdown("---")
    try:
        active_spath = str(save_path) if save_path else None
        if active_spath:
            import os
            mtime = os.path.getmtime(active_spath)
            team = cached_team(active_spath, mtime)
        else:
            team = extract_team(sav_json) or []
    except Exception:
        team = []
    team_grid_ui(team)

    pokemon_detail_panel()

    boxes_grid_ui(sav_json, box_count, box_names, save_path=str(save_path))


def page_entrenadores() -> None:
    st.title("Entrenadores")
    st.caption("Se alimenta del ultimo .sav del entrenador seleccionado.")

    users = list(USERS.keys())
    default_idx = 0
    try:
        cur = st.session_state.get("trainer_selected")
        active = st.session_state.get("user")
        if cur in users:
            default_idx = users.index(cur)
        elif active in users:
            default_idx = users.index(active)
            st.session_state.trainer_selected = active
    except Exception:
        pass
    prev_trainer = st.session_state.get("trainer_selected")
    trainer = st.selectbox("Elige un entrenador", users, index=default_idx)
    st.session_state.trainer_selected = trainer
    if prev_trainer and trainer != prev_trainer:
        st.session_state.pop("selected_pokemon", None)

    try_auto_load_bridge()

    page_entrenadores_view()
