from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    service: str
    status: str


class PinLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_identifier: str = Field(min_length=1, max_length=128)
    pin: str = Field(min_length=1, max_length=32)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class SessionResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str = ""
    expires_at: int | None = None
    expires_in: int | None = None


class AuthSessionResponse(BaseModel):
    trainer_id: str
    auth_user_id: str
    session: SessionResponse


class RefreshResponse(BaseModel):
    session: SessionResponse


class MeResponse(BaseModel):
    trainer_id: str
    display_name: str
    is_admin: bool
    globally_enabled: bool


class TeamLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save_file_id: UUID


class TeamLockResponse(BaseModel):
    id: UUID
    season_id: UUID
    matchday_id: UUID
    trainer_id: UUID
    season_player_id: UUID
    save_file_id: UUID
    save_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    locked_at: datetime
    deadline_at: datetime | None
    is_late: bool
    public_team_snapshot: list[dict[str, Any]] = Field(min_length=6, max_length=6)
    private_team_snapshot: list[dict[str, Any]] = Field(min_length=6, max_length=6)
    created_at: datetime
    updated_at: datetime
