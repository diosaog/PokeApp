"""Pokémon Showdown team text from PokeApp's own Pokémon projections.

Two projections, never mixed:

* ``private`` (the owner's current party, «Generar Poképaste»): species and
  form, nickname, gender, held item, ability, level, shiny, nature, the real
  six IVs and moves, with exactly 1 EV in every stat (owner rule; the save's
  EVs are never exported nor changed).
* ``public`` (an official Team Lock for Pokepast.es): only what PokeApp already
  shows every trainer: species and form, nickname, gender, held item, level,
  shiny and moves. Never ability, nature, IVs, EVs or a Hidden Power type.

Names come from save IDs through app/domain/showdown_names.py. Nothing is
invented: an ID without a known name is left out and reported as a warning.
This module only reads dictionaries; it never parses or writes saves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
import re
import unicodedata
from typing import Iterable, Literal, Mapping

from app.domain.showdown_names import DATA

Projection = Literal["private", "public"]
STATS = (("hp", "HP"), ("atk", "Atk"), ("defense", "Def"), ("spa", "SpA"), ("spd", "SpD"), ("spe", "Spe"))
EXPORT_EV = 1  # Owner rule: every exported stat has exactly one EV.
HIDDEN_POWER_TYPES = (
    "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel",
    "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark",
)
# Same accepted placeholders as the web catalog (web/src/pokemon/localization.ts),
# including the trusted projection's UTF-8-read-as-Latin-1 "PokÃ©mon".
_PREFIX = {
    "species": re.compile(r"^(?:pok(?:[eé]|Ã©)mon|species|especie)\s*#?\s*(\d+)$", re.I),
    "move": re.compile(r"^(?:move|movimiento)\s*#?\s*(\d+)$", re.I),
    "ability": re.compile(r"^(?:ability|habilidad)\s*#?\s*(\d+)$", re.I),
    "item": re.compile(r"^(?:item|objeto)\s*#?\s*(\d+)$", re.I),
    "nature": re.compile(r"^(?:nature|naturaleza)\s*#?\s*(\d+)$", re.I),
}
# Characters that would change the meaning of a Showdown set line.
_UNSAFE_NICKNAME = re.compile(r"[()@\[\]|\r\n]")
# Owner decision (2026-11-04): Gourgeist is exported as plain «Gourgeist» in
# both projections, without a size suffix. Showdown then simulates its default
# (Average) size, whose HP/Atk/Spe differ from Small/Large/Super; the real size
# stays in PokeApp and in the save. No other species is affected.
_PLAIN_SPECIES = frozenset({711})


@dataclass(frozen=True)
class ShowdownWarning:
    """Something the export could not represent; the caller shows it."""

    code: Literal[
        "egg_skipped",
        "species_unknown",
        "form_unknown",
        "form_unavailable",
        "nickname_unsupported",
        "item_unknown",
        "item_not_in_showdown",
        "ability_unknown",
        "nature_unknown",
        "move_unknown",
        "ivs_unavailable",
        "gender_unavailable",
        "level_unavailable",
    ]
    slot: int
    detail: str = ""


@dataclass(frozen=True)
class ShowdownExport:
    text: str
    count: int
    warnings: tuple[ShowdownWarning, ...] = field(default_factory=tuple)


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _ascii(text).lower())


def _ascii(text: str) -> str:
    text = str(text).replace("’", "'").replace("♀", "-F").replace("♂", "-M")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


@cache
def _reverse(category: str) -> dict[str, int | None]:
    """Name → ID for legacy projections that stored names; ambiguity → None."""
    tables = {
        "species": (DATA["species"], DATA["species_es"]),
        "move": (DATA["moves"],),
        "ability": (DATA["abilities"],),
        "item": (DATA["items"], DATA["items_english"]),
        "nature": (DATA["natures"],),
    }[category]
    index: dict[str, int | None] = {}
    for table in tables:
        for number, name in enumerate(table):
            if not name or (number == 0 and category != "nature"):
                continue
            key = to_id(name)
            index[key] = number if index.get(key, number) == number else None
    return index


def _identify(category: str, value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = _PREFIX[category].match(text)
    if match:
        return int(match.group(1))
    return _reverse(category).get(to_id(text))


def _named(table: list, number: int | None) -> str | None:
    if number is None or not 0 <= number < len(table):
        return None
    return table[number] or None


def _gender(value) -> str | None:
    text = str(value).strip().lower() if value is not None else ""
    return {
        "m": "M", "male": "M", "♂": "M", "0": "M",
        "f": "F", "female": "F", "♀": "F", "1": "F",
        "n": "N", "genderless": "N", "2": "N",
    }.get(text)


def _species(pokemon: Mapping, generation: int, slot: int, warnings: list) -> tuple[str, str] | None:
    number = _identify("species", pokemon.get("species"))
    base = _named(DATA["species"], number)
    if base is None:
        warnings.append(ShowdownWarning("species_unknown", slot, str(pokemon.get("species") or "")))
        return None
    if number in _PLAIN_SPECIES:
        return base, base
    form = pokemon.get("form")
    if form is None:
        form = pokemon.get("form_index")
    name = base
    if isinstance(form, int) and not isinstance(form, bool) and form > 0:
        options = DATA["forms"].get(str(number), {}).get(str(generation if generation in (6, 7) else 7), [])
        name = options[form] if form < len(options) and options[form] else None
        if name is None:
            warnings.append(ShowdownWarning("form_unknown", slot, f"{base} #{form}"))
            name = base
    elif isinstance(form, int) and form == 0:
        options = DATA["forms"].get(str(number), {}).get(str(generation if generation in (6, 7) else 7), [])
        # Some species' form 0 is a named forme (e.g. Vivillon-Icy Snow).
        name = options[0] if options and options[0] else base
    elif form is None and len({f for f in DATA["forms"].get(str(number), {}).get("7", []) if f}) > 1:
        # Older projections did not keep the form: say so, never guess one.
        warnings.append(ShowdownWarning("form_unavailable", slot, base))
    return base, name


def _nickname(pokemon: Mapping, number_names: Iterable[str], slot: int, warnings: list) -> str:
    nickname = " ".join(str(pokemon.get("nickname") or "").split())
    # The game's default name (any case, accents or apostrophe style) is not
    # a nickname; any other spelling is the player's.
    default = {" ".join(_ascii(n).lower().split()) for n in number_names if n}
    if not nickname or " ".join(_ascii(nickname).lower().split()) in default:
        return ""
    if _UNSAFE_NICKNAME.search(nickname):
        warnings.append(ShowdownWarning("nickname_unsupported", slot, nickname))
        return ""
    return nickname


def _hidden_power(ivs: Mapping) -> str:
    bits = [ivs[k] & 1 for k in ("hp", "atk", "defense", "spe", "spa", "spd")]
    return HIDDEN_POWER_TYPES[sum(b << i for i, b in enumerate(bits)) * 15 // 63]


def _valid_ivs(ivs) -> dict[str, int] | None:
    if not isinstance(ivs, Mapping):
        return None
    out = {}
    for key, _ in STATS:
        value = ivs.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 31:
            return None
        out[key] = value
    return out


def format_set(pokemon: Mapping, *, generation: int, projection: Projection, slot: int,
               warnings: list[ShowdownWarning]) -> str | None:
    """One Showdown set, or None when the Pokémon cannot be represented."""
    if pokemon.get("is_egg") is True:
        warnings.append(ShowdownWarning("egg_skipped", slot))
        return None
    identified = _species(pokemon, generation, slot, warnings)
    if identified is None:
        return None
    base, species = identified
    number = _identify("species", pokemon.get("species"))
    nickname = _nickname(
        pokemon,
        (base, species, _named(DATA["species_es"], number) or ""),
        slot,
        warnings,
    )
    line = f"{nickname} ({species})" if nickname else species
    gender = _gender(pokemon.get("gender"))
    fixed = DATA["fixed_gender"].get(species) or DATA["fixed_gender"].get(base)
    if fixed is None:
        if gender in ("M", "F"):
            line += f" ({gender})"
        elif gender is None and projection == "private":
            warnings.append(ShowdownWarning("gender_unavailable", slot, species))
    item_value = pokemon.get("item")
    if item_value:
        item_id = _identify("item", item_value)
        generation_of_item = pokemon.get("item_generation")
        if generation_of_item == 3:
            item_id = None  # Gen 3 item table: no Showdown mapping here
        shown = _named(DATA["items"], item_id)
        english = _named(DATA["items_english"], item_id)
        if shown:
            line += f" @ {shown}"
        elif english and projection == "public":
            line += f" @ {english}"
        elif english:
            warnings.append(ShowdownWarning("item_not_in_showdown", slot, english))
        else:
            warnings.append(ShowdownWarning("item_unknown", slot, str(item_value)))
    lines = [line]
    if projection == "private":
        ability = _named(DATA["abilities"], _identify("ability", pokemon.get("ability")))
        if ability:
            lines.append(f"Ability: {ability}")
        elif pokemon.get("ability"):
            warnings.append(ShowdownWarning("ability_unknown", slot, str(pokemon.get("ability"))))
    level = pokemon.get("level")
    if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 100:
        lines.append(f"Level: {level}")
    else:
        warnings.append(ShowdownWarning("level_unavailable", slot, species))
    if pokemon.get("is_shiny") is True:
        lines.append("Shiny: Yes")
    ivs = None
    if projection == "private":
        lines.append("EVs: " + " / ".join(f"{EXPORT_EV} {label}" for _, label in STATS))
        nature = _named(DATA["natures"], _identify("nature", pokemon.get("nature")))
        if nature:
            lines.append(f"{nature} Nature")
        elif pokemon.get("nature"):
            warnings.append(ShowdownWarning("nature_unknown", slot, str(pokemon.get("nature"))))
        ivs = _valid_ivs(pokemon.get("ivs"))
        if ivs is None:
            warnings.append(ShowdownWarning("ivs_unavailable", slot, species))
        else:
            lines.append("IVs: " + " / ".join(f"{ivs[key]} {label}" for key, label in STATS))
    for move in list(pokemon.get("moves") or [])[:4]:
        raw = move.get("name") if isinstance(move, Mapping) else move
        if raw is None and isinstance(move, Mapping):
            raw = move.get("move_id")
        name = _named(DATA["moves"], _identify("move", raw))
        if not name:
            if raw not in (None, "", 0):
                warnings.append(ShowdownWarning("move_unknown", slot, str(raw)))
            continue
        if name == "Hidden Power" and ivs is not None:
            name = f"Hidden Power [{_hidden_power(ivs)}]"
        lines.append(f"- {name}")
    return "\n".join(lines)


def public_names(pokemon: Mapping, generation: int | None = None) -> dict[str, str | None]:
    """English species (with form) and held-item names of a public Pokémon,
    or None where its ID has no known name. Used for public announcements."""
    identified = _species(pokemon, generation or 7, 0, [])
    item_id = _identify("item", pokemon.get("item")) if pokemon.get("item") else None
    return {
        "species": identified[1] if identified else None,
        "item": _named(DATA["items"], item_id) or _named(DATA["items_english"], item_id),
    }


def export_team(team: Iterable[Mapping], *, generation: int, projection: Projection) -> ShowdownExport:
    """The importable text of up to six Pokémon, in the given order."""
    if projection not in ("private", "public"):
        raise ValueError("unknown_projection")
    warnings: list[ShowdownWarning] = []
    sets = []
    for slot, pokemon in enumerate(list(team)[:6], 1):
        text = format_set(pokemon, generation=generation, projection=projection, slot=slot, warnings=warnings)
        if text:
            sets.append(text)
    return ShowdownExport(
        text="\n\n".join(sets) + ("\n" if sets else ""),
        count=len(sets),
        warnings=tuple(warnings),
    )
