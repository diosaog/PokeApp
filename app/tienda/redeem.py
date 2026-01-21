from __future__ import annotations

import json
import time
from typing import List
import streamlit as st

from app.tienda.common import _eq_item
from storage import (
    add_purchase,
    add_redemption,
    get_flags_by_fingerprints,
    set_purchase_status,
    upsert_pokemon_flags,
)
from conex_pkhex import extract_box, extract_team, open_sav_cached
from utils import USERS, list_user_saves


def render_redeem_flow(ctx: dict, current_user: str) -> None:
    item = ctx.get("item")
    pid = ctx.get("pid")
    _ = int(ctx.get("step") or 1)
    st.markdown("---")
    st.subheader(f"Usar: {item} (#{pid})")

    if _eq_item(item, "Robar Pokemon"):
        players = [u for u in USERS.keys() if u != current_user]
        target = st.selectbox("Jugador objetivo", players, key="rob_target")
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(18) if i != 17], key="rob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(target)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json, save_path=spath)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("El jugador no tiene save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer el save del objetivo: {e}")

        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            slot = m.get("slot_index", i)
            label = f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}"
            options.append((label, int(slot), fp))

        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _) in options]) if options else None

        if choice_lbl:
            idx, fp = label_to_idx[choice_lbl]
            flags = get_flags_by_fingerprints([fp]).get(fp)
            if flags:
                try:
                    fj = json.loads(flags.get("flags_json") or "{}")
                except Exception:
                    fj = {}
                if fj.get("blindado"):
                    st.error("Este Pokemon esta blindado. No se puede robar.")
                    return
            if st.button("Confirmar robo"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "steal", "from": target, "origin": origin_kind, "choice_index": idx, "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    add_purchase(current_user, "Comodin de Blindaje por Robo", 0)
                    try:
                        cur = get_flags_by_fingerprints([fp]).get(fp)
                        base = {}
                        if cur and isinstance(cur.get("flags_json"), str) and cur["flags_json"].strip():
                            base = json.loads(cur["flags_json"])
                            if not isinstance(base, dict):
                                base = {}
                        base["robado"] = True
                        base["robado_from"] = target
                        base["robado_at"] = int(time.time())
                        base["blindado"] = True
                        upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
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
                from pkmmeta import pokemon_fingerprint
                team = extract_team(sav_json, save_path=spath) or []
                for i, m in enumerate(team):
                    fp = pokemon_fingerprint(m)
                    labels.append((f"Equipo slot {i+1}: {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", fp))
                try:
                    from conex_pkhex import get_box_meta_quick
                    total_boxes, _ = get_box_meta_quick(sav_json, save_path=spath)
                except Exception:
                    total_boxes = 18
                for b in range(total_boxes):
                    box_list = extract_box(sav_json, b, save_path=spath) or []
                    for idx, m in enumerate(box_list):
                        fp = pokemon_fingerprint(m)
                        labels.append((f"Caja {b+1} slot {idx+1}: {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", fp))
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        label_to_fp = {lbl: fp for (lbl, fp) in labels}
        choice_lbl = st.selectbox("Pokemon a blindar", list(label_to_fp.keys())) if labels else None
        if choice_lbl:
            fp = label_to_fp[choice_lbl]
            _cur = get_flags_by_fingerprints([fp]).get(fp)
            _already = False
            if _cur:
                try:
                    _fj = json.loads(_cur.get("flags_json") or "{}")
                except Exception:
                    _fj = {}
                _already = bool(_fj.get("blindado"))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "shield", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    try:
                        base = {}
                        if _cur and isinstance(_cur.get("flags_json"), str) and _cur["flags_json"].strip():
                            base = json.loads(_cur["flags_json"]) if isinstance(json.loads(_cur["flags_json"]), dict) else {}
                        base["blindado"] = True
                        upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
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
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(18)], key="shieldrob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = open_sav_cached(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json, save_path=spath)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            slot = m.get("slot_index", i)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", int(slot), fp))
        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _) in options]) if options else None
        if choice_lbl:
            _, fp = label_to_idx[choice_lbl]
            _cur = get_flags_by_fingerprints([fp]).get(fp)
            _already = False
            if _cur:
                try:
                    _fj = json.loads(_cur.get("flags_json") or "{}")
                except Exception:
                    _fj = {}
                _already = bool(_fj.get("blindado"))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "shield", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    base = {}
                    if _cur and isinstance(_cur.get("flags_json"), str) and _cur["flags_json"].strip():
                        try:
                            base = json.loads(_cur["flags_json"])
                            if not isinstance(base, dict):
                                base = {}
                        except Exception:
                            base = {}
                    base["blindado"] = True
                    base["blindaje_por_robo"] = True
                    upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
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
                mons = extract_box(sav_json, 17, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", i, fp))
        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon a revivir (Caja 18)", [lbl for (lbl, _, _) in options]) if options else None
        if choice_lbl:
            _, fp = label_to_idx[choice_lbl]
            if st.button("Confirmar revivir"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "revive", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), "used")
                    try:
                        cur = get_flags_by_fingerprints([fp]).get(fp)
                        base = {}
                        if cur and isinstance(cur.get("flags_json"), str) and cur["flags_json"].strip():
                            base = json.loads(cur["flags_json"])
                            if not isinstance(base, dict):
                                base = {}
                        base["blindado"] = True
                        base["revivido_at"] = int(time.time())
                        upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    st.success("Revivir registrado (sin modificar el save).")
                    st.session_state.pop("redeem_ctx", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registrando revivir: {e}")
        return
