# -*- coding: utf-8 -*-
# conex_pkhex.py  Bridge CLI (sin pythonnet): ejecuta un binario que lee .sav Gen3/Gen4 y devuelve JSON
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import os

# Tiempo máximo por invocación al bridge (segundos)
BRIDGE_TIMEOUT = int(os.environ.get("PKHEX_TIMEOUT", "15"))

# Caché simple de lecturas por caja: clave = (sav_path, box_index, mode)
_BOX_CACHE: Dict[Tuple[str, int, Optional[str]], Dict[str, Any]] = {}

def _clear_caches() -> None:
    _BOX_CACHE.clear()

__all__ = ["PKHeXRuntime", "extract_team", "get_box_meta", "extract_box", "has_pc_data", "get_bridge_path"]

# ================= bridge runtime / estado =================

_BRIDGE_PATH: Optional[Path] = None
_LAST_SAV_PATH: Optional[str] = None  # último .sav abierto (para invocar --box N después)

class PKHeXRuntime:
    @staticmethod
    def load(exe_path: str) -> None:
        global _BRIDGE_PATH
        p = Path(exe_path)
        if p.is_dir():
            for cand in ("PKHeXBridge.exe", "pkhex_bridge.exe", "PKHeXBridge"):
                if (p / cand).exists():
                    p = p / cand
                    break
        if not p.exists():
            raise RuntimeError(f"No encuentro el bridge en: {p}")
        _BRIDGE_PATH = p.resolve()
        _clear_caches()

    @staticmethod
    def ensure_loaded() -> None:
        if _BRIDGE_PATH is None:
            raise RuntimeError("Bridge no cargado. Indica la ruta del ejecutable y pulsa 'Cargar'.")

    @staticmethod
    def open_sav(path: str | Path) -> Dict[str, Any]:
        """Abre el .sav una vez para obtener datos generales (party, etc.) y
        deja guardado el path para futuras lecturas por caja."""
        PKHeXRuntime.ensure_loaded()

        # recordar el sav actual para lecturas per-box (e invalidar caché si cambia)
        global _LAST_SAV_PATH
        new_path = str(Path(path))
        if _LAST_SAV_PATH != new_path:
            _LAST_SAV_PATH = new_path
            _clear_caches()

        # --- pasar flags al bridge según sesión/env (sin --box aquí) ---
        args = [str(_BRIDGE_PATH), _LAST_SAV_PATH]

        mode = os.environ.get("PKHEX_MODE")
        os.environ.get("PKHEX_BOX")  # ignorado aquí; per-box se usa en extract_box/get_box_meta

        # Estado de streamlit (si existe)
        try:
            import streamlit as st  # type: ignore
            if not mode:
                mode = st.session_state.get("pkhex_mode")
            # no añadimos box aquí; se usa en llamadas per-box
        except Exception:
            pass

        if mode and str(mode).strip().lower() != "auto":
            args += ["--mode", str(mode).strip()]
        # --- fin flags ---

        sp = subprocess.run(args, capture_output=True, text=True, timeout=BRIDGE_TIMEOUT)
        if sp.returncode != 0:
            err = sp.stderr.strip() or "Error desconocido del bridge."
            raise RuntimeError(f"Bridge falló ({sp.returncode}): {err}")
        try:
            data = json.loads(sp.stdout)
        except Exception as e:
            raise RuntimeError(f"Salida del bridge no es JSON válido: {e}")

        # Acepta cualquier variante v7 (v7, v7d, v7e, v7h, v7j)
        tag = str(data.get("BridgeTag") or "")
        if not tag.startswith("pc-probed-v7"):
            bp = str(_BRIDGE_PATH) if _BRIDGE_PATH else "¿no cargado?"
            raise RuntimeError(
                f"Bridge desactualizado (tag='{tag}'). Se requiere 'pc-probed-v7*'.\n"
                f"Ruta actual: {bp}"
            )
        return data

def get_bridge_path() -> str | None:
    return str(_BRIDGE_PATH) if _BRIDGE_PATH is not None else None

def _current_mode() -> Optional[str]:
    """Lee el modo desde session_state/env (None o 'auto' => no forzar)."""
    mode = os.environ.get("PKHEX_MODE")
    try:
        import streamlit as st  # type: ignore
        if not mode:
            mode = st.session_state.get("pkhex_mode")
    except Exception:
        pass
    if mode:
        m = str(mode).strip().lower()
        return None if m == "auto" else m
    return None

def _ensure_last_sav_from_session() -> None:
    """Si no tenemos _LAST_SAV_PATH, intenta coger active_sav_path de Streamlit."""
    global _LAST_SAV_PATH
    if _LAST_SAV_PATH:
        return
    try:
        import streamlit as st  # type: ignore
        spath = st.session_state.get("active_sav_path")
        if spath:
            _LAST_SAV_PATH = str(spath)
    except Exception:
        pass

def _run_bridge_for_box(box_index: int) -> Optional[Dict[str, Any]]:
    """Ejecuta el bridge con --box N (y modo si procede) usando el último sav conocido."""
    if _BRIDGE_PATH is None:
        raise RuntimeError("Bridge no cargado.")
    _ensure_last_sav_from_session()
    if not _LAST_SAV_PATH:
        return None

    args = [str(_BRIDGE_PATH), _LAST_SAV_PATH, "--box", str(int(box_index))]
    mode = _current_mode()
    if mode:
        args += ["--mode", mode]
    # caché por (sav, box, mode)
    cache_key = (_LAST_SAV_PATH, int(box_index), mode)
    if cache_key in _BOX_CACHE:
        return _BOX_CACHE[cache_key]

    try:
        sp = subprocess.run(args, capture_output=True, text=True, timeout=BRIDGE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    if sp.returncode != 0:
        return None
    try:
        data = json.loads(sp.stdout)
        if isinstance(data, dict):
            _BOX_CACHE[cache_key] = data
            return data
        return None
    except Exception:
        return None

# ================= utilidades (compat/fallback) =================

def _norm_gender(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in {"m", "male", "0"}:
        return "M"
    if s in {"f", "female", "1"}:
        return "F"
    return None

def _ci_get(d: Dict[str, Any], key: str):
    if not isinstance(d, dict):
        return None
    tgt = key.lower()
    for k, v in d.items():
        if str(k).lower() == tgt:
            return v
    return None

def _first_present(d: Dict[str, Any], *keys: str):
    for k in keys:
        v = _ci_get(d, k)
        if v is not None:
            return v
    return None


def _box_count_hint(sav_json: Dict[str, Any]) -> int:
    """Intenta deducir cuántas cajas hay en el save."""
    try:
        raw = _first_present(sav_json, "BoxCount", "box_count", "BoxesCount", "boxesCount")
        if raw is None and isinstance(sav_json, dict) and "BoxCount" in sav_json:
            raw = sav_json.get("BoxCount")
        if raw is not None:
            n = int(raw)
            if 1 <= n <= 40:
                return n
    except Exception:
        pass
    try:
        boxes = _find_boxes_root(sav_json)
        if isinstance(boxes, list):
            return len(boxes)
    except Exception:
        pass
    return 18

# ================= adaptadores UI =================

def _pkm_to_ui(p: Dict[str, Any]) -> Dict[str, Any]:
    dex_id = p.get("Dex") or p.get("DexId") or p.get("SpeciesId") or p.get("SpeciesNum")
    if isinstance(dex_id, str) and dex_id.isdigit():
        dex_id = int(dex_id)

    species_raw = p.get("Species") or p.get("species")
    species_name = p.get("SpeciesName") or p.get("species_name")
    if not species_name and isinstance(species_raw, str) and not species_raw.isdigit():
        species_name = species_raw
    species_display = species_name or (f"#{species_raw}" if isinstance(species_raw, int) else (species_raw or "?"))

    nickname = p.get("Nickname") or p.get("nickname") or ""
    if isinstance(nickname, str):
        nickname = "".join(ch for ch in nickname if ch >= " " and ch != "\uffff").strip()

    level = p.get("Level") or p.get("level")
    nature = p.get("Nature") or p.get("nature")

    moves = p.get("Moves") or p.get("moves") or []
    norm_moves: List[str] = []
    moves_detail: List[Dict[str, Any]] = []
    for m in moves:
        if isinstance(m, dict):
            nm = m.get("Name") or m.get("name") or ""
            if nm:
                norm_moves.append(nm)
                try:
                    mid = int(m.get("MoveId") or m.get("id") or 0)
                except Exception:
                    mid = 0
                try:
                    mpp = int(m.get("PP") or m.get("pp") or 0)
                except Exception:
                    mpp = 0
                moves_detail.append({"name": nm, "id": mid, "pp": mpp})
        elif isinstance(m, int):
            if 1 <= m <= 467:
                norm_moves.append(f"Move#{m}")
                moves_detail.append({"name": f"Move#{m}", "id": int(m), "pp": None})
        else:
            if not m:
                continue
            s = str(m).strip()
            if not s:
                continue
            if s.isdigit() and int(s) > 467:
                continue
            norm_moves.append(s)
            moves_detail.append({"name": s, "id": None, "pp": None})

    form_name = p.get("FormName") or p.get("form_name")
    form_index = p.get("Form") if isinstance(p.get("Form"), int) else p.get("form_index")
    is_shiny = bool(p.get("Shiny") or p.get("is_shiny") or False)
    gender = _norm_gender(p.get("Gender") or p.get("gender"))

    box_index = p.get("BoxIndex")
    slot_index = p.get("SlotIndex")
    source = p.get("Source")

    # OT del mon (para filtrar fantasmas si hiciera falta)
    ot_tid = p.get("OT_TID")
    ot_sid = p.get("OT_SID")
    ot_name = p.get("OT_Name")
    # Held item / Ability
    held_item = p.get("Item") or p.get("HeldItem") or p.get("item") or None
    ability = p.get("Ability") or p.get("ability") or None

    out: Dict[str, Any] = {
        "species": species_display,
        "species_name": species_name,
        "dex_id": dex_id if isinstance(dex_id, int) else None,
        "nickname": nickname,
        "moves": norm_moves,
        "moves_detail": moves_detail,
        "form_name": form_name,
        "form_index": form_index,
        "is_shiny": is_shiny,
        "gender": gender,
        "box_index": box_index,
        "slot_index": slot_index,
        "source": source,
        "ot_tid": ot_tid,
        "ot_sid": ot_sid,
        "ot_name": ot_name,
        "held_item": held_item,
        "ability": ability,
    }
    # Añadir IVs para cálculo de Hidden Power (sin mostrarlos en UI)
    try:
        out["ivs"] = {
            "hp": int(p.get("HP_IV") or 0),
            "atk": int(p.get("ATK_IV") or 0),
            "def": int(p.get("DEF_IV") or 0),
            "spa": int(p.get("SPA_IV") or 0),
            "spd": int(p.get("SPD_IV") or 0),
            "spe": int(p.get("SPE_IV") or 0),
        }
        out["evs"] = {
            "hp": int(p.get("HP_EV") or 0),
            "atk": int(p.get("ATK_EV") or 0),
            "def": int(p.get("DEF_EV") or 0),
            "spa": int(p.get("SPA_EV") or 0),
            "spd": int(p.get("SPD_EV") or 0),
            "spe": int(p.get("SPE_EV") or 0),
        }
    except Exception:
        pass
    if level is not None:
        out["level"] = level
    if nature is not None:
        out["nature"] = nature
    return out

# ====== Fallbacks de detección (se mantienen por compatibilidad) ======

def _extract_mons_from_box_obj(box_obj: Any) -> List[Dict[str, Any]]:
    # caja como lista directa
    if isinstance(box_obj, list):
        return [x for x in box_obj if isinstance(x, dict)]
    # caja como dict con múltiples posibles campos
    if isinstance(box_obj, dict):
        cand = _first_present(box_obj, "Mons", "mons", "Pokémon", "pokemon", "Pkm", "pkm", "Slots", "slots")
        if isinstance(cand, list):
            return [x for x in cand if isinstance(x, dict)]
        if isinstance(cand, dict):
            # coge el primer array que haya dentro
            for v in cand.values():
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
    return []

def _find_boxes_root(data: Dict[str, Any]) -> List[Any]:
    # 1) directos
    boxes = _first_present(data, "Boxes")
    if isinstance(boxes, list):
        return boxes

    # 2) anidados típicos
    for parent in ("PC", "Storage", "BoxData"):
        node = _first_present(data, parent)
        if isinstance(node, dict):
            boxes = _first_present(node, "Boxes")
            if isinstance(boxes, list):
                return boxes

    # 3) otras variantes
    for key in ("boxes", "pc_boxes", "pc", "storage"):
        v = data.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            vv = v.get("Boxes") or v.get("boxes")
            if isinstance(vv, list):
                return vv

    # 4) reconstrucción desde plano: AllMons / PCMons / Mons with Box/Slot
    flat_candidates = (
        _first_present(data, "AllMons", "PCMons", "AllPC", "AllPokémon", "all_mons", "pc_mons")
        or _first_present(_first_present(data, "PC") or {}, "AllMons", "Mons", "Pokémon")
        or _first_present(_first_present(data, "Storage") or {}, "AllMons", "Mons", "Pokémon")
    )
    if isinstance(flat_candidates, list) and flat_candidates:
        boxes_grid: List[List[Dict[str, Any]]] = [[] for _ in range(18)]
        placed = 0
        for p in flat_candidates:
            if not isinstance(p, dict):
                continue
            # claves posibles de caja/slot
            bix = p.get("Box")
            if bix is None:
                bix = p.get("BoxIndex")
            if bix is None:
                bix = p.get("BoxID")
            if bix is None:
                bix = p.get("BoxNo")
            if bix is None and "Index" in p and "Slot" in p:
                idx_abs = p["Index"]
                try:
                    idx_abs = int(idx_abs)
                    bix, _ = divmod(idx_abs, 30)
                except Exception:
                    bix = None
            else:
                _ = p.get("Slot") if "Slot" in p else p.get("SlotIndex")
            try:
                bix = int(bix) if bix is not None else None
            except Exception:
                bix = None

            if bix is not None and 0 <= bix < 18:
                boxes_grid[bix].append(p)
                placed += 1

        if placed > 0:
            return boxes_grid

    # 5) último recurso: escaneo profundo
    def dfs(o) -> Optional[List[Any]]:
        if isinstance(o, list) and len(o) >= 10:
            mon_like = 0
            for el in o[:20]:
                mons = _extract_mons_from_box_obj(el)
                if isinstance(el, list) or (isinstance(el, dict) and (mons or any(isinstance(v, list) for v in (el.values())))):
                    mon_like += 1
            if mon_like >= max(5, len(o)//3):
                return o
        if isinstance(o, dict):
            for _, v in o.items():
                res = dfs(v)
                if res is not None:
                    return res
        if isinstance(o, list):
            for v in o:
                res = dfs(v)
                if res is not None:
                    return res
        return None

    found = dfs(data)
    return found if isinstance(found, list) else []

# ================= API para la UI =================

def has_pc_data(_: Dict[str, Any], save_path: str | None = None) -> bool:
    """Verifica el PC haciendo una llamada real a la caja 0."""
    if save_path:
        p = Path(save_path)
        if not p.exists():
            return False
        PKHeXRuntime.open_sav(p)
    data0 = _run_bridge_for_box(0)
    if not isinstance(data0, dict):
        return False
    boxes = data0.get("Boxes")
    if not isinstance(boxes, list) or not boxes:
        return False
    b0 = boxes[0]
    return isinstance(b0, dict) and "Mons" in b0  # existe estructura de caja

def extract_team(sav_json: str | Dict[str, Any], save_path: str | None = None) -> List[Dict[str, Any]]:
    if save_path:
        p = Path(save_path)
        if p.exists():
            try:
                PKHeXRuntime.open_sav(p)
            except Exception:
                pass
    try:
        data = json.loads(sav_json) if isinstance(sav_json, str) else sav_json
        party = (_first_present(data, "Party") or {})
        mons = _first_present(party, "Mons") or party.get("mons") or []
        return [_pkm_to_ui(p) for p in mons if isinstance(p, dict)]
    except Exception:
        #", e)
        return []

def get_box_meta(sav_json: Dict[str, Any], save_path: str | None = None) -> Tuple[int, List[str]]:
    """Devuelve la cantidad de cajas y sus nombres intentando leerlos directamente del bridge."""
    if save_path:
        p = Path(save_path)
        if p.exists():
            PKHeXRuntime.open_sav(p)
    names: List[str] = []
    ok_any = False
    total = _box_count_hint(sav_json)
    for i in range(total):
        nm = None
        data_i = _run_bridge_for_box(i)
        if isinstance(data_i, dict):
            boxes = data_i.get("Boxes")
            if isinstance(boxes, list) and boxes:
                b0 = boxes[0]
                if isinstance(b0, dict):
                    nm = b0.get("Name") or b0.get("name") or b0.get("BoxName")
        if nm:
            ok_any = True
            names.append(str(nm))
        else:
            names.append(f"Caja {i+1}")

    if ok_any:
        return total, names

    # Fallback a estructura previa (por compatibilidad)
    boxes = _find_boxes_root(sav_json)
    names = []
    for i, b in enumerate(boxes):
        nm = None
        if isinstance(b, dict):
            nm = _first_present(b, "Name", "name", "BoxName", "boxName", "Title", "title")
        names.append(str(nm) if nm else f"Caja {i+1}")
    fb_total = len(boxes) if isinstance(boxes, list) else 0
    return (fb_total if fb_total else total), names

def extract_box(sav_json: Dict[str, Any], box_index: int, save_path: str | None = None) -> List[Dict[str, Any]]:
    """Lee la caja directamente del ejecutable con --box N (como en las pruebas que funcionan).
       Si falla, intenta fallback a la lógica antigua contra el JSON recibido."""
    if save_path:
        p = Path(save_path)
        if p.exists():
            PKHeXRuntime.open_sav(p)
    total = _box_count_hint(sav_json)
    if not (0 <= box_index < total):
        return []

    # 1) Lectura per-box (preferida)
    data_i = _run_bridge_for_box(box_index)
    if isinstance(data_i, dict):
        boxes = data_i.get("Boxes")
        if isinstance(boxes, list) and boxes:
            b0 = boxes[0]
            mons = (b0.get("Mons") if isinstance(b0, dict) else None) or []
            mapped = [_pkm_to_ui(p) for p in mons if isinstance(p, dict)]
            return mapped

    # 2) Fallback: usar estructura del JSON recibido (antiguo)
    boxes = _find_boxes_root(sav_json)
    if not isinstance(boxes, list) or not (0 <= box_index < len(boxes)):
        return []

    box_obj = boxes[box_index]
    mons = _extract_mons_from_box_obj(box_obj)
    mapped = [_pkm_to_ui(p) for p in mons if isinstance(p, dict)]
    if mapped:
        return mapped

    # 3) Fallback profundo
    collected: List[Dict[str, Any]] = []

    def looks_like_mon(d: Dict[str, Any]) -> bool:
        if not isinstance(d, dict):
            return False
        keys = {k.lower() for k in d.keys()}
        hints = {"species", "speciesname", "dex", "dexid", "speciesid", "level", "moves", "nature"}
        return len(keys & hints) >= 2

    def dfs(o: Any, depth: int = 0):
        if depth > 4:
            return
        if isinstance(o, dict):
            if looks_like_mon(o):
                collected.append(o)
            for v in o.values():
                dfs(v, depth + 1)
        elif isinstance(o, list):
            for it in o:
                dfs(it, depth + 1)

    dfs(box_obj)
    mapped = [_pkm_to_ui(p) for p in collected if isinstance(p, dict)]
    return mapped








# --- fast box meta: probe few boxes only ---

def get_box_meta_quick(sav_json: Dict[str, Any], save_path: str | None = None, max_probe: int = 3) -> Tuple[int, List[str]]:
    """VersiИn rЗpida de get_box_meta: sЗlo sondea unas pocas cajas para nombrarlas."""
    if save_path:
        p = Path(save_path)
        if p.exists():
            try:
                PKHeXRuntime.open_sav(p)
            except Exception:
                pass

    names: List[str] = []
    probe = 0
    total = _box_count_hint(sav_json)
    for i in range(total):
        nm = None
        if probe < max_probe:
            data_i = _run_bridge_for_box(i)
            if isinstance(data_i, dict):
                boxes = data_i.get("Boxes")
                if isinstance(boxes, list) and boxes:
                    b0 = boxes[0]
                    if isinstance(b0, dict):
                        nm = b0.get("Name") or b0.get("name") or b0.get("BoxName")
            probe += 1
        if nm:
            names.append(str(nm))
        else:
            names.append(f"Caja {i+1}")

    return total, names


