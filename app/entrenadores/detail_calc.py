from __future__ import annotations

from typing import Optional

from dexdata import pokedex_entry
from i18n import NATURES_ES

def _extract_stats_from_p(p: dict) -> dict | None:
    try:
        stx = p.get("stats") if isinstance(p, dict) else None
        if isinstance(stx, dict) and any(k in stx for k in ("hp", "atk", "def", "spa", "spd", "spe")):
            out = {}
            for k in ("hp", "atk", "def", "spa", "spd", "spe"):
                v = stx.get(k)
                try:
                    out[k] = int(v)
                except Exception:
                    pass
            if out:
                return out

        keys = [("hp", "HP"), ("atk", "ATK"), ("def", "DEF"), ("spa", "SPA"), ("spd", "SPD"), ("spe", "SPE")]
        out = {}
        for k, up in keys:
            v = p.get(k)
            if v is None:
                v = p.get(up)
            if v is not None:
                try:
                    out[k] = int(v)
                except Exception:
                    pass
        if out and len(out) >= 3:
            return out

        return _calc_stats_from_base(p)
    except Exception:
        return None


def _calc_stats_from_base(
    p: dict,
    *,
    ivs: dict | None = None,
    evs: dict | None = None,
    nature: str | None = None,
) -> dict | None:
    try:
        species = p.get("species_name") or p.get("species")
        dex_id = p.get("dex_id")
        if not species and dex_id is None:
            return None
        entry = pokedex_entry(
            species_name=species,
            dex_id=dex_id,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            gender=p.get("gender"),
        )
        bstats = entry.get("baseStats") or {}
        if not bstats:
            return None

        def _to_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return default

        level = _to_int(p.get("level") or 50, 50)
        ivs = ivs if ivs is not None else (p.get("ivs") or {})
        evs = evs if evs is not None else (p.get("evs") or {})

        up = down = None
        nat = nature if nature is not None else p.get("nature")
        key_nat = str(nat or "").strip()
        key_norm = key_nat.lower().capitalize()
        data = NATURES_ES.get(key_nat) or NATURES_ES.get(key_norm)
        if data:
            _name, up_long, down_long = data
            map_short = {
                "attack": "atk",
                "special-attack": "spa",
                "defense": "def",
                "special-defense": "spd",
                "speed": "spe",
            }
            up = map_short.get(up_long)
            down = map_short.get(down_long)

        def _nature_mult(stat_key: str) -> float:
            if up and stat_key == up:
                return 1.1
            if down and stat_key == down:
                return 0.9
            return 1.0

        def calc_hp(base, iv, ev) -> int:
            return int(((2 * base + iv + ev // 4) * level) // 100 + level + 10)

        def calc_other(base, iv, ev, mult) -> int:
            val = int(((2 * base + iv + ev // 4) * level) // 100 + 5)
            return int(val * mult)

        res = {}
        for k in ("hp", "atk", "def", "spa", "spd", "spe"):
            b = _to_int(bstats.get(k), None)
            if b is None:
                continue
            iv = _to_int((ivs or {}).get(k), 0)
            ev = _to_int((evs or {}).get(k), 0)
            if k == "hp":
                res[k] = calc_hp(b, iv, ev)
            else:
                res[k] = calc_other(b, iv, ev, _nature_mult(k))
        return res if res else None
    except Exception:
        return None


def _base_stats_at_level(mon: dict) -> dict:
    zero = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}
    res = _calc_stats_from_base(mon, ivs=zero, evs=zero, nature=None)
    return res or {}


def _nature_mods(nature_val):
    try:
        key = str(nature_val or "").strip()
        key_norm = key.lower().capitalize()
        data = NATURES_ES.get(key) or NATURES_ES.get(key_norm)
        if not data:
            return None, None
        _name, up, down = data
        map_short = {
            "attack": "atk",
            "special-attack": "spa",
            "defense": "def",
            "special-defense": "spd",
            "speed": "spe",
        }
        return map_short.get(up), map_short.get(down)
    except Exception:
        return None, None
