from __future__ import annotations

"""
Carga ligera de datos de Showdown con caché local para:
- Tipos por especie/forma
- Detalles de movimientos (tipo, categoría, potencia, precisión, pp)

No requiere dependencias externas: usa urllib. Persistencia opcional en disco
para evitar depender siempre de red.
"""
import json  # noqa: E402
import time  # noqa: E402
import unicodedata  # noqa: E402
import re  # noqa: E402
from functools import lru_cache  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, Any, Optional, List  # noqa: E402

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - disponible sólo en runtime de app
    st = None  # type: ignore

BASE_URL = "https://play.pokemonshowdown.com/data"

# Carpeta de datos persistentes (alineada con storage.py)
_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = _BASE_DIR / "data"
if not DATA_DIR.exists():
    alt = _BASE_DIR.parent / "data"
    if alt.exists():
        DATA_DIR = alt
DATA_DIR.mkdir(exist_ok=True)

CACHE_TTL = 24 * 3600  # 24h

TYPE_COLORS = {
    "Normal": "#A8A77A",
    "Fire": "#EE8130",
    "Water": "#6390F0",
    "Electric": "#F7D02C",
    "Grass": "#7AC74C",
    "Ice": "#96D9D6",
    "Fighting": "#C22E28",
    "Poison": "#A33EA1",
    "Ground": "#E2BF65",
    "Flying": "#A98FF3",
    "Psychic": "#F95587",
    "Bug": "#A6B91A",
    "Rock": "#B6A136",
    "Ghost": "#735797",
    "Dragon": "#6F35FC",
    "Dark": "#705746",
    "Steel": "#B7B7CE",
    "Fairy": "#D685AD",
}


def _now() -> int:
    return int(time.time())


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except (UnicodeError, json.JSONDecodeError):
            continue
        except Exception:
            return None
    return None


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(obj), encoding="utf-8")
    except Exception:
        pass


def _fetch_json(url: str) -> Optional[Dict[str, Any]]:
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception:
        return None


# ---------- PokeAPI helpers (ES names) ----------
def _slugify(name: str) -> str:
    s = name.strip().lower()
    repl = {
        " ": "-",
        "'": "",
        '"': "",
        ".": "",
        ",": "",
        ":": "",
        "!": "",
        "?": "",
        "_": "-",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    s = s.replace("--", "-")
    return s


def _to_ascii(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFD", text)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t


def _norm_key(text: str) -> str:
    if not text:
        return ""
    base = _to_ascii(str(text)).strip().lower()
    return re.sub(r"[^a-z0-9]", "", base)


MOVES_ES_CACHE_MEM: Dict[str, str] = {}
ABILITIES_ES_CACHE_MEM: Dict[str, str] = {}
ABILITY_DESC_ES_CACHE_MEM: Dict[str, str] = {}
ITEMS_ES_CACHE_MEM: Dict[str, str] = {}
ITEMS_ID_ES_CACHE_MEM: Dict[str, str] = {}
MOVE_DESC_ES_CACHE_MEM: Dict[str, str] = {}


def _cached_lookup(
    cache_file: Path, key: str, fetch_fn, *, mem_cache: Dict[str, str]
) -> Optional[str]:
    # Memoria primero
    if key in mem_cache:
        return mem_cache.get(key) or None
    try:
        cache = (
            json.loads(cache_file.read_text(encoding="utf-8"))
            if cache_file.exists()
            else {}
        )
    except Exception:
        cache = {}
    if key in cache:
        val = cache.get(key)
        if isinstance(val, str) and val:
            mem_cache[key] = val
            return val
        # si estaba None o vaco, reintentar fetch para evitar cachear fallos
    try:
        val = fetch_fn(key)
    except Exception:
        val = None
    # Solo cachear si hay valor
    if isinstance(val, str) and val:
        cache[key] = val
        mem_cache[key] = val
    try:
        cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return val


FALLBACK_MOVES_ES = {
    "tackle": "Placaje",
    "scratch": "Aranazo",
    "leer": "Malicioso",
    "growl": "Grunido",
    "ember": "Ascuas",
    "taunt": "Mofa",
    "defense-curl": "Rizo Defensa",
    "rock-throw": "Lanzarrocas",
    "harden": "Fortaleza",
    "absorb": "Absorber",
    "growth": "Desarrollo",
    "stun-spore": "Paralizador",
    "poison-sting": "Picotazo Venenoso",
    "vine-whip": "Latigo Cepa",
    "water-gun": "Pistola Agua",
    "gust": "Tornado",
    "quick-attack": "Ataque Rapido",
}


def move_name_es(name_en: str) -> str:
    if not name_en:
        return "-"
    slug = _slugify(name_en)
    if slug in FALLBACK_MOVES_ES:
        return FALLBACK_MOVES_ES[slug]
    cache_file = DATA_DIR / "moves_es_cache.json"

    def fetch(slug_: str) -> Optional[str]:
        url = f"https://pokeapi.co/api/v2/move/{slug_}/"
        try:
            import urllib.request
            import json as _json

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            for n in data.get("names", []):
                if n and n.get("language", {}).get("name") == "es":
                    return n.get("name")
        except Exception:
            return None
        return None

    val = _cached_lookup(cache_file, slug, fetch, mem_cache=MOVES_ES_CACHE_MEM)
    return _to_ascii(val or name_en)


def move_desc_es(name_en: str, *, move_id: Optional[int] = None) -> str:
    if not name_en and move_id is None:
        return ""

    slug = _slugify(name_en or "")
    cache_key = str(move_id or slug)
    cache_file = DATA_DIR / "moves_desc_es_cache.json"

    def fetch(key: str) -> Optional[str]:
        endpoint = key if key.isdigit() else slug
        if not endpoint:
            return None
        url = f"https://pokeapi.co/api/v2/move/{endpoint}/"
        try:
            import urllib.request
            import json as _json

            req = urllib.request.Request(url, headers={"User-Agent": "PokeApp/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            entries = data.get("flavor_text_entries") or []
            preferred_versions = {
                "scarlet-violet",
                "sword-shield",
                "ultra-sun-ultra-moon",
                "black-2-white-2",
                "black-white",
            }
            fallback = ""
            for entry in entries:
                if not entry or entry.get("language", {}).get("name") != "es":
                    continue
                text = (
                    str(entry.get("flavor_text") or "")
                    .replace("\n", " ")
                    .replace("\f", " ")
                    .strip()
                )
                if not text:
                    continue
                fallback = fallback or text
                version_group = entry.get("version_group", {}).get("name")
                if version_group in preferred_versions:
                    return text
            if fallback:
                return fallback
            for entry in data.get("effect_entries") or []:
                if entry and entry.get("language", {}).get("name") == "es":
                    text = str(
                        entry.get("short_effect") or entry.get("effect") or ""
                    ).strip()
                    if text:
                        return text.replace("\n", " ").replace("\f", " ")
        except Exception:
            return None
        return None

    val = _cached_lookup(cache_file, cache_key, fetch, mem_cache=MOVE_DESC_ES_CACHE_MEM)
    return _to_ascii(val or "")


FALLBACK_ABILITIES_ES = {
    "blaze": "Mar Llamas",
    "torrent": "Torrente",
    "overgrow": "Espesura",
    "rock-head": "Cabeza Roca",
    "sturdy": "Robustez",
    "poison-point": "Punto Toxico",
    "natural-cure": "Cura Natural",
    "chlorophyll": "Clorofila",
}


def ability_name_es(name_en: str) -> str:
    if not name_en:
        return "-"
    slug = _slugify(name_en)
    if slug in FALLBACK_ABILITIES_ES:
        return FALLBACK_ABILITIES_ES[slug]
    cache_file = DATA_DIR / "abilities_es_cache.json"

    def fetch(slug_: str) -> Optional[str]:
        url = f"https://pokeapi.co/api/v2/ability/{slug_}/"
        try:
            import urllib.request
            import json as _json

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            for n in data.get("names", []):
                if n and n.get("language", {}).get("name") == "es":
                    return n.get("name")
        except Exception:
            return None
        return None

    val = _cached_lookup(cache_file, slug, fetch, mem_cache=ABILITIES_ES_CACHE_MEM)
    return _to_ascii(val or name_en)


def ability_desc_es(name_en: str) -> str:
    if not name_en:
        return ""
    slug = _slugify(name_en)
    cache_file = DATA_DIR / "abilities_desc_es_cache.json"

    def fetch(slug_: str) -> Optional[str]:
        url = f"https://pokeapi.co/api/v2/ability/{slug_}/"
        try:
            import urllib.request
            import json as _json

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            for entry in data.get("flavor_text_entries", []):
                if entry and entry.get("language", {}).get("name") == "es":
                    text = entry.get("flavor_text") or ""
                    return text.replace("\n", " ").replace("\f", " ").strip()
        except Exception:
            return None
        return None

    val = _cached_lookup(cache_file, slug, fetch, mem_cache=ABILITY_DESC_ES_CACHE_MEM)
    return _to_ascii(val or "")


def item_name_es(name_or_id: str) -> str:
    if not name_or_id:
        return "-"
    raw = str(name_or_id).strip()
    raw = raw.lstrip("#")
    if not raw:
        return "-"
    if raw.isdigit() and int(raw) == 0:
        return "-"
    if raw.isdigit():
        cached = ITEMS_ID_ES_CACHE_MEM.get(raw)
        if cached:
            return cached
        try:
            cache_paths = [
                DATA_DIR / "item_names_es.json",
                _BASE_DIR / "assets" / "item_names_es.json",
                _BASE_DIR.parent / "assets" / "item_names_es.json",
                Path.cwd() / "assets" / "item_names_es.json",
            ]
            for cache_file in cache_paths:
                if not cache_file.exists():
                    continue
                data = _read_json(cache_file)
                if isinstance(data, dict) and raw in data:
                    name = str(data.get(raw) or "").strip()
                    if name:
                        name = _to_ascii(name)
                        ITEMS_ID_ES_CACHE_MEM[raw] = name
                        return name
        except Exception:
            pass
    slug = raw if raw.isdigit() else _slugify(raw)
    cache_file = DATA_DIR / "items_es_cache.json"

    def fetch(slug_: str) -> Optional[str]:
        url = f"https://pokeapi.co/api/v2/item/{slug_}/"
        try:
            import urllib.request
            import json as _json

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            for n in data.get("names", []):
                if n and n.get("language", {}).get("name") == "es":
                    return n.get("name")
        except Exception:
            return None
        return None

    val = _cached_lookup(cache_file, slug, fetch, mem_cache=ITEMS_ES_CACHE_MEM)
    return _to_ascii(val or name_or_id)


def _candidate_data_dirs() -> list[Path]:
    seen = set()
    out: list[Path] = []
    for p in (
        DATA_DIR,
        _BASE_DIR / "data",
        _BASE_DIR / "assets",
        _BASE_DIR.parent / "data",
        _BASE_DIR.parent / "assets",
        Path.cwd() / "data",
        Path.cwd() / "assets",
        Path.cwd().parent / "data",
        Path.cwd().parent / "assets",
    ):
        try:
            if p and p.exists() and p.is_dir():
                key = str(p.resolve())
                if key not in seen:
                    seen.add(key)
                    out.append(p)
        except Exception:
            continue
    return out or [DATA_DIR]


def _load_dataset(name: str) -> Dict[str, Any]:
    """Carga dataset `name` de Showdown con caché a disco y opcionalmente cacheo en memoria de Streamlit."""
    cache_file = DATA_DIR / f"ps_{name}.json"
    stamp_file = DATA_DIR / f"ps_{name}.stamp"

    def expired() -> bool:
        try:
            ts = int(stamp_file.read_text())
            return (_now() - ts) > CACHE_TTL
        except Exception:
            return True

    # Intenta cache en disco
    if cache_file.exists() and not expired():
        obj = _read_json(cache_file) or {}
        if obj:
            return obj

    # Busca en otras rutas de data si el cache principal falla
    for d in _candidate_data_dirs():
        alt_file = d / f"ps_{name}.json"
        if alt_file == cache_file:
            continue
        obj = _read_json(alt_file) or {}
        if obj:
            try:
                _write_json(cache_file, obj)
                stamp_file.write_text(str(_now()))
            except Exception:
                pass
            return obj

    # Descarga
    url = f"{BASE_URL}/{name}.json"
    obj = _fetch_json(url) or {}
    if obj:
        _write_json(cache_file, obj)
        try:
            stamp_file.write_text(str(_now()))
        except Exception:
            pass
        return obj

    # Fallback a lo que hubiera en disco aunque esté expirado
    return _read_json(cache_file) or {}


_DEX_INDEX: Optional[Dict[str, Any]] = None


def _build_dex_index() -> Dict[str, Any]:
    pokedex = _load_dataset("pokedex") or {}
    moves = _load_dataset("moves") or {}

    moves_by_num: Dict[int, Dict[str, Any]] = {}
    moves_by_key: Dict[str, Dict[str, Any]] = {}
    for key, entry in (moves or {}).items():
        if not isinstance(entry, dict):
            continue
        num = entry.get("num")
        if isinstance(num, int):
            moves_by_num[num] = entry
        name = entry.get("name")
        if isinstance(name, str) and name:
            moves_by_key[_norm_key(name)] = entry
        if isinstance(key, str) and key:
            moves_by_key.setdefault(_norm_key(key), entry)

    pokedex_by_num: Dict[int, Dict[str, Any]] = {}
    for key, entry in (pokedex or {}).items():
        if not isinstance(entry, dict):
            continue
        num = entry.get("num")
        if isinstance(num, int):
            pokedex_by_num[num] = entry
        if isinstance(key, str) and key:
            entry.setdefault("_key", key)

    return {
        "pokedex": pokedex or {},
        "moves": moves or {},
        "moves_by_num": moves_by_num,
        "moves_by_key": moves_by_key,
        "pokedex_by_num": pokedex_by_num,
    }


def _dex_index() -> Dict[str, Any]:
    global _DEX_INDEX
    if _DEX_INDEX is None:
        _DEX_INDEX = _build_dex_index()
    return _DEX_INDEX


_MOVES_ES_ID_MAP: Optional[Dict[str, int]] = None


def _load_moves_es_id_map() -> Dict[str, int]:
    global _MOVES_ES_ID_MAP
    if _MOVES_ES_ID_MAP is not None:
        return _MOVES_ES_ID_MAP
    cache_paths = [
        Path(__file__).resolve().parents[1] / "assets" / "moves_es_id.json",
        DATA_DIR / "moves_es_id.json",
    ]
    for cache_file in cache_paths:
        if cache_file.exists():
            try:
                raw = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    _MOVES_ES_ID_MAP = {str(k): int(v) for k, v in raw.items()}
                    return _MOVES_ES_ID_MAP
            except Exception:
                pass

    mapping: Dict[str, int] = {}
    # PokeAPI CSV (single request) for Spanish move names
    try:
        import csv
        import urllib.request

        url = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/move_names.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        reader = csv.reader(data.splitlines())
        next(reader, None)
        # Expected: move_id, local_language_id, name
        for row in reader:
            if len(row) < 3:
                continue
            try:
                move_id = int(row[0])
                lang_id = int(row[1])
            except Exception:
                continue
            if lang_id != 7:
                continue
            name_es = row[2]
            key = _norm_key(name_es)
            if key and key not in mapping:
                mapping[key] = move_id
    except Exception:
        mapping = {}

    # Fallbacks: manual minimal map
    manual = {
        "fuegosagrado": 221,  # Sacred Fire
        "velocextrema": 245,  # Extreme Speed
    }
    for k, v in manual.items():
        mapping.setdefault(k, v)

    try:
        (DATA_DIR / "moves_es_id.json").write_text(
            json.dumps(mapping, ensure_ascii=True), encoding="utf-8"
        )
    except Exception:
        pass
    _MOVES_ES_ID_MAP = mapping
    return mapping


def _move_id_from_es(name: str) -> Optional[int]:
    if not name:
        return None
    key = _norm_key(name)
    if not key:
        return None
    mapping = _load_moves_es_id_map()
    mid = mapping.get(key)
    try:
        return int(mid) if mid is not None else None
    except Exception:
        return None


def pokedex_data() -> Dict[str, Any]:
    return _dex_index().get("pokedex") or {}


def moves_data() -> Dict[str, Any]:
    return _dex_index().get("moves") or {}


@lru_cache(maxsize=4096)
def pokedex_entry(
    *,
    species_name: str | None,
    dex_id: Optional[int] = None,
    form_index: Optional[int] = None,
    form_name: Optional[str] = None,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    dex = _dex_index()
    entry = {}
    if species_name:
        from showdown_sprites import showdown_id  # evitar ciclos en import

        sid = showdown_id(
            species_name=species_name,
            form_index=form_index,
            form_name=form_name,
            gender=gender,
        )
        key = _to_data_key(sid)
        entry = dex.get("pokedex", {}).get(key) or {}
        if not entry and "-" in sid:
            base = sid.split("-", 1)[0]
            entry = dex.get("pokedex", {}).get(_to_data_key(base)) or {}

    if not entry:
        num = None
        if dex_id is not None:
            try:
                num = int(dex_id)
            except Exception:
                num = None
        if num is None and species_name:
            s = str(species_name).strip()
            if s.startswith("#") and s[1:].isdigit():
                num = int(s[1:])
            elif s.isdigit():
                num = int(s)
        if num is not None:
            entry = dex.get("pokedex_by_num", {}).get(num) or {}
    return entry or {}


def _to_data_key(showdown_id: str) -> str:
    """Convierte un id tipo 'rotom-heat' a clave de dataset 'rotomheat'."""
    return showdown_id.replace("-", "").lower()


@lru_cache(maxsize=4096)
def species_types(
    *,
    species_name: str,
    form_index: Optional[int] = None,
    form_name: Optional[str] = None,
    gender: Optional[str] = None,
    dex_id: Optional[int] = None,
) -> List[str]:
    """Devuelve [Tipo1, Tipo2?] usando Pokedex. Usa forma si aplica."""
    entry = pokedex_entry(
        species_name=species_name,
        dex_id=dex_id,
        form_index=form_index,
        form_name=form_name,
        gender=gender,
    )
    types = entry.get("types") or []
    return [str(t).title() for t in types]


@lru_cache(maxsize=8192)
def move_info(
    move_name: str, *, move_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    if not move_name and move_id is None:
        return None
    dex = _dex_index()
    entry = None
    if move_id is not None:
        try:
            entry = dex.get("moves_by_num", {}).get(int(move_id))
        except Exception:
            entry = None
    if not entry and move_name:
        key = _norm_key(move_name)
        entry = dex.get("moves", {}).get(key) or dex.get("moves_by_key", {}).get(key)
        if not entry:
            import re as _re

            m = _re.search(r"\d+", str(move_name))
            if m:
                try:
                    entry = dex.get("moves_by_num", {}).get(int(m.group(0)))
                except Exception:
                    entry = None
    if not entry and move_name:
        mid = _move_id_from_es(move_name)
        if mid is not None:
            entry = dex.get("moves_by_num", {}).get(int(mid))
    if not entry:
        return None
    # Normaliza campos
    out = {
        "name": entry.get("name") or move_name,
        "type": str(entry.get("type") or "").title(),
        "category": entry.get("category"),
        "power": entry.get("basePower"),
        "accuracy": entry.get("accuracy"),
        "pp": entry.get("pp"),
    }
    return out


def type_color(t: str) -> str:
    return TYPE_COLORS.get(str(t).title(), "#999999")


def showdown_export(
    team: List[Dict[str, Any]],
    *,
    include_ability: bool = False,
    include_evs: bool = False,
    include_ivs: bool = False,
) -> str:
    """Exporta equipo en formato Showdown. Si `include_ability/evs/ivs` están en True
    y los datos existen, se incluyen en el paste."""
    lines: List[str] = []
    for p in team:
        species = p.get("species_name") or p.get("species") or "?"
        nickname = p.get("nickname") or ""
        title = (
            f"{nickname} ({species})" if nickname and nickname != species else species
        )
        item = p.get("held_item") or p.get("item")
        if item:
            title += f" @ {item}"
        lines.append(title)
        if include_ability:
            ab = p.get("ability") or p.get("Ability")
            if ab:
                lines.append(f"Ability: {ab}")
        # Nature
        nat = p.get("nature")
        if nat:
            lines.append(f"{nat} Nature")
        if include_evs:
            evs = p.get("evs") or {}
            order = [
                ("hp", "HP"),
                ("atk", "Atk"),
                ("def", "Def"),
                ("spa", "SpA"),
                ("spd", "SpD"),
                ("spe", "Spe"),
            ]
            parts = []
            for k, label in order:
                try:
                    v = int(evs.get(k) or 0)
                except Exception:
                    v = 0
                if v:
                    parts.append(f"{v} {label}")
            if parts:
                lines.append("EVs: " + " / ".join(parts))
        if include_ivs:
            ivs = p.get("ivs") or {}
            order = [
                ("hp", "HP"),
                ("atk", "Atk"),
                ("def", "Def"),
                ("spa", "SpA"),
                ("spd", "SpD"),
                ("spe", "Spe"),
            ]
            parts = []
            for k, label in order:
                v = ivs.get(k)
                try:
                    v = int(v)
                except Exception:
                    v = None
                if v is not None and v != 31:
                    parts.append(f"{v} {label}")
            if parts:
                lines.append("IVs: " + " / ".join(parts))
        # Moves
        moves = p.get("moves") or []
        for mv in moves:
            if not mv:
                continue
            lines.append(f"- {mv}")
        lines.append("")
    return "\n".join(lines).strip()
