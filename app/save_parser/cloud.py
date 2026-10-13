"""Private client observations, explicitly NOT trusted competitive save facts."""

import json
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid5

from pydantic import Field, field_validator

from app.save_parser.models import ObservedSave, SaveFingerprint, WireModel

MAX_OBSERVATION_BYTES = 2 * 1024 * 1024
NAMESPACE = UUID("ee56edca-d0f9-46b7-89ad-155b10b466ca")


class CloudObservation(WireModel):
    schema_version: Literal[1] = 1
    fingerprint: SaveFingerprint
    parser_version: Literal["pokeapp-reader/3;pkhex/24.11.11"]
    observation: ObservedSave

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_schema_version")
        return value

    def digest(self) -> str:
        return sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest()

    def identifier(self, trainer_id: str, season_id: str) -> str:
        return str(
            uuid5(NAMESPACE, f"{UUID(trainer_id)}:{UUID(season_id)}:{self.digest()}")
        )


class ObservationReceipt(WireModel):
    id: str
    trainer_id: str
    season_id: str
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    received_at: str
    trust: Literal["client_observed"]
    competitive_authority: Literal[False]

    @field_validator("id", "trainer_id", "season_id")
    @classmethod
    def canonical_uuid(cls, value):
        if str(UUID(value)) != value:
            raise ValueError("invalid_receipt_identity")
        return value

    @field_validator("received_at")
    @classmethod
    def timestamp(cls, value):
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("invalid_receipt_timestamp")
        return value

    @field_validator("competitive_authority", mode="before")
    @classmethod
    def no_authority(cls, value):
        if value is not False:
            raise ValueError("untrusted_receipt")
        return value
