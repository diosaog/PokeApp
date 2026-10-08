"""Public current-game facts; no raw parser, save or identity evidence."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Region = Literal["hoenn", "kanto", "sinnoh", "johto", "unova"]


class ProgressQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BadgeRegionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    region: Region
    # Ordinals within this region, not a fabricated contiguous set from a count.
    earned_badges: list[int]


class ProgressRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["unknown", "observed"] = "unknown"
    game: str | None = None
    observed_at: datetime | None = None
    badges_count: int | None = Field(default=None, ge=0, le=16)
    primary_region: Region | None = None
    regions: list[BadgeRegionRead] | None = None
    champion_defeated: bool | None = None
