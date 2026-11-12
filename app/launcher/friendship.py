"""«Felicidad máxima» over the existing journal (owner request 2026-11-04).

Free and unlimited, like Rare Candy and Heart Scale: no coins, purchase,
server record or admin approval. One Pokémon's real friendship (the byte the
game reads for its current handler) becomes 255. Since 2026-11-12 the Pokémon
may be in the current party or in any PC box: it is changed where it is, never
moved. Pokémon-Amie affection and every other byte stay unchanged; randomized
species, moves or abilities are never judged. Every write goes through the
same engine as the other operations: emulator closed, exact source bytes,
independent verified backup, durable journal, native re-read and
recovery/restore.

Enabled in production with Launcher 0.26.12 (owner authorization 2026-11-05);
PC boxes with Launcher 0.26.15 (owner authorization 2026-11-12).
"""

from hashlib import sha256

from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WriteSafetyError

KIND = "max_friendship"
MAX_FRIENDSHIP = 255
# A party change keeps its original shape (no box_index): journals written by
# earlier Launchers still verify and recover unchanged.
PARTY_KEYS = {"kind", "location", "slot_index", "expected_pokemon_sha256", "expected_friendship"}
BOX_KEYS = PARTY_KEYS | {"box_index"}
BOXES = 32
BOX_SLOTS = 30


def valid_place(location, box_index, slot_index):
    """Party slot 0-5 without a box, or a box 0-31 and slot 0-29."""
    if type(slot_index) is not int:
        return False
    if location == "party":
        return box_index is None and 0 <= slot_index <= 5
    return (
        location == "box"
        and type(box_index) is int
        and 0 <= box_index < BOXES
        and 0 <= slot_index < BOX_SLOTS
    )


def place_text(location, box_index, slot_index):
    if location == "box":
        return f"la Caja {box_index + 1}, posición {slot_index + 1}"
    return f"la posición {slot_index + 1} del equipo"


def describe(change):
    location = change.get("location") if isinstance(change, dict) else None
    if (
        set(change) != (BOX_KEYS if location == "box" else PARTY_KEYS)
        or change["kind"] != KIND
        or not valid_place(location, change.get("box_index"), change["slot_index"])
        or type(change["expected_friendship"]) is not int
        or not 0 <= change["expected_friendship"] < MAX_FRIENDSHIP
    ):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    return (
        f"Subir a {MAX_FRIENDSHIP} la felicidad del Pokémon en "
        f"{place_text(location, change.get('box_index'), change['slot_index'])} "
        f"(ahora {change['expected_friendship']}). "
        "Solo cambia ese valor y el Pokémon no se mueve; se conserva una copia del archivo original."
    )


def party_view(native, data):
    """The party and every occupied PC box slot, read from these exact bytes."""
    reading = native.inspect_friendship(data)
    return {
        "game": reading["game"],
        "source_sha256": reading["source_sha256"],
        "party": [dict(member) for member in reading["party"]],
        "boxes": [dict(member) for member in reading["boxes"]],
    }


def find_member(view, location, box_index, slot_index):
    if location == "box":
        return next(
            (m for m in view["boxes"] if m["box_index"] == box_index and m["slot_index"] == slot_index),
            None,
        )
    return next((m for m in view["party"] if m["slot_index"] == slot_index), None)


def friendship_intent(native, data, slot_index, pokemon_sha256, box_index=None):
    """The exact change for the Pokémon the trainer saw, from one snapshot.

    Without `box_index` the target is a party slot; with it, that PC box slot.
    The Pokémon must still be exactly there (same bytes) or nothing happens.
    """
    location = "party" if box_index is None else "box"
    if not valid_place(location, box_index, slot_index) or not isinstance(pokemon_sha256, str):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    reading = native.inspect_friendship(data)
    if reading["source_sha256"] != sha256(data).hexdigest():
        raise WriteSafetyError("STALE_SOURCE")
    member = find_member(reading, location, box_index, slot_index)
    if member is None or not member["eligible"]:
        raise WriteSafetyError("FRIENDSHIP_NOT_ELIGIBLE")
    if member["pokemon_sha256"] != pokemon_sha256:
        raise WriteSafetyError("STALE_MUTATION")  # another Pokémon is there now
    if member["friendship"] >= MAX_FRIENDSHIP:
        raise WriteSafetyError("FRIENDSHIP_ALREADY_MAX")
    mutation = {
        "kind": KIND,
        "location": location,
        "slot_index": slot_index,
        "expected_pokemon_sha256": member["pokemon_sha256"],
        "expected_friendship": member["friendship"],
    }
    if location == "box":
        mutation["box_index"] = box_index
    return WriteIntent.create(
        expected_sha256=reading["source_sha256"],
        game=reading["game"],
        trainer_key=reading["trainer_key"],
        mutation=mutation,
    )
