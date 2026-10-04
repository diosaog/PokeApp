"""Owned live wipe counter, separate from save observations and frozen history."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.api.season_admin_models import StrictBody

WipeCount = Annotated[int, Field(strict=True, ge=0, le=2147483647)]
WipeRevision = Annotated[int, Field(strict=True, ge=0, le=9007199254740991)]


class SetWipeRevivalsBody(StrictBody):
    revived_after_wipe: WipeCount
    expected_revision: WipeRevision


class WipeRevivalsRead(StrictBody):
    season_id: UUID
    revived_after_wipe: WipeCount
    revision: WipeRevision
    editable: Annotated[bool, Field(strict=True)]
    blocking_reason: (
        Literal[
            "participant_inactive",
            "season_inactive",
            "league_closed",
            "membership_ineligible",
        ]
        | None
    )
    replayed: Annotated[bool, Field(strict=True)]

    @model_validator(mode="after")
    def consistent_editability(self):
        if self.editable != (self.blocking_reason is None):
            raise ValueError("Invalid wipe counter editability")
        return self
