from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
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


class NormalPurchaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    confirm_base_price: bool = Field(default=False, strict=True)


class PromotionalPurchaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NormalPurchaseResponse(BaseModel):
    id: UUID
    season_id: UUID
    trainer_id: UUID
    season_player_id: UUID
    item_id: UUID
    quantity: Literal[1]
    unit_price: int = Field(gt=0)
    total_price: int = Field(gt=0)
    status: Literal["pending"]
    purchased_at: datetime
    balance_after: int = Field(ge=0)
    ledger_id: UUID
    event_id: UUID
    matchday_id: UUID
    matchday_number: int = Field(gt=0)


class PromotionalPurchaseResponse(NormalPurchaseResponse):
    promotion_id: UUID
    base_price: int = Field(gt=0)
    promotion_kind: Literal["normal", "mega"]
    remaining_stock: int = Field(ge=0)


class RedemptionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pokemon_entity_id: UUID


class RedemptionResponse(BaseModel):
    redemption_id: UUID
    purchase_id: UUID
    season_id: UUID
    trainer_id: UUID
    shop_item_id: UUID
    effect_code: Literal['shield', 'revive']
    target_pokemon_entity_id: UUID
    target_owner_trainer_id: UUID
    purchase_status: Literal['used']
    redemption_status: Literal['applied']
    physical_effect_status: Literal['not_required', 'pending']
    requested_at: datetime
    redeemed_at: datetime
    physical_effect_completed_at: None
    activity_event_id: UUID
    gift_purchase_id: None


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
