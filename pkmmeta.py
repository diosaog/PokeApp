from __future__ import annotations
import json
import hashlib

def pokemon_fingerprint(p: dict) -> str:
    """Huella estable del Pokémon basada en campos disponibles del bridge."""
    dex = p.get('dex_id') or 0
    spn = (p.get('species_name') or p.get('species') or '').strip()
    tid = p.get('ot_tid') or 0
    sid = p.get('ot_sid') or 0
    gen = (p.get('gender') or '').strip()
    shiny = bool(p.get('is_shiny', False))
    form = p.get('form_index') or 0
    lvl = p.get('level') or 0
    base = [int(dex), spn, int(tid), int(sid), gen, 1 if shiny else 0, int(form), int(lvl)]
    raw = json.dumps(base, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()



