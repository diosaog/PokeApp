from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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
    matchday_id: UUID | None
    matchday_number: int | None = Field(gt=0)

    @field_serializer("balance_after")
    def exact_balance(self, value: int) -> str:
        return str(value)


class PromotionalPurchaseResponse(NormalPurchaseResponse):
    promotion_id: UUID
    base_price: int = Field(gt=0)
    promotion_kind: Literal["normal", "mega"]
    remaining_stock: int = Field(ge=0)


class RedemptionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pokemon_entity_id: UUID


class RedemptionResponse(BaseModel):
    # Additive current projection; physical_effect_status remains the original snapshot.
    physical_state: str | None = None
    redemption_id: UUID
    purchase_id: UUID
    season_id: UUID
    trainer_id: UUID
    shop_item_id: UUID
    effect_code: Literal["shield", "revive", "robbery_shield", "steal"]
    target_pokemon_entity_id: UUID
    target_owner_trainer_id: UUID
    purchase_status: Literal["used"]
    redemption_status: Literal["applied"]
    physical_effect_status: Literal["not_required", "pending"]
    requested_at: datetime
    redeemed_at: datetime
    physical_effect_completed_at: None
    activity_event_id: UUID
    gift_purchase_id: UUID | None


class ItemUsePrepareBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pokemon_entity_id: UUID
    save_file_id: UUID
    save_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")


class ItemUseClaimBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    claim_id: UUID


class ItemUseCompleteBody(ItemUseClaimBody):
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    status: Literal[
        "APPLIED_VERIFIED",
        "FAILED_RECOVERABLE",
        "RECOVERY_REQUIRED",
        "BLOCKED_UNCERTAIN",
    ]
    observed_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    error_code: str | None = Field(default=None, pattern=r"^[A-Z0-9_]{1,64}$")


class ItemUseResponse(BaseModel):
    physical_state: str | None = None
    id: UUID
    operation_id: str
    purchase_id: UUID
    season_id: UUID
    trainer_id: UUID
    target_pokemon_entity_id: UUID
    save_file_id: UUID
    save_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    effect_code: Literal["revive", "steal"]
    status: Literal[
        "PREPARED",
        "PENDING_APPLICATION",
        "APPLIED_VERIFIED",
        "FAILED_RECOVERABLE",
        "RECOVERY_REQUIRED",
        "BLOCKED_UNCERTAIN",
    ]
    observed_sha256: str | None = None
    error_code: str | None = None
    receipt: dict | None = None
    created_at: datetime
    updated_at: datetime
    applied_at: datetime | None = None
    expires_at: datetime


class ItemUseListResponse(BaseModel):
    items: list[ItemUseResponse]
    physical_application_enabled: Literal[False] = False


TransferStatus = Literal[
    "PREPARING",
    "WAITING_OTHER",
    "PENDING_SOURCE",
    "VERIFYING_SOURCE",
    "PENDING_DESTINATION",
    "VERIFYING_BOTH",
    "BOTH_VERIFIED_PENDING_IDENTITY",
    "COMMITTED",
    "CANCELLED",
    "BLOCKED_UNCERTAIN",
]


class TransferRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pokemon_entity_id: UUID


class TransferRequestResponse(BaseModel):
    authorization_id: UUID
    status: TransferStatus


class TransferSummary(BaseModel):
    authorization_id: UUID
    side: Literal["source", "destination"]
    status: TransferStatus
    purchase_id: UUID | None = None
    pokemon_entity_id: UUID
    claimed: bool
    apply_started: bool
    verified: bool
    accepted_save_id: UUID | None = None
    expires_at: datetime
    created_at: datetime


class TransferListResponse(BaseModel):
    items: list[TransferSummary]
    transfer_enabled: bool = False


class TransferLauncherItem(TransferSummary):
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    # Own side only; the Launcher's native engine revalidates it before any use.
    intent: dict[str, Any] | None = None


class TransferLauncherListResponse(BaseModel):
    items: list[TransferLauncherItem]
    transfer_enabled: bool = False


class TransferLegBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["ready", "begin", "cancel"]
    claim_id: UUID | None = None
    backup_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class TransferLegResponse(BaseModel):
    authorization_id: UUID
    side: Literal["source", "destination"]
    status: TransferStatus
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    apply_started: bool
    result_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    verified: bool
    accepted_save_id: UUID | None = None


class ItemArtifactResponse(BaseModel):
    authorization_id: UUID
    status: Literal[
        "NOT_SUBMITTED", "UPLOADING", "QUEUED", "VERIFYING", "VERIFIED", "REJECTED", "EXPIRED", "RETRY_REQUIRED"
    ]
    result_sha256: str | None = None


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
