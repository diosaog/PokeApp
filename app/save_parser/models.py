"""Small, versioned wire models; no PKHeX names, local paths or app identity claims."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
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


class ObservedSave(WireModel):
    game: str = Field(min_length=1, max_length=24)
    generation: Literal[3, 4, 5]
    trainer: ParsedTrainer
    party: tuple[ParsedPokemon | None, ...] = Field(min_length=6, max_length=6)
    boxes: tuple[ParsedBox, ...] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_layout(self):
        if [b.number for b in self.boxes] != list(range(1, len(self.boxes) + 1)):
            raise ValueError("invalid_box_layout")
        if any(p.identity.format != self.generation for _, p in self.occupied()):
            raise ValueError("invalid_native_format")
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
