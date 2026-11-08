"""Comparison rules of Administración › Avisos: suspicion and facts, never a verdict.

Two successive accepted saves of one trainer and the server's own record of
authorized operations go in; notices for the administrator come out. Nothing
here writes a save, blocks anyone or touches points, coins or Team Lock, and
no change is ever called proven cheating: comparing saves cannot prove where a
change came from. An external edit that produces exactly what a legitimate
action produces is indistinguishable, and a game mechanic not modelled here
looks unexplained. Randomized games are expected, so official legality is
never used as truth and pre-existing attributes are never judged.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.domain.pokemon_evolutions import EVOLUTIONS
from app.domain.unlimited_items import UNLIMITED_ITEMS

DETECTOR_VERSION = 1

STATS = ("hp", "atk", "defense", "spa", "spd", "spe")
STAT_LABELS = {
    "hp": "PS",
    "atk": "Ataque",
    "defense": "Defensa",
    "spa": "At. Esp.",
    "spd": "Def. Esp.",
    "spe": "Velocidad",
}
SEVERITY_RANK = {"baja": 0, "media": 1, "alta": 2}

# Free and unlimited by owner decision, with no server record: never a notice.
UNLIMITED_ITEM_IDS = frozenset(item["item_id"] for item in UNLIMITED_ITEMS)
ABILITY_CAPSULE = 645
# Objects in the bag's own "key" pouch are story progress, not competitive gain.
IGNORED_POUCHES = frozenset({"KeyItems"})
# Medicine pouch objects that are worth a notice on their own.
WATCHED_MEDICINE = frozenset({44, 45, 46, 47, 48, 49, 51, 52, 53})  # Ceniza Sagrada, vitaminas, Más PP / PP Máximos
# Common objects a normal game hands out constantly (ids from the game's item
# table): Poké Balls except Master/Gloria, curas y Pociones, Repelentes, Cuerda
# Huida, Miel, objetos para vender, plumas y abonos. They only count when they
# jump absurdly.
ORDINARY_ITEMS = frozenset(
    {
        *range(2, 16),
        *range(492, 500),
        576,
        851,
        *range(17, 44),
        54,
        63, 64, *range(65, 76),
        76, 77, 78, 79,
        *range(86, 93),
        94, 95, 96, 97, 98, 106,
        *range(565, 572),
        580, 581, 582, 583,
    }
)  # fmt: skip
BULK_UNITS = 100
BULK_RECORDS = 10

MAX_EV = {3: 255, 4: 255, 5: 255, 6: 252, 7: 252}
MAX_EV_TOTAL = 510
EV_JUMP = 200
FRIENDSHIP_JUMP = 100
MAX_FRIENDSHIP = 255
MOVES_AT_ONCE = 3

# Species whose form legitimately changes in play (items, tutors, fusion,
# seasons, cells). Any other form change has no known mechanic behind it.
FORM_CHANGE_SPECIES = frozenset(
    {386, 412, 479, 487, 492, 493, 585, 586, 641, 642, 645, 646, 647, 648, 649,
     658, 676, 716, 718, 720, 741, 773, 774, 800}
)  # fmt: skip

_ID = re.compile(r"#\s*(\d+)\s*$")
_GAME_RECORD_GUARDS = (
    "ot_name",
    "ot_tid",
    "ot_sid",
    "ot_gender",
    "origin_version",
    "language",
    "met_location",
    "met_level",
    "met_date",
    "egg_location",
    "egg_date",
)
_GUARD_LABELS = {
    "ot_name": "Entrenador original",
    "ot_tid": "ID del entrenador original",
    "ot_sid": "ID secreto del entrenador original",
    "ot_gender": "Sexo del entrenador original",
    "origin_version": "Juego de origen",
    "language": "Idioma de origen",
    "met_location": "Lugar de encuentro",
    "met_level": "Nivel de encuentro",
    "met_date": "Fecha de encuentro",
    "egg_location": "Lugar del huevo",
    "egg_date": "Fecha del huevo",
}
NO_PROOF = (
    "Comparar partidas no prueba el origen: un cambio externo que deje el mismo "
    "resultado que una acción legítima no se puede distinguir."
)


def _id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = _ID.search(value)
        return int(match[1]) if match else None
    return None


def _time(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return None


def standard_evolution(origin, target) -> bool:
    """Whether `target` is reached from `origin` through standard evolutions."""
    seen = set()
    frontier = list(EVOLUTIONS.get(origin, ()))
    while frontier:
        species = frontier.pop()
        if species == target:
            return True
        if species not in seen:
            seen.add(species)
            frontier.extend(EVOLUTIONS.get(species, ()))
    return False


@dataclass(frozen=True)
class Slot:
    key: str
    source: str
    box: int
    slot: int
    species: int | None
    form: int | None
    nickname: str
    level: int | None
    gender: str | None
    shiny: bool | None
    is_egg: bool
    ability: int | None
    nature: int | None
    item: int | None
    moves: tuple[int, ...] | None
    ivs: dict | None
    evs: dict | None
    evidence: dict

    @property
    def place(self) -> dict:
        return {"source": self.source, "box": self.box, "slot": self.slot}

    @property
    def generation(self) -> int:
        fmt = self.evidence.get("format")
        return fmt if isinstance(fmt, int) else 0


def identity_key(evidence):
    """Persistent identifiers only: never species, slot or mutable facts."""
    pid = evidence.get("pid")
    if not isinstance(pid, int):
        return None
    ec = evidence.get("encryption_constant")
    if ec is not None:
        return f"{pid}:{ec}"
    return f"{pid}:{evidence.get('ot_tid')}:{evidence.get('ot_sid')}"


def _stats(value):
    if not isinstance(value, dict) or any(not isinstance(value.get(s), int) for s in STATS):
        return None
    return {s: value[s] for s in STATS}


def _slot(pokemon, source, box, number):
    if not isinstance(pokemon, dict):
        return None
    evidence = pokemon.get("identity_evidence")
    if not isinstance(evidence, dict):
        return None
    key = identity_key(evidence)
    if key is None:
        return None
    moves = pokemon.get("moves")
    return Slot(
        key=key,
        source=source,
        box=box,
        slot=number,
        species=_id(pokemon.get("species")),
        form=pokemon.get("form") if isinstance(pokemon.get("form"), int) else None,
        nickname=str(pokemon.get("nickname") or ""),
        level=pokemon.get("level") if isinstance(pokemon.get("level"), int) else None,
        gender=pokemon.get("gender") if isinstance(pokemon.get("gender"), str) else None,
        shiny=pokemon.get("is_shiny") if isinstance(pokemon.get("is_shiny"), bool) else None,
        is_egg=pokemon.get("is_egg") is True or evidence.get("is_egg") is True,
        ability=_id(pokemon.get("ability")),
        nature=_id(pokemon.get("nature")),
        item=_id(pokemon.get("item")),
        moves=tuple(m for m in (_id(entry.get("name")) for entry in moves if isinstance(entry, dict)) if m)
        if isinstance(moves, list)
        else None,
        ivs=_stats(pokemon.get("ivs")),
        evs=_stats(pokemon.get("evs")),
        evidence=evidence,
    )


def slots(payload) -> list[Slot]:
    found = []
    for entry in payload.get("party") or []:
        found.append(_slot(entry.get("pokemon"), "party", 0, entry.get("slot_number")))
    for box in payload.get("boxes") or []:
        for entry in box.get("slots") or []:
            found.append(_slot(entry.get("pokemon"), "box", box.get("box_number"), entry.get("slot_number")))
    return [slot for slot in found if slot is not None]


def _change(field, label, kind, before, after, severity, reason, **extra):
    return {
        "field": field,
        "label": label,
        "kind": kind,
        "before": before,
        "after": after,
        "severity": severity,
        "reason": reason,
        **extra,
    }


def _worst(changes):
    return max((c["severity"] for c in changes), key=SEVERITY_RANK.__getitem__)


def _training_ops(operations, start, end):
    by_key = defaultdict(list)
    for op in operations.get("training") or ():
        finished = _time(op.get("finished_at"))
        if finished is None or finished > end or (start is not None and finished <= start):
            continue
        key = identity_key({"pid": op.get("pid"), "encryption_constant": op.get("ec")})
        if key:
            by_key[key].append(op)
    for ops in by_key.values():
        ops.sort(key=lambda op: _time(op["finished_at"]))
    return by_key


TRAINING_LABELS = {
    "menta_naturaleza": "Menta (naturaleza)",
    "chapa_plateada": "Chapa Plateada",
    "chapa_dorada": "Chapa Dorada",
}


def _training_notes(ops):
    return [
        {
            "kind": "training",
            "label": TRAINING_LABELS.get(op.get("item_code"), "Entrenamiento virtual"),
            "at": op.get("finished_at"),
            "detail": _training_detail(op),
        }
        for op in ops
    ]


def _training_detail(op):
    code = op.get("item_code")
    if code == "chapa_plateada":
        return f"IV de {STAT_LABELS.get(op.get('stat'), 'una estadística')} a 31, auditado por PokeApp."
    if code == "chapa_dorada":
        return "Los seis IVs a 31, auditado por PokeApp."
    return "Cambio de naturaleza auditado por PokeApp."


def _expected_after_training(before, ops):
    """Apply the audited operations, in order, to the previous observed values."""
    ivs = dict(before.ivs) if before.ivs else None
    nature = before.nature
    for op in ops:
        code = op.get("item_code")
        if code == "chapa_dorada" and ivs is not None:
            ivs = {s: 31 for s in STATS}
        elif code == "chapa_plateada" and ivs is not None and op.get("stat") in ivs:
            ivs[op["stat"]] = 31
        elif code == "menta_naturaleza" and op.get("nature_id") is not None:
            nature = int(op["nature_id"])
    return ivs, nature


def _compare_pokemon(before: Slot, after: Slot, ops, *, facts) -> list[dict]:
    """Field-level unexplained changes of one Pokémon present in both saves."""
    changes: list[dict] = []
    expected_ivs, expected_nature = _expected_after_training(before, ops)
    species_changed = (
        before.species is not None and after.species is not None and before.species != after.species
    )
    form_changed = before.form is not None and after.form is not None and before.form != after.form
    level_up = after.level is not None and before.level is not None and after.level > before.level

    # IVs: no in-game mechanic of these games rewrites the stored value
    # (Hyper Training leaves it untouched).
    if expected_ivs and after.ivs:
        for stat in STATS:
            if after.ivs[stat] != expected_ivs[stat]:
                changes.append(
                    _change(
                        f"iv_{stat}",
                        f"IV de {STAT_LABELS[stat]}",
                        "iv",
                        before.ivs[stat],
                        after.ivs[stat],
                        "alta",
                        "Los IVs reales no cambian jugando y no consta ninguna Chapa aplicada "
                        "por PokeApp que lo explique.",
                    )
                )
    if expected_nature is not None and after.nature is not None and after.nature != expected_nature:
        changes.append(
            _change(
                "nature",
                "Naturaleza",
                "nature",
                _ref("Nature", before.nature),
                _ref("Nature", after.nature),
                "alta",
                "La naturaleza no cambia jugando y no consta ninguna Menta aplicada por PokeApp.",
            )
        )
    if before.ability is not None and after.ability is not None and before.ability != after.ability:
        # An evolution or form change legitimately changes the ability slot's
        # value; a Capsule is visible because the bag holds one less.
        capsule_used = (
            facts.bag_known and facts.bag_before.get(ABILITY_CAPSULE, 0) > facts.bag_after.get(ABILITY_CAPSULE, 0)
        )
        if not (species_changed or form_changed or capsule_used):
            changes.append(
                _change(
                    "ability",
                    "Habilidad",
                    "ability",
                    _ref("Ability", before.ability),
                    _ref("Ability", after.ability),
                    "alta" if facts.bag_known else "media",
                    "La habilidad cambió sin evolución ni cambio de forma, y sin que se haya gastado una "
                    "Cápsula Habilidad."
                    if facts.bag_known
                    else "La habilidad cambió sin evolución ni cambio de forma; no se pudo comprobar si se "
                    "gastó una Cápsula Habilidad.",
                )
            )
    if species_changed and not standard_evolution(before.species, after.species):
        reverse = standard_evolution(after.species, before.species)
        changes.append(
            _change(
                "species",
                "Especie",
                "species",
                _ref("Pokémon", before.species),
                _ref("Pokémon", after.species),
                "media" if reverse else "baja",
                "La especie ha retrocedido a una fase anterior de su evolución." if reverse
                else "El cambio de especie no coincide con las evoluciones estándar; en una partida "
                "aleatorizada puede ser legítimo.",
            )
        )
    if (
        form_changed
        and not species_changed
        and after.species not in FORM_CHANGE_SPECIES
    ):
        changes.append(
            _change(
                "form",
                "Forma",
                "text",
                before.form,
                after.form,
                "media",
                "La forma cambió en una especie sin mecánica conocida para cambiarla.",
            )
        )
    if (
        before.gender is not None
        and after.gender is not None
        and before.gender != after.gender
        and (after.generation >= 6 or not species_changed)
    ):
        changes.append(
            _change(
                "gender",
                "Sexo",
                "text",
                before.gender,
                after.gender,
                "alta",
                "El sexo de un Pokémon no cambia jugando.",
            )
        )
    if before.shiny is not None and after.shiny is not None and before.shiny != after.shiny:
        changes.append(
            _change(
                "shiny",
                "Shiny",
                "bool",
                before.shiny,
                after.shiny,
                "alta",
                "El estado shiny depende de identificadores que no cambian jugando.",
            )
        )
    if not before.is_egg:
        for name in _GAME_RECORD_GUARDS:
            old = before.evidence.get(name)
            new = after.evidence.get(name)
            if old is not None and new is not None and old != new:
                changes.append(
                    _change(
                        f"origin_{name}",
                        _GUARD_LABELS[name],
                        "text",
                        old,
                        new,
                        "alta",
                        "Es un dato de origen del Pokémon y no cambia jugando.",
                    )
                )
    if before.is_egg is False and after.is_egg is True:
        changes.append(
            _change(
                "egg",
                "Huevo",
                "bool",
                False,
                True,
                "alta",
                "Un Pokémon ya nacido no vuelve a ser un huevo.",
            )
        )
    if before.level is not None and after.level is not None and after.level < before.level:
        changes.append(
            _change(
                "level",
                "Nivel",
                "int",
                before.level,
                after.level,
                "media",
                "El nivel ha bajado, algo que no ocurre jugando; también puede deberse a volver a una "
                "copia antigua de la partida.",
            )
        )
    if before.evs and after.evs:
        limit = MAX_EV.get(after.generation, 255)
        before_total, after_total = sum(before.evs.values()), sum(after.evs.values())
        gained = sum(max(0, after.evs[s] - before.evs[s]) for s in STATS)
        over = [s for s in STATS if after.evs[s] > limit and after.evs[s] > before.evs[s]]
        if over:
            changes.extend(
                _change(
                    f"ev_{s}",
                    f"EV de {STAT_LABELS[s]}",
                    "ev",
                    before.evs[s],
                    after.evs[s],
                    "alta",
                    f"Supera el máximo de {limit} EVs por estadística que permite el juego.",
                )
                for s in over
            )
        if after_total > MAX_EV_TOTAL and after_total > before_total:
            changes.append(
                _change(
                    "ev_total",
                    "EVs totales",
                    "int",
                    before_total,
                    after_total,
                    "alta",
                    f"Supera el máximo de {MAX_EV_TOTAL} EVs totales que permite el juego.",
                )
            )
        elif gained >= EV_JUMP and not level_up and not over:
            changes.append(
                _change(
                    "ev_jump",
                    "EVs ganados",
                    "int",
                    before_total,
                    after_total,
                    "baja",
                    "Aumento muy grande de EVs sin subir de nivel; podría ser entrenamiento intensivo.",
                )
            )
    if before.moves is not None and after.moves is not None and not species_changed and not level_up:
        replaced = len(set(after.moves) - set(before.moves))
        if replaced >= MOVES_AT_ONCE:
            changes.append(
                _change(
                    "moves",
                    "Movimientos",
                    "moves",
                    [_ref("Move", m) for m in before.moves],
                    [_ref("Move", m) for m in after.moves],
                    "baja",
                    f"Cambiaron {replaced} movimientos de una vez sin subir de nivel; las MT y el "
                    "Recordador de Movimientos también lo explican.",
                )
            )
    if facts.friendship_known and after.key in facts.friendship_before and after.key in facts.friendship_after:
        old, new = facts.friendship_before[after.key], facts.friendship_after[after.key]
        # 255 is exactly what the free «Felicidad máxima» of the Launcher leaves.
        if new != MAX_FRIENDSHIP and new - old >= FRIENDSHIP_JUMP:
            changes.append(
                _change(
                    "friendship",
                    "Felicidad",
                    "int",
                    old,
                    new,
                    "baja",
                    "Subida muy grande de felicidad sin explicación registrada; el juego la sube poco a poco.",
                )
            )
    return changes


def _ref(prefix, value):
    return f"{prefix} #{value}" if value is not None else None


def _title(changes):
    ivs = [c for c in changes if c["field"].startswith("iv_")]
    if len(ivs) == 6 and all(c["after"] == 31 for c in ivs):
        return "Los seis IVs han pasado a 31"
    if ivs and len(ivs) == len(changes):
        return f"{len(ivs)} IV modificado" + ("s" if len(ivs) != 1 else "")
    if len(changes) == 1:
        return f"{changes[0]['label']} modificada" if changes[0]["label"] in ("Habilidad", "Naturaleza", "Especie", "Forma") else f"{changes[0]['label']} modificado"
    return "Varios atributos modificados"


def _view(after: Slot, before: Slot | None = None):
    moved = before is not None and (before.source, before.box, before.slot) != (after.source, after.box, after.slot)
    return {
        "key": after.key,
        "species": _ref("Pokémon", after.species) or "Especie desconocida",
        "form": after.form,
        "nickname": after.nickname,
        "level": after.level,
        "gender": after.gender,
        "shiny": bool(after.shiny),
        "is_egg": after.is_egg,
        "location": after.place,
        "previous_location": before.place if moved else None,
        "previous_species": _ref("Pokémon", before.species)
        if before is not None and before.species != after.species
        else None,
        "item": _ref("Item", after.item),
    }


@dataclass(frozen=True)
class _Facts:
    bag_known: bool
    bag_before: dict
    bag_after: dict
    friendship_known: bool
    friendship_before: dict
    friendship_after: dict


def _pokemon_notice(before, after, changes, ops):
    return {
        "group_key": f"pokemon:{after.key}",
        "category": "pokemon",
        "severity": _worst(changes),
        "title": _title(changes),
        "summary": changes[0]["reason"] + " " + NO_PROOF,
        "origin": "desconocido",
        "pokemon": _view(after, before),
        "changes": changes,
        "operations": _training_notes(ops),
    }


def _clone_notice(key, entries, previous_count):
    change = _change(
        "copies",
        "Copias del mismo Pokémon",
        "int",
        previous_count,
        len(entries),
        "alta",
        f"El mismo Pokémon aparece {len(entries)} veces en la partida con identificadores idénticos.",
    )
    return {
        "group_key": f"clone:{key}",
        "category": "origen",
        "severity": "alta",
        "title": "Pokémon duplicado",
        "summary": change["reason"] + " " + NO_PROOF,
        "origin": "desconocido",
        "pokemon": _view(entries[0]),
        "changes": [change],
        "operations": [],
    }


def _new_pokemon_notice(key, slot, transfers_in):
    """New in this save. Only origin anomalies are reported; a capture is normal."""
    if key in transfers_in or slot.is_egg:
        return None
    changes = []
    if slot.evidence.get("schema_version") == 2 and slot.evidence.get("source_trainer_match") is False:
        changes.append(
            _change(
                "foreign_ot",
                "Entrenador original",
                "text",
                None,
                slot.evidence.get("ot_name"),
                "baja",
                "Pokémon nuevo con un entrenador original distinto al de la partida y sin transferencia "
                "registrada; podría venir de un intercambio dentro del juego.",
            )
        )
    if slot.ivs and all(slot.ivs[s] == 31 for s in STATS):
        changes.append(
            _change(
                "perfect_ivs",
                "IVs",
                "text",
                None,
                "31 en las seis estadísticas",
                "baja",
                "Pokémon nuevo con los seis IVs perfectos, algo muy improbable de encontrar jugando; "
                "la crianza es la explicación habitual.",
            )
        )
    if not changes:
        return None
    return {
        "group_key": f"new:{key}",
        "category": "origen",
        "severity": _worst(changes),
        "title": "Pokémon nuevo con origen dudoso",
        "summary": changes[0]["reason"] + " " + NO_PROOF,
        "origin": "desconocido",
        "pokemon": _view(slot),
        "changes": changes,
        "operations": [],
    }


def _bag_view(snapshot):
    items = {}
    pouches = {}
    if isinstance(snapshot, dict):
        for item, count in (snapshot.get("items") or {}).items():
            items[int(item)] = count
        for item, pouch in (snapshot.get("pouches") or {}).items():
            pouches[int(item)] = pouch
    return items, pouches


def _credits(operations, start, end):
    """Item id → still unused authorized deliveries of that object, oldest first."""
    available = defaultdict(list)
    used = set(operations.get("credited") or ())
    deliveries = sorted(
        (d for d in operations.get("deliveries") or () if d.get("status") in ("RESERVED", "DELIVERED")),
        key=lambda d: _time(d["reserved_at"]),
    )
    for delivery in deliveries:
        if str(delivery["id"]) in used or _time(delivery["reserved_at"]) > end:
            continue
        finished = _time(delivery.get("finished_at"))
        if finished is not None and start is not None and finished <= start:
            continue  # it had its chance in the comparison before this one
        available[delivery.get("game_item_id")].append(delivery)
    return available


def _item_tier(item, pouch):
    if item in UNLIMITED_ITEM_IDS or pouch in IGNORED_POUCHES:
        return "ignored"
    if pouch in ("TMHMs", "ZCrystals"):
        return "record"
    if pouch in ("Berries", "BattleItems", "Balls"):
        return "ordinary" if item not in (1, 16) else "watch"
    if pouch == "Medicine":
        return "watch" if item in WATCHED_MEDICINE else "ordinary"
    return "ordinary" if item in ORDINARY_ITEMS else "watch"


def _compare_inventory(previous_bag, current_bag, pairs, operations, start, end):
    """Bag plus objects held by Pokémon present in both saves: moving an object
    from the bag to a Pokémon (or back) is never an increase."""
    bag_before, pouch_before = _bag_view(previous_bag)
    bag_after, pouch_after = _bag_view(current_bag)
    held_before = Counter(b.item for b, _ in pairs if b.item)
    held_after = Counter(a.item for _, a in pairs if a.item)
    credits = _credits(operations, start, end)
    credited_ids: list[str] = []
    considered: list[dict] = []
    rows: list[dict] = []
    records = 0
    for item in sorted(set(bag_before) | set(bag_after) | set(held_before) | set(held_after)):
        pouch = pouch_after.get(item) or pouch_before.get(item)
        tier = _item_tier(item, pouch)
        if tier == "ignored":
            continue
        before_total = bag_before.get(item, 0) + held_before.get(item, 0)
        after_total = bag_after.get(item, 0) + held_after.get(item, 0)
        delta = after_total - before_total
        if delta <= 0:
            continue
        matched = credits.get(item, [])[:delta]
        credited_ids.extend(str(d["id"]) for d in matched)
        considered.extend(
            {
                "kind": "delivery",
                "label": d.get("item_name") or "Objeto de la Tienda",
                "at": d.get("finished_at") or d.get("reserved_at"),
                "detail": "Entrega de una compra de la Tienda, auditada por el servidor.",
            }
            for d in matched
        )
        unjustified = delta - len(matched)
        if unjustified <= 0:
            continue
        if tier == "record":
            records += 1
            continue
        if tier == "ordinary" and unjustified < BULK_UNITS:
            continue
        carriers = [
            (a.nickname or _ref("Pokémon", a.species))
            for b, a in pairs
            if a.item == item and b.item != item
        ]
        severity = "media" if tier == "watch" else "baja"
        rows.append(
            _change(
                f"item_{item}",
                "Objeto",
                "item",
                before_total,
                after_total,
                severity,
                (
                    "Aumento de un objeto de uso común muy por encima de lo habitual; "
                    if tier == "ordinary"
                    else ""
                )
                + (
                    f"Solo {len(matched)} de las {delta} unidades "
                    + ("consta como entregada" if len(matched) == 1 else "constan como entregadas")
                    + " por PokeApp; el resto no tiene origen verificado."
                    if matched
                    else "Sin compras, recompensas ni entregas registradas en PokeApp que lo expliquen."
                ),
                item=_ref("Item", item),
                delta=delta,
                justified=len(matched),
                unjustified=unjustified,
                holders=carriers[:6],
            )
        )
    if records >= BULK_RECORDS:
        rows.append(
            _change(
                "records",
                "MT y cristales Z",
                "text",
                None,
                f"+{records} a la vez",
                "baja",
                "Han aparecido muchas MT o cristales Z de golpe; jugando se obtienen poco a poco.",
            )
        )
    return rows, credited_ids, considered


def analyze(previous, current, operations) -> dict:
    """Compare one accepted save with its predecessor.

    `previous`/`current`: {"payload", "uploaded_at", "bag", "friendship"}, where
    bag is {"items": {id: count}, "pouches": {id: name}} or None when unknown,
    and friendship {identity key: value} or None. Returns JSON-ready notices.
    Unknown data is never read as zero and never invents a change.
    """
    start = _time(previous.get("uploaded_at"))
    end = _time(current.get("uploaded_at"))
    before_groups: dict[str, list[Slot]] = defaultdict(list)
    after_groups: dict[str, list[Slot]] = defaultdict(list)
    for slot in slots(previous["payload"]):
        before_groups[slot.key].append(slot)
    for slot in slots(current["payload"]):
        after_groups[slot.key].append(slot)
    transfers_in = frozenset(
        key
        for key in (
            identity_key({"pid": t.get("pid"), "encryption_constant": t.get("ec")})
            for t in operations.get("transfers_in") or ()
        )
        if key
    )
    training = _training_ops(operations, start, end)
    bag_known = previous.get("bag") is not None and current.get("bag") is not None
    facts = _Facts(
        bag_known=bag_known,
        bag_before=_bag_view(previous.get("bag"))[0],
        bag_after=_bag_view(current.get("bag"))[0],
        friendship_known=previous.get("friendship") is not None and current.get("friendship") is not None,
        friendship_before=previous.get("friendship") or {},
        friendship_after=current.get("friendship") or {},
    )
    notices: list[dict] = []
    pairs: list[tuple[Slot, Slot]] = []
    for key in sorted(after_groups):
        after_list, before_list = after_groups[key], before_groups.get(key, [])
        if len(after_list) > 1 and len(after_list) > len(before_list):
            notices.append(_clone_notice(key, after_list, len(before_list)))
        elif len(after_list) == 1 and len(before_list) == 1:
            before, after = before_list[0], after_list[0]
            pairs.append((before, after))
            ops = training.get(key, [])
            changes = _compare_pokemon(before, after, ops, facts=facts)
            if changes:
                notices.append(_pokemon_notice(before, after, changes, ops))
        elif not before_list and len(after_list) == 1:
            notice = _new_pokemon_notice(key, after_list[0], transfers_in)
            if notice is not None:
                notices.append(notice)
    credited: list[str] = []
    inventory_status = "compared"
    if bag_known:
        rows, credited, considered = _compare_inventory(
            previous.get("bag"), current.get("bag"), pairs, operations, start, end
        )
        if rows:
            justified = sum(r.get("justified") or 0 for r in rows)
            notices.append(
                {
                    "group_key": "inventory",
                    "category": "objetos",
                    "severity": _worst(rows),
                    "title": (
                        f"{len(rows)} objetos con aumento sin verificar"
                        if len(rows) != 1
                        else "Objeto con aumento sin verificar"
                    ),
                    "summary": "La ausencia de compra en PokeApp no demuestra por sí sola que el objeto sea "
                    "ilegítimo: también se pueden conseguir jugando. " + NO_PROOF,
                    "origin": "parcialmente justificado" if justified else "desconocido",
                    "pokemon": None,
                    "changes": rows,
                    "operations": considered,
                }
            )
    else:
        inventory_status = "no_baseline" if current.get("bag") is not None else "unavailable"
    notices.sort(key=lambda n: (-SEVERITY_RANK[n["severity"]], n["group_key"]))
    return {
        "detector_version": DETECTOR_VERSION,
        "inventory_status": inventory_status,
        "notices": notices,
        "credited_deliveries": credited,
    }
