from __future__ import annotations
import json
import hashlib


def _fingerprint_base(p: dict, *, include_level: bool) -> str:
    dex = p.get("dex_id") or 0
    spn = (p.get("species_name") or p.get("species") or "").strip()
    tid = p.get("ot_tid") or 0
    sid = p.get("ot_sid") or 0
    gen = (p.get("gender") or "").strip()
    shiny = bool(p.get("is_shiny", False))
    form = p.get("form_index") or 0
    lvl = p.get("level") or 0
    base = [int(dex), spn, int(tid), int(sid), gen, 1 if shiny else 0, int(form)]
    if include_level:
        base.append(int(lvl))
    raw = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def pokemon_fingerprint(p: dict) -> str:
    """Legacy fingerprint (includes level)."""
    return _fingerprint_base(p, include_level=True)


def pokemon_fingerprint_stable(p: dict) -> str:
    """Stable fingerprint (excludes level)."""
    return _fingerprint_base(p, include_level=False)
