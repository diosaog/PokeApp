"""Build app/domain/showdown_names.py: save IDs → Pokémon Showdown names.

Sources (read as data, never executed):
  * Showdown's published tables, downloaded to --showdown:
      pokedex.json, moves.json, items.js, abilities.js
    from https://play.pokemonshowdown.com/data/
  * web/src/pokemon/catalog.es.json (PKHeX.Core English/Spanish names, the
    same ID space the server parser emits).

Every Showdown name is taken from Showdown's own table by its in-game number
(`num`) and cross-checked against PKHeX's English name for that ID; the build
fails on any unexplained disagreement. Names are normalised to ASCII so that
Showdown's importer (toID drops non [a-z0-9]) resolves them: "Flabébé" →
"Flabebe", "King’s Rock" → "King's Rock". Forms follow Showdown's formeOrder
(the games' internal form numbers); battle-only, Mega/Primal/Totem/Gigantamax
and post-Gen-7 formes can never be stored in a Gen 6/7 save and are null.

    python -m tools.build_showdown_names --showdown <dir> [--check]
"""

from __future__ import annotations

import argparse
import json
import pprint
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "web/src/pokemon/catalog.es.json"
# A Python module, not JSON: the API deploy bundle ships app/**/*.py only.
OUTPUT = ROOT / "app/domain/showdown_names.py"
MAX = {"species": 807, "move": 728, "ability": 233, "item": 959}
# Forme suffixes that never exist outside a battle or outside Gen 6/7 games.
UNSTORABLE = re.compile(
    r"(^|-)(Mega(-[XY])?|Primal|Gmax|Totem|Galar|Hisui|Paldea|Eternamax|Starter|World)($|-)"
)
# ORAS stored Cosplay Pikachu as forms 1-6; later games reuse those numbers.
GEN6_PIKACHU = [
    "Pikachu",
    "Pikachu-Rock-Star",
    "Pikachu-Belle",
    "Pikachu-Pop-Star",
    "Pikachu-PhD",
    "Pikachu-Libre",
    "Pikachu-Cosplay",
]
# Same ID, a name Showdown spells differently; each verified by hand.
ITEM_ALIASES = {
    137: "Mail",  # PKHeX "Greet Mail": Showdown's generic Mail
    259: "Stick",  # Gen 2-7 name; "Leek" (Gen 8+) is rejected in Gen 6 formats
}


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def ascii_name(text: str) -> str:
    text = text.replace("’", "'").replace("♀", "-F").replace("♂", "-M")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def js_entries(path: Path) -> dict[str, dict]:
    """Top-level `key:{name:"…",num:N,gen:G}` of a Showdown .js table, by text."""
    text = path.read_text(encoding="utf-8")
    i, depth, quote, key_start, entries = text.index("{") + 1, 0, None, None, {}
    key_start = i
    body_start = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "{":
            if depth == 0:
                body_start = i
                key = text[key_start:i].strip().strip(",").rstrip(":").strip()
            depth += 1
        elif c == "}":
            if depth == 0:
                break
            depth -= 1
            if depth == 0:
                entries[key] = _fields(text[body_start + 1 : i])
                key_start = i + 1
        i += 1
    return entries


def _fields(body: str) -> dict:
    flat, depth, quote = [], 0, None
    for c in body:
        if quote:
            if c == quote:
                quote = None
            if depth == 0:
                flat.append(c)
            continue
        if c in "\"'":
            quote = c
        if c == "{":
            depth += 1
        if depth == 0:
            flat.append(c)
        if c == "}":
            depth -= 1
    flat_text = "".join(flat)
    out = {}
    for field, pattern, cast in (
        ("name", r'(?:^|,)name:"([^"]*)"', str),
        ("num", r"(?:^|,)num:(-?\d+)", int),
        ("gen", r"(?:^|,)gen:(\d+)", int),
    ):
        match = re.search(pattern, flat_text)
        if match:
            out[field] = cast(match.group(1))
    return out


def by_number(entries, top, label, pkhex, aliases=None):
    """ID → Showdown name, verified against PKHeX's English name for that ID."""
    aliases = aliases or {}
    found: dict[int, list[dict]] = {}
    for entry in entries:
        num = entry.get("num")
        if entry.get("name") and isinstance(num, int) and 0 < num <= top:
            found.setdefault(num, []).append(entry)
    names: list[str | None] = [None] * (top + 1)
    for num, options in found.items():
        # The newest spelling up to Gen 7: Gen 3 berries over their Gen 2
        # names, never a Gen 8+ rename of the same ID.
        options.sort(key=lambda e: (e.get("gen", 3) > 7, -e.get("gen", 3)))
        name = aliases.get(num, options[0]["name"])
        expected = pkhex[num]
        if num not in aliases and to_id(ascii_name(expected)) != to_id(
            ascii_name(name)
        ):
            raise SystemExit(f"{label} {num}: Showdown {name!r} ≠ PKHeX {expected!r}")
        names[num] = ascii_name(name)
    return names


def build(showdown: Path) -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["categories"]
    dex = json.loads((showdown / "pokedex.json").read_text(encoding="utf-8"))
    moves = json.loads((showdown / "moves.json").read_text(encoding="utf-8"))
    items = js_entries(showdown / "items.js")
    abilities = js_entries(showdown / "abilities.js")
    pkhex = {k: catalog[k]["en"] for k in ("species", "move", "ability", "item")}

    bases = {
        v["num"]: v
        for v in dex.values()
        if v.get("num", 0) > 0 and not v.get("forme")
    }
    resolvable = {to_id(ascii_name(v["name"])) for v in dex.values()}
    cosmetic = {
        to_id(ascii_name(name))
        for v in dex.values()
        for name in v.get("cosmeticFormes") or []
    }
    species: list[str | None] = [None] * (MAX["species"] + 1)
    forms: dict[str, dict[str, list[str | None]]] = {}
    fixed_gender: dict[str, str] = {}
    for num in range(1, MAX["species"] + 1):
        base = bases[num]
        name = ascii_name(base["name"])
        expected = ascii_name(pkhex["species"][num])
        if to_id(name) != to_id(expected):
            raise SystemExit(f"species {num}: Showdown {name!r} ≠ PKHeX {expected!r}")
        species[num] = name
        order = base.get("formeOrder") or []
        if len(order) > 1:
            entries = []
            for forme in order:
                key = to_id(ascii_name(forme))
                entry = next(
                    (v for v in dex.values() if to_id(ascii_name(v["name"])) == key),
                    None,
                )
                suffix = forme[len(base["name"]) + 1 :] if forme != base["name"] else ""
                storable = (
                    not UNSTORABLE.search(suffix)
                    and not (entry or {}).get("battleOnly")
                    and (entry or {}).get("gen", 7) <= 7
                    and (key in resolvable or key in cosmetic)
                )
                entries.append(ascii_name(forme) if storable else None)
            gen6 = [
                None
                if value is None or "Alola" in value or value.endswith("-Bond")
                else value
                for value in entries
            ]
            if num == 25:
                gen6 = list(GEN6_PIKACHU)
                entries = [e if e not in GEN6_PIKACHU[1:] else None for e in entries]
            forms[str(num)] = {"6": gen6, "7": entries}
    for value in dex.values():
        if value.get("num", 0) > 0 and value.get("gender") in ("M", "F", "N"):
            fixed_gender[ascii_name(value["name"])] = value["gender"]

    move_names = by_number(
        (dict(v, gen=v.get("gen", 3)) for v in moves.values() if not v.get("isZ") and not v.get("isMax")),
        MAX["move"],
        "move",
        pkhex["move"],
    )
    # Z-Moves only exist inside a battle: never in a stored move slot.
    ability_names = by_number(
        abilities.values(), MAX["ability"], "ability", pkhex["ability"]
    )
    item_names = by_number(items.values(), MAX["item"], "item", pkhex["item"], ITEM_ALIASES)
    english_items = [
        None
        if not n or n in ("???", "None") or index == 0
        else ascii_name(n)
        for index, n in enumerate(pkhex["item"][: MAX["item"] + 1])
    ]
    natures = [ascii_name(n) for n in catalog["nature"]["en"][:25]]
    spanish_species = [
        "" if not n else ascii_name(n) for n in catalog["species"]["es"][: MAX["species"] + 1]
    ]
    z_moves = {to_id(ascii_name(v["name"])) for v in moves.values() if v.get("isZ")}
    for table, label in (
        (species, "species"),
        (move_names, "move"),
        (ability_names, "ability"),
    ):
        missing = [i for i in range(1, len(table)) if table[i] is None]
        if label == "move":
            # Only Z-Moves (battle-only, never stored in a move slot) may lack
            # a name; PKHeX lists each twice (physical/special).
            missing = [
                i for i in missing if to_id(ascii_name(pkhex["move"][i])) not in z_moves
            ]
        if missing:
            raise SystemExit(f"{label}: no Showdown name for {missing[:10]}")
    return {
        "schema": 1,
        "sources": {
            "showdown": "https://play.pokemonshowdown.com/data/ (pokedex.json, moves.json, items.js, abilities.js)",
            "retrieved": date.today().isoformat(),
            "catalog": "web/src/pokemon/catalog.es.json",
        },
        "species": species,
        "species_es": spanish_species,
        "forms": forms,
        "fixed_gender": dict(sorted(fixed_gender.items())),
        "moves": move_names,
        "abilities": ability_names,
        "items": item_names,
        "items_english": english_items,
        "natures": natures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showdown", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = build(args.showdown)
    body = pprint.pformat(data, width=100, compact=True, sort_dicts=False)
    header = (
        '"""Generated by tools/build_showdown_names.py; do not edit by hand.\n\n'
        "Save IDs (species, form, move, ability, item, nature) to the names\n"
        "Pokemon Showdown imports, verified against Showdown's own tables and\n"
        'the web catalog\'s English names. Regenerate when either changes."""\n\n'
    )
    args.output.write_text(f"{header}DATA = {body}\n", encoding="utf-8")
    known = sum(1 for n in data["items"] if n)
    print(
        f"species={sum(1 for n in data['species'] if n)} forms={len(data['forms'])}"
        f" moves={sum(1 for n in data['moves'] if n)} abilities={sum(1 for n in data['abilities'] if n)}"
        f" items(showdown)={known} items(english)={sum(1 for n in data['items_english'] if n)}"
        f" -> {args.output}"
    )


if __name__ == "__main__":
    main()
