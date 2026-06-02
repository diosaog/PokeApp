from __future__ import annotations

import json
import time
from typing import List
import streamlit as st

from app.entrenadores.constants import DEAD_BOX_INDEX, DEAD_BOX_LABEL, TOTAL_BOXES
from app.tienda.common import _eq_item
from storage import (
    add_purchase,
    add_redemption,
    get_purchase,
    get_flags_by_fingerprints,
    set_purchase_status,
    upsert_pokemon_flags,
)
from conex_pkhex import extract_box, extract_team, open_sav_cached
from pkmmeta import pokemon_fingerprint, pokemon_fingerprint_stable
from utils import active_users, list_user_saves


def _fingerprints_for_mon(m: dict) -> tuple[str | None, str | None]:
    legacy = None
    stable = None
    try:
        legacy = pokemon_fingerprint(m)
    except Exception:
        legacy = None
    try:
        stable = pokemon_fingerprint_stable(m)
    except Exception:
        stable = None
    return legacy, stable


def _load_flags_for_fps(legacy: str | None, stable: str | None, *, owner: str | None) -> tuple[dict, str | None]:
    fps = [fp for fp in (legacy, stable) if isinstance(fp, str)]
    if not fps:
        return {}, None
    if owner:
        flags_map = get_flags_by_fingerprints(fps, owner=owner)
    else:
        flags_map = get_flags_by_fingerprints(fps)
    flags: dict = {}
    for fp in (legacy, stable):
        meta = flags_map.get(fp)
        if not meta:
            continue
        fj = meta.get("flags_json")
        if isinstance(fj, str) and fj.strip():
            try:
                obj = json.loads(fj)
                if isinstance(obj, dict):
                    flags.update(obj)
            except Exception:
                pass
    fp_key = stable or legacy
    return flags, fp_key


def _redeem_purchase_belongs_to_user(pid, item: str, current_user: str) -> bool:
    try:
        purchase_id = int(pid)
    except Exception:
        return False
    if not current_user or current_user == "-":
        return False
    try:
        purchase = get_purchase(purchase_id)
    except Exception:
        return False
    if not purchase:
        return False
    try:
        _row_id, owner, row_item, _price, _created_at, status, _redeemed_at = purchase
    except Exception:
        return False
    if str(owner or "").strip() != str(current_user or "").strip():
        return False
    if str(status or "").strip().lower() == "used":
        return False
    return _eq_item(str(row_item), str(item))


def render_redeem_flow(ctx: dict, current_user: str) -> None:
    item = ctx.get("item")
    pid = ctx.get("pid")
    _ = int(ctx.get("step") or 1)
    st.markdown("---")
    st.subheader(f"Usar: {item} (#{pid})")

    if not _redeem_purchase_belongs_to_user(pid, str(item or ""), current_user):
        st.error("No puedes usar comodines que no pertenezcan a tu usuario.")
        st.session_state.pop("redeem_ctx", None)
        return

    if _eq_item(item, "Robar Pokemon"):
        players = [u for u in active_users().keys() if u != current_user]
        target = st.selectbox("Jugador objetivo", players, key="rob_target")
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(TOTAL_BOXES) if i != DEAD_BOX_INDEX], key="rob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(target)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("El jugador no tiene save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer el save del objetivo: {e}")

        options = []
        for i, m in enumerate(mons):
            fp_legacy, fp_stable = _fingerprints_for_mon(m)
            slot = m.get("slot_index", i)
            label = f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}"
            options.append((label, int(slot), fp_legacy, fp_stable))

        label_to_idx = {lbl: (idx, fp_legacy, fp_stable) for (lbl, idx, fp_legacy, fp_stable) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _, _) in options]) if options else None

        if choice_lbl:
            idx, fp_legacy, fp_stable = label_to_idx[choice_lbl]
            flags, fp_key = _load_flags_for_fps(fp_legacy, fp_stable, owner=target)
            if flags.get("blindado"):
                st.error("Este Pokemon esta blindado. No se puede robar.")
                return
            if st.button("Confirmar robo"):
                try:
                    payload = {
                        "type": "steal",
                        "from": target,
                        "origin": origin_kind,
                        "choice_index": idx,
                        "fingerprint": fp_key,
                    }
                    if fp_legacy:
                        payload["fingerprint_legacy"] = fp_legacy
                    if fp_stable:
                        payload["fingerprint_stable"] = fp_stable
                    add_redemption(int(pid), current_user, item, json.dumps(payload, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    add_purchase(current_user, "Comodin de Blindaje por Robo", 0)
                    try:
                        if fp_key:
                            base = dict(flags)
                            base["robado"] = True
                            base["robado_from"] = target
                            base["robado_at"] = int(time.time())
                            base["blindado"] = True
                            upsert_pokemon_flags(target, fp_key, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    st.success("Robo registrado (sin modificar el save).")
                    st.session_state.pop("redeem_ctx", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registrando el robo: {e}")
        return

    if _eq_item(item, "Blindar Pokemon"):
        mons: List[dict] = []
        labels = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                team = extract_team(sav_json) or []
                for i, m in enumerate(team):
                    fp_legacy, fp_stable = _fingerprints_for_mon(m)
                    labels.append((f"Equipo slot {i+1}: {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", fp_legacy, fp_stable))
                try:
                    from conex_pkhex import get_box_meta_quick
                    total_boxes, _ = get_box_meta_quick(sav_json, save_path=spath)
                except Exception:
                    total_boxes = TOTAL_BOXES
                try:
                    total_boxes = int(total_boxes or 0)
                except Exception:
                    total_boxes = 0
                total_boxes = min(total_boxes, TOTAL_BOXES) if total_boxes > 0 else TOTAL_BOXES
                for b in range(total_boxes):
                    box_list = extract_box(sav_json, b, save_path=spath) or []
                    for idx, m in enumerate(box_list):
                        fp_legacy, fp_stable = _fingerprints_for_mon(m)
                        labels.append((f"Caja {b+1} slot {idx+1}: {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", fp_legacy, fp_stable))
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        label_to_fp = {lbl: (fp_legacy, fp_stable) for (lbl, fp_legacy, fp_stable) in labels}
        choice_lbl = st.selectbox("Pokemon a blindar", list(label_to_fp.keys())) if labels else None
        if choice_lbl:
            fp_legacy, fp_stable = label_to_fp[choice_lbl]
            flags, fp_key = _load_flags_for_fps(fp_legacy, fp_stable, owner=current_user)
            _already = bool(flags.get("blindado"))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    payload = {"type": "shield", "fingerprint": fp_key}
                    if fp_legacy:
                        payload["fingerprint_legacy"] = fp_legacy
                    if fp_stable:
                        payload["fingerprint_stable"] = fp_stable
                    add_redemption(int(pid), current_user, item, json.dumps(payload, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    try:
                        if fp_key:
                            base = dict(flags)
                            base["blindado"] = True
                            upsert_pokemon_flags(current_user, fp_key, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    st.success("Blindaje aplicado.")
                    st.toast("Pokemon blindado")
                    st.session_state.pop("redeem_ctx", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error aplicando blindaje: {e}")
        return

    if _eq_item(item, "Comodin de Blindaje por Robo"):
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(TOTAL_BOXES)], key="shieldrob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        for i, m in enumerate(mons):
            fp_legacy, fp_stable = _fingerprints_for_mon(m)
            slot = m.get("slot_index", i)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", int(slot), fp_legacy, fp_stable))
        label_to_idx = {lbl: (idx, fp_legacy, fp_stable) for (lbl, idx, fp_legacy, fp_stable) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _, _) in options]) if options else None
        if choice_lbl:
            _, fp_legacy, fp_stable = label_to_idx[choice_lbl]
            flags, fp_key = _load_flags_for_fps(fp_legacy, fp_stable, owner=current_user)
            _already = bool(flags.get("blindado"))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    payload = {"type": "shield", "fingerprint": fp_key}
                    if fp_legacy:
                        payload["fingerprint_legacy"] = fp_legacy
                    if fp_stable:
                        payload["fingerprint_stable"] = fp_stable
                    add_redemption(int(pid), current_user, item, json.dumps(payload, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    if fp_key:
                        base = dict(flags)
                        base["blindado"] = True
                        base["blindaje_por_robo"] = True
                        upsert_pokemon_flags(current_user, fp_key, json.dumps(base, ensure_ascii=False))
                    st.success("Blindaje por robo aplicado.")
                    st.session_state.pop("redeem_ctx", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error aplicando blindaje: {e}")
        return

    if _eq_item(item, "Revivir Pokemon"):
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                mons = extract_box(sav_json, DEAD_BOX_INDEX, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        for i, m in enumerate(mons):
            fp_legacy, fp_stable = _fingerprints_for_mon(m)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", i, fp_legacy, fp_stable))
        label_to_idx = {lbl: (idx, fp_legacy, fp_stable) for (lbl, idx, fp_legacy, fp_stable) in options}
        choice_lbl = st.selectbox(f"Pokemon a revivir ({DEAD_BOX_LABEL})", [lbl for (lbl, _, _, _) in options]) if options else None
        if choice_lbl:
            _, fp_legacy, fp_stable = label_to_idx[choice_lbl]
            flags, fp_key = _load_flags_for_fps(fp_legacy, fp_stable, owner=current_user)
            if st.button("Confirmar revivir"):
                try:
                    payload = {"type": "revive", "fingerprint": fp_key}
                    if fp_legacy:
                        payload["fingerprint_legacy"] = fp_legacy
                    if fp_stable:
                        payload["fingerprint_stable"] = fp_stable
                    add_redemption(int(pid), current_user, item, json.dumps(payload, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    try:
                        if fp_key:
                            base = dict(flags)
                            base["blindado"] = True
                            base["revivido_at"] = int(time.time())
                            upsert_pokemon_flags(current_user, fp_key, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    try:
                        from app.liga.ranking import clear_ranking_caches

                        clear_ranking_caches()
                    except Exception:
                        pass
                    st.success("Revivir registrado (sin modificar el save).")
                    st.session_state.pop("redeem_ctx", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registrando revivir: {e}")
        return
