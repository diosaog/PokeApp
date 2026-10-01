"""Small, versioned wire models; no PKHeX names, local paths or app identity claims."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.pokemon_identity import (
    PokemonIdentityEvidence,
    PokemonLocation,
    ParsedPokemonObservation,
)


class ErrorCode(StrEnum):
    SAVE_NOT_FOUND = "SAVE_NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    FILE_LOCKED = "FILE_LOCKED"
    UNSUPPORTED_GAME = "UNSUPPORTED_GAME"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    CORRUPT_SAVE = "CORRUPT_SAVE"
    TRUNCATED_SAVE = "TRUNCATED_SAVE"
    PARSER_FAILURE = "PARSER_FAILURE"
    AMBIGUOUS_IDENTITY = "AMBIGUOUS_IDENTITY"
    SAVE_CHANGED_DURING_READ = "SAVE_CHANGED_DURING_READ"
    INVALID_PATH = "INVALID_PATH"


class SaveError(Exception):
    def __init__(self, code: ErrorCode):
        self.code = ErrorCode(code)
        super().__init__(self.code.value)


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SaveFingerprint(WireModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=1, le=8 * 1024 * 1024)


class ParsedTrainer(WireModel):
    name: str = Field(max_length=64)
    tid: int = Field(ge=0, le=65535)
    sid: int = Field(ge=0, le=65535)
    gender: int = Field(ge=0, le=1)
    language: int | None = Field(default=None, ge=0, le=255)


class ParsedMove(WireModel):
    id: int = Field(ge=0, le=559)
    pp: int = Field(ge=0, le=255)


class ParsedPokemon(WireModel):
    species_id: int = Field(ge=1, le=649)
    nickname: str = Field(max_length=64)
    level: int = Field(ge=1, le=100)
    form: int = Field(ge=0, le=255)
    gender: int = Field(ge=0, le=2)
    shiny: bool
    is_egg: bool
    ability_id: int = Field(ge=0, le=255)
    nature_id: int = Field(ge=0, le=24)
    item_id: int = Field(ge=0, le=65535)
    moves: tuple[ParsedMove, ...] = Field(min_length=4, max_length=4)
    ivs: tuple[int, ...] = Field(min_length=6, max_length=6)
    evs: tuple[int, ...] = Field(min_length=6, max_length=6)
    identity: PokemonIdentityEvidence

    @field_validator("identity", mode="before")
    @classmethod
    def identity_inputs(cls, value):
        return PokemonIdentityEvidence(**value) if isinstance(value, dict) else value

    @model_validator(mode="after")
    def validate_stats(self):
        if any(not 0 <= v <= 31 for v in self.ivs) or any(
            not 0 <= v <= 255 for v in self.evs
        ):
            raise ValueError("invalid_stats")
        if self.ivs != self.identity.ivs:
            raise ValueError("inconsistent_identity_ivs")
        return self


class ParsedBox(WireModel):
    number: int = Field(ge=1, le=24)
    slots: tuple[ParsedPokemon | None, ...] = Field(min_length=30, max_length=30)


ProgressRegion = Literal["hoenn", "kanto", "sinnoh", "johto", "unova"]


class ObservedBadgeRegion(WireModel):
    """Observed flags in the game's badge-bit order; false is observed absence."""

    region: ProgressRegion
    badge_flags: tuple[bool, ...] = Field(min_length=8, max_length=8)


class ObservedProgress(WireModel):
    """Save facts only: no competitive cap, admin approval or ownership claim."""

    schema_version: Literal[1]
    primary_region: ProgressRegion
    regions: tuple[ObservedBadgeRegion, ...] = Field(min_length=1, max_length=2)

    @field_validator("schema_version", mode="before")
    @classmethod
    def version_is_integer(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_progress_version")
        return value

    @model_validator(mode="after")
    def validate_regions(self):
        names = tuple(region.region for region in self.regions)
        if len(names) != len(set(names)) or names[0] != self.primary_region:
            raise ValueError("invalid_progress_regions")
        return self


def progress_layout(game: str) -> tuple[int, tuple[str, ...]] | None:
    """Native games supported by the worker, including PKHeX family labels."""
    if game in {"R", "S", "RS", "E"}:
        return 3, ("hoenn",)
    if game in {"FR", "LG", "FRLG"}:
        return 3, ("kanto",)
    if game in {"D", "P", "DP", "Pt"}:
        return 4, ("sinnoh",)
    if game in {"HG", "SS", "HGSS"}:
        return 4, ("johto", "kanto")
    if game in {"B", "W", "BW", "B2", "W2", "B2W2"}:
        return 5, ("unova",)
    return None


class ObservedSave(WireModel):
    game: str = Field(min_length=1, max_length=24)
    generation: Literal[3, 4, 5]
    trainer: ParsedTrainer
    party: tuple[ParsedPokemon | None, ...] = Field(min_length=6, max_length=6)
    boxes: tuple[ParsedBox, ...] = Field(min_length=1, max_length=24)
    # Old neutral observations remain readable, without turning unknown into zero.
    progress: ObservedProgress | None = None

    @model_validator(mode="after")
    def validate_layout(self):
        if [b.number for b in self.boxes] != list(range(1, len(self.boxes) + 1)):
            raise ValueError("invalid_box_layout")
        if any(p.identity.format != self.generation for _, p in self.occupied()):
            raise ValueError("invalid_native_format")
        if self.progress is not None:
            observed_layout = (
                self.generation,
                tuple(region.region for region in self.progress.regions),
            )
            if progress_layout(self.game) != observed_layout:
                raise ValueError("invalid_progress_game")
        return self

    def occupied(self):
        for slot, pokemon in enumerate(self.party, 1):
            if pokemon is not None:
                yield PokemonLocation("party", 0, slot), pokemon
        for box in self.boxes:
            for slot, pokemon in enumerate(box.slots, 1):
                if pokemon is not None:
                    yield PokemonLocation("box", box.number, slot), pokemon

    def identity_observations(self) -> tuple[ParsedPokemonObservation, ...]:
        """Inputs compatible with 023, WITHOUT allocating or binding authoritative IDs."""
        return tuple(
            ParsedPokemonObservation(location, p.identity)
            for location, p in self.occupied()
        )


def progress_evidence(observation: ObservedSave, source_hash: str) -> dict:
    """Neutral additive envelope for a future trusted 023 ingestion adapter.

    Persist only alongside the same parsed save/identity binding. The envelope is
    not a signature or an authorization; callers cannot promote client JSON into
    trustworthy server facts merely by constructing this dictionary.
    """
    if not isinstance(observation, ObservedSave):
        raise ValueError("invalid_observed_save")
    if not isinstance(source_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", source_hash
    ):
        raise ValueError("invalid_source_hash")
    return {
        "schema_version": 1,
        "game": observation.game,
        "generation": observation.generation,
        "source_hash": source_hash,
        "progress": observation.progress.model_dump(mode="json")
        if observation.progress is not None
        else None,
    }


class ParserResponse(WireModel):
    schema_version: Literal[1]
    parser_version: str = Field(min_length=1, max_length=100)
    observation: ObservedSave | None
    error: ErrorCode | None

    @model_validator(mode="after")
    def one_outcome(self):
        if (self.observation is None) == (self.error is None):
            raise ValueError("invalid_parse_outcome")
        return self


class SaveParser(Protocol):
    version: str

    def parse(self, data: bytes) -> ObservedSave: ...


@dataclass(frozen=True)
class PokemonChange:
    status: str
    before: tuple[PokemonLocation, ...]
    after: tuple[PokemonLocation, ...]


def compare_observations(
    before: ObservedSave | None, after: ObservedSave
) -> tuple[PokemonChange, ...]:
    """Local hints only. Same-PID collisions/core changes remain ambiguous, as in 023."""
    old, new = defaultdict(list), defaultdict(list)
    for location, p in before.occupied() if before else ():
        old[p.identity.pid].append((location, p))
    for location, p in after.occupied():
        new[p.identity.pid].append((location, p))
    changes = []
    for pid in sorted(old.keys() | new.keys()):
        a, b = old[pid], new[pid]
        if len(a) > 1 or len(b) > 1:
            status = "AMBIGUOUS"
        elif not a:
            status = "NEW"
        elif not b:
            status = "MISSING"
        elif a[0][1].identity.candidate_key != b[0][1].identity.candidate_key:
            status = "AMBIGUOUS"
        elif a[0][1] != b[0][1]:
            status = "CHANGED"
        else:
            status = "MOVED" if a[0][0] != b[0][0] else "UNCHANGED"
        changes.append(
            PokemonChange(status, tuple(x[0] for x in a), tuple(x[0] for x in b))
        )
    return tuple(changes)
