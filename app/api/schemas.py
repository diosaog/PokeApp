from __future__ import annotations

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
