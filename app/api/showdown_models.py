"""The owner's private Pokémon Showdown export of their current party."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class ShowdownWarningRead(BaseModel):
    code: str
    slot: Annotated[int, Field(ge=1, le=6)]
    detail: Annotated[str, Field(max_length=200)] = ""


class ShowdownExportRead(BaseModel):
    """Generated on request from the same save projection as the «Equipo»
    card; the client compares save_id/uploaded_at with what it shows."""

    save_id: UUID
    uploaded_at: datetime
    game: str | None
    text: Annotated[str, Field(max_length=6000)]
    count: Annotated[int, Field(ge=1, le=6)]
    warnings: list[ShowdownWarningRead] = Field(default_factory=list, max_length=60)
