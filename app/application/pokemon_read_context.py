"""Display context from the same server-parsed save, including older payloads."""

from app.repositories.errors import PersistenceError

GAME_GENERATIONS = {"X": 6, "Y": 6, "OR": 6, "AS": 6,
                    "SN": 7, "MN": 7, "US": 7, "UM": 7}


def pokemon_context(pokemon, payload, game=None):
    """Never infer an item table from species, the viewer, or another save."""
    source_game = payload.get("game", game)
    if game is not None and source_game != game:
        raise PersistenceError("Save game mismatch")
    generation = GAME_GENERATIONS.get(source_game)
    if generation is not None and payload.get("generation", generation) != generation:
        raise PersistenceError("Save generation mismatch")
    return {**pokemon, **({"item_generation": generation} if generation else {})}


def item_generation_of(payload):
    """Item table of one parsed save, or None when the payload cannot tell it."""
    if not isinstance(payload, dict):
        return None
    generation = GAME_GENERATIONS.get(payload.get("game"))
    if generation is None or payload.get("generation", generation) != generation:
        return None
    return generation


def game_item_generation(game):
    return GAME_GENERATIONS.get(game)


def with_item_generation(team, generation):
    """A frozen team named with the item table of the save it was fixed from.

    Team Lock snapshots stored before 2026-11-11 kept "Item #234" without its
    table, so the web could only say «Objeto sin identificar». A value the
    snapshot already carries always wins; nothing is added without a game.
    """
    if generation is None or not isinstance(team, list):
        return team
    return [
        {**mon, "item_generation": mon.get("item_generation") or generation}
        if isinstance(mon, dict) and mon.get("item")
        else mon
        for mon in team
    ]
