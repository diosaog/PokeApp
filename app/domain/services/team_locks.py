from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields, replace

from app.domain.common import to_jsonable
from app.domain.legacy import pokemon_from_legacy
from app.domain.pokemon import PokemonFlags, PokemonMove, PrivatePokemon, PublicPokemon, StatSpread
from app.domain.seasons import SeasonRules
from app.domain.team_locks import TeamLock


@dataclass(frozen=True)
class TeamLockValidation:
    allowed: bool
    reason: str = "ok"


def validate_team_lock(
    *,
    trainer_id: str,
    participant_ids: list[str] | tuple[str, ...],
    matchday_number: int,
    team: list[PublicPokemon] | tuple[PublicPokemon, ...],
    rules: SeasonRules,
) -> TeamLockValidation:
    trainer = str(trainer_id or "").strip()
    if not trainer:
        return TeamLockValidation(False, "missing_trainer")
    if trainer not in {str(value) for value in participant_ids}:
        return TeamLockValidation(False, "trainer_not_participant")
    if int(matchday_number or 0) <= 0:
        return TeamLockValidation(False, "invalid_matchday")
    if len(tuple(team)) != 6:
        return TeamLockValidation(False, "team_requires_six")
    return TeamLockValidation(True)


def build_team_lock(
    *,
    lock_id: str,
    season_id: str,
    trainer_id: str,
    locked_at: str,
    team: list[PublicPokemon] | tuple[PublicPokemon, ...],
    matchday_id: str = "",
    matchday_number: int | None = None,
    save_record_id: str = "",
    save_sha256: str = "",
    deadline_at: str = "",
    is_late: bool = False,
) -> TeamLock:
    return TeamLock(
        id=lock_id,
        season_id=season_id,
        trainer_id=trainer_id,
        locked_at=locked_at,
        team=tuple(team)[:6],
        matchday_id=matchday_id,
        matchday_number=matchday_number,
        save_record_id=save_record_id,
        save_sha256=save_sha256,
        deadline_at=deadline_at,
        is_late=bool(is_late),
    )


def snapshots_from_parsed_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    """Hydrate existing DTOs or legacy party rows; this does not parse raw saves."""
    party = payload.get("party")
    if not isinstance(party, list) or len(party) != 6:
        raise ValueError("team_requires_six")
    if not all(isinstance(slot, dict) for slot in party):
        raise ValueError("invalid_parsed_team")
    slotted = any("slot_number" in slot or "pokemon" in slot for slot in party)
    if slotted:
        if any(type(slot.get("slot_number")) is not int for slot in party):
            raise ValueError("invalid_party_slots")
        if sorted(slot["slot_number"] for slot in party) != list(range(1, 7)):
            raise ValueError("invalid_party_slots")
        party = [slot.get("pokemon") for slot in sorted(party, key=lambda slot: slot["slot_number"])]

    private_team = []
    for raw in party:
        if not isinstance(raw, dict):
            raise ValueError("invalid_parsed_team")
        if slotted:
            # Rehydrate the established PrivatePokemon DTO, including typed children.
            data = {f.name: deepcopy(raw[f.name]) for f in fields(PrivatePokemon) if f.name in raw}
            data["moves"] = tuple(PokemonMove(**move) for move in data.get("moves", []))
            data["flags"] = PokemonFlags(**data.get("flags", {}))
            for key in ("ivs", "evs"):
                if data.get(key) is not None:
                    data[key] = StatSpread(**data[key])
            mon = PrivatePokemon(**data)
        else:
            mon = pokemon_from_legacy(raw, private=True)
        private_team.append(mon)
    # Free-form metadata has no public visibility contract, even inside a DTO.
    public = [to_jsonable(replace(mon, metadata={}).to_public()) for mon in private_team]
    private = [to_jsonable(mon) for mon in private_team]
    return deepcopy(public), deepcopy(private)
