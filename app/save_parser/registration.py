"""Shared receipt contract. A private observation receipt cannot satisfy it."""

from typing import Literal

from pydantic import Field

from app.domain.pokemon_identity import digest
from app.save_parser.models import ObservedSave, WireModel


def observation_digest(observation: ObservedSave, parser_version: str) -> str:
    return digest(
        {
            "parser_version": parser_version,
            "observation": observation.model_dump(mode="json"),
        }
    )


class SaveRegistration(WireModel):
    status: Literal["registered"]
    save_id: str
    trainer_id: str
    season_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    parser_version: str
    is_current: bool
