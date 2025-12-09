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
from pathlib import Path  # noqa: E402
from typing import Dict, Any, Optional, List  # noqa: E402

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - disponible sólo en runtime de app
    st = None  # type: ignore

BASE_URL = "https://play.pokemonshowdown.com/data"

# Carpeta de datos persistentes (misma que storage.py usa para DB)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
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
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
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
    repl = {" ": "-", "'": "", "": "", ".": "", ",": "", ":": "", "!": "", "?": "", "_": "-"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = s.replace("--", "-")
    return s


MOVES_ES_CACHE_MEM: Dict[str, str] = {}
ABILITIES_ES_CACHE_MEM: Dict[str, str] = {}


def _cached_lookup(cache_file: Path, key: str, fetch_fn, *, mem_cache: Dict[str, str]) -> Optional[str]:
    # Memoria primero
    if key in mem_cache:
        return mem_cache.get(key) or None
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
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
    # Gen 1-4 comunes
    "tackle": "Placaje",
    "scratch": "Arañazo",
    "leer": "Malicioso",
    "growl": "Gruñido",
    "ember": "Ascuas",
    "taunt": "Mofa",
    "defense-curl": "Rizo Defensa",
    "rock-throw": "Lanzarrocas",
    "harden": "Fortaleza",
    "absorb": "Absorber",
    "growth": "Desarrollo",
    "stun-spore": "Paralizador",
    "poison-sting": "Picotazo Venenoso",
    "vine-whip": "Látigo Cepa",
    "water-gun": "Pistola Agua",
    "gust": "Tornado",
    "quick-attack": "Ataque Rápido",
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
    return val or name_en


FALLBACK_ABILITIES_ES = {
    "blaze": "Mar Llamas",
    "torrent": "Torrente",
    "overgrow": "Espesura",
    "rock-head": "Cabeza Roca",
    "sturdy": "Robustez",
    "poison-point": "Punto Tóxico",
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
    return val or name_en


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


def pokedex_data() -> Dict[str, Any]:
    if st is not None:
        @st.cache_data(show_spinner=False)
        def _load() -> Dict[str, Any]:
            return _load_dataset("pokedex")
        return _load()
    return _load_dataset("pokedex")


def moves_data() -> Dict[str, Any]:
    if st is not None:
        @st.cache_data(show_spinner=False)
        def _load() -> Dict[str, Any]:
            return _load_dataset("moves")
        return _load()
    return _load_dataset("moves")


def _to_data_key(showdown_id: str) -> str:
    """Convierte un id tipo 'rotom-heat' a clave de dataset 'rotomheat'."""
    return showdown_id.replace("-", "").lower()


def species_types(*, species_name: str, form_index: Optional[int] = None,
                  form_name: Optional[str] = None, gender: Optional[str] = None) -> List[str]:
    """Devuelve [Tipo1, Tipo2?] usando Pokédex de Showdown. Usa forma si aplica."""
    from showdown_sprites import showdown_id  # evitar ciclos en import
    sid = showdown_id(species_name=species_name, form_index=form_index, form_name=form_name, gender=gender)
    key = _to_data_key(sid)
    pdx = pokedex_data()
    entry = pdx.get(key) or {}
    types = entry.get("types") or []
    # A veces las formas no están; intenta base sin forma
    if not types and "-" in sid:
        base = sid.split("-", 1)[0]
        entry = pdx.get(_to_data_key(base)) or {}
        types = entry.get("types") or []
    # Normaliza a lista de títulos capitalizados
    return [str(t).title() for t in types]


def move_info(move_name: str) -> Optional[Dict[str, Any]]:
    if not move_name:
        return None
    key = move_name.strip().lower().replace(" ", "").replace("-", "")
    md = moves_data()
    entry = md.get(key)
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
        title = f"{nickname} ({species})" if nickname and nickname != species else species
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
            order = [("hp","HP"),("atk","Atk"),("def","Def"),("spa","SpA"),("spd","SpD"),("spe","Spe")]
            parts=[]
            for k,label in order:
                try:
                    v=int(evs.get(k) or 0)
                except Exception:
                    v=0
                if v:
                    parts.append(f"{v} {label}")
            if parts:
                lines.append("EVs: "+" / ".join(parts))
        if include_ivs:
            ivs = p.get("ivs") or {}
            order = [("hp","HP"),("atk","Atk"),("def","Def"),("spa","SpA"),("spd","SpD"),("spe","Spe")]
            parts=[]
            for k,label in order:
                v = ivs.get(k)
                try:
                    v = int(v)
                except Exception:
                    v = None
                if v is not None and v != 31:
                    parts.append(f"{v} {label}")
            if parts:
                lines.append("IVs: "+" / ".join(parts))
        # Moves
        moves = p.get("moves") or []
        for mv in moves:
            if not mv:
                continue
            lines.append(f"- {mv}")
        lines.append("")
    return "\n".join(lines).strip()









