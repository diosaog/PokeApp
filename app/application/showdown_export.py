"""«Generar Poképaste»: the owner's current party as Pokémon Showdown text.

Built on request only, from the very PCRead projection the trainer profile's
«Equipo» card displays (personal or League save, already scoped to the
authenticated owner). Never a Team Lock snapshot, never a write: the save,
its EVs and every stored projection stay exactly as they are.
"""

from __future__ import annotations

import re

from app.api.read_models import PCRead
from app.api.showdown_models import ShowdownExportRead, ShowdownWarningRead
from app.application.pokemon_read_context import GAME_GENERATIONS
from app.domain.showdown import export_team

_PARTY = re.compile(r"^Equipo · ([1-6])$")


class ShowdownUnavailable(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def party_export(pc: PCRead) -> ShowdownExportRead:
    if pc.status != "ready" or pc.save is None:
        raise ShowdownUnavailable("SHOWDOWN_SAVE_NOT_READY")
    party = sorted(
        (
            (int(match.group(1)), slot.pokemon)
            for slot in pc.pokemon
            if (match := _PARTY.match(slot.location))
        ),
        key=lambda pair: pair[0],
    )
    if not party:
        raise ShowdownUnavailable("SHOWDOWN_TEAM_EMPTY")
    generation = GAME_GENERATIONS.get(pc.save.game or "", 6)
    result = export_team(
        (pokemon.model_dump(mode="json") for _, pokemon in party),
        generation=generation,
        projection="private",
    )
    if not result.count:
        raise ShowdownUnavailable("SHOWDOWN_TEAM_EMPTY")
    # Warning slots refer to the exported order, i.e. the party order.
    slots = [number for number, _ in party]
    return ShowdownExportRead(
        save_id=pc.save.id,
        uploaded_at=pc.save.uploaded_at,
        game=pc.save.game,
        text=result.text,
        count=result.count,
        warnings=[
            ShowdownWarningRead(
                code=w.code, slot=slots[w.slot - 1], detail=w.detail[:200]
            )
            for w in result.warnings
        ],
    )
