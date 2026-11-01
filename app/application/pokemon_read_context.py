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
