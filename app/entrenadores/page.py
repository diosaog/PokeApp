from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from app.entrenadores.bridge import try_auto_load_bridge
from app.entrenadores.cache import cached_box_meta_quick, cached_has_pc_data, cached_team, preload_entrenadores_cache
from app.entrenadores.detail import pokemon_detail_panel
from app.entrenadores.inventory import _purchases_inventory_ui, _inventory_cached, _render_purchase_cards, _category_for_item
from app.entrenadores.pokepaste import ensure_pokepaste_state
from app.entrenadores.state import ensure_local_save_for
from app.entrenadores.summary import trainer_summary_with_portrait_ui
from app.entrenadores.trainer_flags import (
    format_trainer_with_flags,
    is_trainer_retired,
    is_trainer_robbed,
    set_trainer_retired,
    sync_trainer_robbed_flags_from_history,
)
from app.entrenadores.boxes import boxes_grid_ui
from app.discord_notify import notify_team_locked_async
from app.ui.team_grid import team_grid_ui
from app.interfaz.theme import apply_platinum_ui
from app.liga.context import current_jornada
from app.liga.ranking import clear_ranking_caches
from app.tienda.money import clear_money_caches
from conex_pkhex import PKHeXRuntime, extract_team, get_bridge_path, open_sav_cached
from storage import (
    get_current_save_for_user,
    get_team_lock,
    list_saves_by_user,
    settings_get,
    upsert_team_lock,
)
from utils import DEFAULT_DLL_HINT, USERS, active_users, list_user_saves


INVENTORY_TABS_CSS = """
<style>
div[data-testid="stTabs"] div[data-baseweb="tab-list"],
div[data-testid="stTabs"] [role="tablist"] {
  gap: 8px !important;
  flex-wrap: wrap !important;
  align-items: stretch !important;
}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:first-of-type,
div[data-testid="stTabs"] [role="tablist"] [role="tab"]:first-of-type {
  flex: 0 0 176px !important;
  width: 176px !important;
  min-width: 176px !important;
  justify-content: center !important;
  padding-left: 14px !important;
  padding-right: 14px !important;
  white-space: nowrap !important;
}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:first-of-type *,
div[data-testid="stTabs"] [role="tablist"] [role="tab"]:first-of-type * {
  width: 100%;
  text-align: center;
  white-space: nowrap !important;
}
</style>
"""


def _notify_trainer_retired_async(trainer: str, by_user: str | None = None) -> None:
    try:
        from app import discord_notify

        existing = getattr(discord_notify, "notify_trainer_retired_async", None)
        if callable(existing):
            existing(trainer=trainer, by_user=by_user)
            return

        import threading

        def _send() -> None:
            try:
                fields = []
                if by_user:
                    fields.append(
                        {
                            "name": "Registrado por",
                            "value": str(by_user),
                            "inline": True,
                        }
                    )
                discord_notify._post_webhook(
                    {
                        "embeds": [
                            discord_notify._embed(
                                title="Entrenador retirado",
                                description=(
                                    f"{trainer} se ha retirado de la liga. "
                                    "Sus resultados anteriores se conservan, pero deja de contar "
                                    "para jornadas, puntos, monedas y sistemas activos."
                                ),
                                color=0x95A5A6,
                                fields=fields,
                            )
                        ]
                    }
                )
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()
    except Exception:
        pass


def _save_meta_for_lock(user: str, save_path: Path | None) -> tuple[int | None, str | None]:
    if not user or not save_path:
        return None, None
    try:
        current = get_current_save_for_user(user)
        if current and str(current[1]) == save_path.name:
            return int(current[0]), str(current[3] or "")
    except Exception:
        pass
    try:
        for row in list_saves_by_user(user, limit=20):
            if str(row[1]) == save_path.name:
                return int(row[0]), str(row[3] or "")
    except Exception:
        pass
    return None, None


def _fmt_lock_time(ts: int) -> str:
    if not ts:
        return "-"
    try:
        from datetime import datetime

        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def _render_team_lock_controls(
    *,
    team: list[dict],
    current_user: str,
    save_path: Path | None,
) -> None:
    jornada = current_jornada()
    lock = get_team_lock(jornada, current_user)
    if lock:
        status = "Fijado tarde" if lock.get("is_late") else "Fijado"
        st.caption(
            f"Equipo fijado para Jornada {jornada}: {status} | "
            f"{_fmt_lock_time(int(lock.get('locked_at') or 0))}"
        )
    else:
        st.caption(f"Equipo fijado para Jornada {jornada}: Sin fijar")

    disabled = len(team) != 6
    if disabled:
        st.warning("Necesitas 6 Pokemon en el equipo para fijarlo para combates.")

    if st.button(
        f"Fijar Equipo Para la Jornada {jornada}",
        disabled=disabled,
        use_container_width=True,
        key=f"lock_team_{current_user}_{jornada}",
    ):
        save_id, save_sha = _save_meta_for_lock(current_user, save_path)
        is_late = bool(st.session_state.get("league_active"))
        saved = upsert_team_lock(
            jornada=jornada,
            user=current_user,
            team=list(team)[:6],
            save_id=save_id,
            save_sha256=save_sha,
            is_late=is_late,
        )
        if not saved:
            st.error("No se pudo fijar el equipo. Revisa Supabase o vuelve a intentarlo.")
            return
        notify_team_locked_async(user=current_user, jornada=jornada, is_late=is_late)
        st.success(
            f"Equipo fijado para Jornada {jornada}"
            + (" (tarde)." if is_late else ".")
        )
        st.rerun()


def page_entrenadores_setup() -> None:
    is_own_profile = st.session_state.get("trainer_selected") == st.session_state.get("user")
    if not is_own_profile:
        return
    with st.expander(
        "Configurar lector de saves DS (Bridge)",
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
    current_user_retired = is_trainer_retired(current_user)
    ensure_pokepaste_state()

    ensure_local_save_for(trainer or "")

    if is_trainer_retired(trainer):
        st.warning(
            "Este entrenador esta retirado. Se mantiene visible, pero no participa en sistemas activos."
        )
    elif is_trainer_robbed(trainer):
        st.info("Este entrenador ya ha sido robado en la ronda actual.")

    saves = list_user_saves(trainer) if trainer else []
    active_path = saves[0] if saves else None
    st.info(
        f"Guardado detectado para {trainer or '-'}: {Path(active_path).name if active_path else '(sin guardados)'}"
    )

    if not st.session_state.get("pkhex_loaded", False):
        if is_own_profile:
            st.warning("Configura el lector (bridge) para poder leer el save.")
        else:
            st.info("El guardado no esta disponible en este momento.")
        return

    if not active_path:
        if is_own_profile:
            st.warning("Sube un .sav o .dsv en la pestana Saves.")
        else:
            st.info("Este entrenador no tiene guardados.")
        return

    try:
        save_path = Path(active_path)
        if not save_path.exists():
            st.error("El archivo del entrenador no existe.")
            return
        st.session_state.active_sav_path = str(save_path)
        mtime = save_path.stat().st_mtime
        sav_json = open_sav_cached(save_path)
    except Exception as e:
        st.error(f"No se pudo abrir el guardado: {e}")
        try:
            st.caption(f"Ruta del bridge actual: {get_bridge_path() or ''}")
        except Exception:
            pass
        return

    try:
        box_count, box_names = cached_box_meta_quick(str(save_path), mtime)
    except Exception:
        box_count, box_names = 0, []
    try:
        pc_ok = cached_has_pc_data(str(save_path), mtime)
    except Exception:
        pc_ok = False
    preload_entrenadores_cache(str(save_path), mtime, box_count)

    st.markdown("---")
    col_stats, col_inv = st.columns([1.35, 1.1], gap="large")
    with col_stats:
        trainer_summary_with_portrait_ui(
            sav_json,
            box_count,
            is_own_profile=is_own_profile,
            save_path=str(save_path),
        )
    with col_inv:
        st.markdown(
            "<div style='display:inline-block; background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);"
            " border:1px solid var(--bw2-edge-strong); border-radius:0; padding:7px 10px; color:#ffffff;"
            " font-family:var(--font-pixel); font-size:10px; text-transform:uppercase; letter-spacing:0.04em;"
            " clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);'>Inventario</div>",
            unsafe_allow_html=True,
        )
        st.markdown(INVENTORY_TABS_CSS, unsafe_allow_html=True)
        tab_shop, tab_como = st.tabs(["Compras (tienda)", "Comodines"])
        with tab_shop:
            _purchases_inventory_ui(trainer or "", allow_use=False)
        with tab_como:
            inv = _inventory_cached(trainer or "")
            comos = [r for r in inv if _category_for_item(r[1]) == "Comodines"] if inv else []
            if not is_own_profile:
                st.caption("Solo el propietario puede usar sus comodines.")
            elif current_user_retired:
                st.caption("Los entrenadores retirados no pueden usar comodines.")
            _render_purchase_cards(
                comos,
                "Comodines",
                key_prefix="comos",
                allow_use=is_own_profile and not current_user_retired,
            )

        ctx = st.session_state.get("redeem_ctx")
        if ctx and not current_user_retired:
            try:
                from tienda2 import _render_redeem_flow  # wrapper keeps API
                _render_redeem_flow(ctx, current_user)
            except Exception:
                st.error("No se pudo cargar el flujo de uso de comodines. Ve a la pestana Tienda.")
        elif ctx and current_user_retired:
            st.session_state.pop("redeem_ctx", None)
            st.warning("Los entrenadores retirados no pueden usar comodines.")

    st.markdown("---")
    try:
        active_spath = str(save_path) if save_path else None
        if active_spath:
            team = cached_team(active_spath, mtime)
        else:
            team = extract_team(sav_json) or []
    except Exception:
        team = []
    if is_own_profile and not current_user_retired:
        _render_team_lock_controls(
            team=list(team or [])[:6],
            current_user=str(current_user or ""),
            save_path=Path(save_path) if save_path else None,
        )
    elif is_own_profile and current_user_retired:
        st.caption("Entrenador retirado: no puede fijar equipo para jornadas.")
    team_grid_ui(team)
    detail_slot = st.empty()
    boxes_grid_ui(sav_json, box_count, box_names, save_path=str(save_path), pc_ok=pc_ok, mtime=mtime)
    with detail_slot:
        pokemon_detail_panel()


def _render_retirement_admin() -> None:
    current_user = str(st.session_state.get("user") or "")
    if current_user.strip().lower() != "anto":
        return

    st.markdown("---")
    with st.expander("Gestion de abandonos", expanded=False):
        st.caption("Solo Anto puede marcar un abandono. Es permanente desde la app.")
        league_active = False
        try:
            raw_state = settings_get("league_state")
            if raw_state:
                league_active = bool(json.loads(raw_state).get("active"))
        except Exception:
            league_active = bool(st.session_state.get("league_active"))
        if league_active:
            st.warning(
                "Hay una jornada en edicion. Cierra esa jornada antes de marcar un abandono."
            )
        candidates = [user for user in USERS.keys() if not is_trainer_retired(user)]
        if not candidates:
            st.caption("No quedan entrenadores disponibles para retirar.")
            return
        target = st.selectbox(
            "Entrenador que abandona",
            candidates,
            format_func=format_trainer_with_flags,
            key="retirement_target",
        )
        confirm = st.text_input(
            "Escribe RETIRAR para confirmar",
            key="retirement_confirm",
        )
        if st.button(
            "Marcar abandono",
            disabled=(confirm != "RETIRAR") or league_active,
            use_container_width=True,
            key="retirement_submit",
        ):
            try:
                set_trainer_retired(str(target), by_user=current_user)
                clear_money_caches()
                clear_ranking_caches()
                _notify_trainer_retired_async(str(target), by_user=current_user)
                st.success(f"{target} marcado como retirado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo marcar el abandono: {e}")


def page_entrenadores() -> None:
    apply_platinum_ui("Entrenadores")
    st.title("Entrenadores")
    st.caption("Se alimenta del ultimo .sav o .dsv del entrenador seleccionado.")

    try:
        sync_trainer_robbed_flags_from_history(list(active_users().keys()))
    except Exception:
        pass

    users = list(USERS.keys())
    try:
        active = st.session_state.get("user")
        cur = st.session_state.get("trainer_selected")
        last_login_user = st.session_state.get("_trainer_login_user")
        if active in users and last_login_user != active:
            st.session_state.trainer_selected = active
            st.session_state["_trainer_login_user"] = active
        elif cur not in users:
            st.session_state.trainer_selected = active if active in users else (users[0] if users else None)
    except Exception:
        pass
    prev = st.session_state.get("_trainer_selected_last")
    sel = st.selectbox(
        "Elige un entrenador",
        users,
        key="trainer_selected",
        format_func=format_trainer_with_flags,
    )
    if prev is None:
        st.session_state["_trainer_selected_last"] = sel
    elif sel != prev:
        st.session_state["_trainer_selected_last"] = sel
        st.session_state.pop("selected_pokemon", None)

    try_auto_load_bridge()

    page_entrenadores_view()
    _render_retirement_admin()
