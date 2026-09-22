from copy import deepcopy
from dataclasses import replace
from threading import RLock
from uuid import uuid4

from app.domain.common import to_jsonable
from app.domain.pokemon import PokemonMove, PrivatePokemon, StatSpread
from app.domain.team_locks import TeamLockRecord, TeamLockSource
from app.repositories.errors import PersistenceError
from test_api_phase8b import TRAINER_ID


SEASON = "22222222-2222-2222-2222-222222222222"
MATCHDAY = "33333333-3333-3333-3333-333333333333"
PLAYER = "44444444-4444-4444-4444-444444444444"
SAVE = "55555555-5555-5555-5555-555555555555"
PARSED = "66666666-6666-6666-6666-666666666666"
OTHER = "77777777-7777-7777-7777-777777777777"
NOW = "2026-09-22T12:00:00Z"


def source_fixture():
    mon = PrivatePokemon(
        species="Milotic", level=55, ability="Competitive", nature="Bold",
        ivs=StatSpread(hp=31), evs=StatSpread(hp=252), original_trainer="private-owner",
        moves=(PokemonMove(name="Surf", move_id=57, pp=0),),
        metadata={"nested_private": {"pin": "dummy-never-public"}},
    )
    return TeamLockSource(
        season=dict(id=SEASON, status="active"),
        matchday=dict(id=MATCHDAY, season_id=SEASON, number=1, status="scheduled", closed_at=None),
        participant=dict(id=PLAYER, season_id=SEASON, trainer_id=TRAINER_ID, status="active"),
        save=dict(id=SAVE, season_id=SEASON, trainer_id=TRAINER_ID, sha256="a" * 64,
                  parser_status="parsed", parser_version="fixture-v1", deleted_at=None),
        parsed=dict(id=PARSED, save_file_id=SAVE, status="parsed", parser_version="fixture-v1", schema_version=1,
                    payload={"party": [{"slot_number": n, "pokemon": to_jsonable(mon)} for n in range(1, 7)]}),
    )


class MemoryAtomicTeamLocks:
    """Unit-test double. PostgreSQL atomicity is covered separately by SQL fixtures."""

    def __init__(self):
        self.source = source_fixture()
        self.records = {}
        self.events = {}
        self.mutations = []
        self.fail_event = False
        self.lock = RLock()

    def load_source(self, **kwargs):
        return deepcopy(self.source)

    def upsert_with_activity(self, mutation):
        with self.lock:
            key = (mutation.season_id, mutation.matchday_id, mutation.trainer_id)
            previous = self.records.get(key)
            record = TeamLockRecord(
                id=previous.id if previous else str(uuid4()), season_id=mutation.season_id,
                matchday_id=mutation.matchday_id, trainer_id=mutation.trainer_id,
                season_player_id=mutation.season_player_id, save_file_id=mutation.save_file_id,
                save_sha256=mutation.save_sha256, locked_at=NOW, deadline_at=None, is_late=False,
                public_team_snapshot=deepcopy(mutation.public_team_snapshot),
                private_team_snapshot=deepcopy(mutation.private_team_snapshot), created_at=NOW, updated_at=NOW,
            )
            if self.fail_event:
                raise PersistenceError("dummy event failure")
            self.records[key] = record
            self.events.setdefault(key, {"type": "TEAM_LOCKED", "lock_id": record.id, "save_id": record.save_file_id})
            self.mutations.append(deepcopy(mutation))
            return deepcopy(record)

    def change(self, section, **values):
        self.source = replace(self.source, **{section: dict(getattr(self.source, section), **values)})
