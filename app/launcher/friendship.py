"""«Felicidad máxima» over the existing journal (owner request 2026-11-04).

Free and unlimited, like Rare Candy and Heart Scale: no coins, purchase,
server record or admin approval. One current-party Pokémon's real friendship
(the byte the game reads for its current handler) becomes 255. Pokémon-Amie
affection and every other byte stay unchanged; randomized species, moves or
abilities are never judged. Every write goes through the same engine as the
other operations: emulator closed, exact source bytes, independent verified
backup, durable journal, native re-read and recovery/restore.

Production writes stay off until the owner enables "max_friendship" in
write_engine.PRODUCTION_MUTATIONS after real-save qualification.
"""

from hashlib import sha256

from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WriteSafetyError

KIND = "max_friendship"
MAX_FRIENDSHIP = 255


def describe(change):
    if (
        set(change) != {"kind", "location", "slot_index", "expected_pokemon_sha256", "expected_friendship"}
        or change["kind"] != KIND
        or change["location"] != "party"
        or type(change["slot_index"]) is not int
        or not 0 <= change["slot_index"] <= 5
        or type(change["expected_friendship"]) is not int
        or not 0 <= change["expected_friendship"] < MAX_FRIENDSHIP
    ):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    return (
        f"Subir a {MAX_FRIENDSHIP} la felicidad del Pokémon en la posición "
        f"{change['slot_index'] + 1} del equipo (ahora {change['expected_friendship']}). "
        "Solo cambia ese valor; se conserva una copia del archivo original."
    )


def party_view(native, data):
    reading = native.inspect_friendship(data)
    return {
        "game": reading["game"],
        "source_sha256": reading["source_sha256"],
        "party": [dict(member) for member in reading["party"]],
    }


def friendship_intent(native, data, slot_index, pokemon_sha256):
    """The exact change for the Pokémon the trainer saw, from one snapshot."""
    if type(slot_index) is not int or not 0 <= slot_index <= 5 or not isinstance(pokemon_sha256, str):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    reading = native.inspect_friendship(data)
    if reading["source_sha256"] != sha256(data).hexdigest():
        raise WriteSafetyError("STALE_SOURCE")
    member = next((m for m in reading["party"] if m["slot_index"] == slot_index), None)
    if member is None or not member["eligible"]:
        raise WriteSafetyError("FRIENDSHIP_NOT_ELIGIBLE")
    if member["pokemon_sha256"] != pokemon_sha256:
        raise WriteSafetyError("STALE_MUTATION")  # the party changed since it was shown
    if member["friendship"] >= MAX_FRIENDSHIP:
        raise WriteSafetyError("FRIENDSHIP_ALREADY_MAX")
    return WriteIntent.create(
        expected_sha256=reading["source_sha256"],
        game=reading["game"],
        trainer_key=reading["trainer_key"],
        mutation={
            "kind": KIND,
            "location": "party",
            "slot_index": slot_index,
            "expected_pokemon_sha256": member["pokemon_sha256"],
            "expected_friendship": member["friendship"],
        },
    )
