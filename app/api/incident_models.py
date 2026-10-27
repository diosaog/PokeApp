"""Admin incident center contracts (Phase 28, local until migration 062 ships)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Reason = Field(min_length=5, max_length=500)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A reason is required and kept in the audit: no blank or padded text.
    @field_validator("reason", check_fields=False)
    @classmethod
    def trimmed_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("reason too short")
        return value


class PurchaseResolveBody(Strict):
    # cancel: a pending, unused purchase; refund: a used one. Coins return once.
    action: Literal["cancel", "refund"]
    reason: str = Reason


class CoinAdjustBody(Strict):
    trainer_id: UUID
    amount: int = Field(ge=-100000, le=100000)
    reason: str = Reason

    @field_validator("amount")
    @classmethod
    def not_zero(cls, value):
        if value == 0:
            raise ValueError("amount must not be zero")
        return value


class IncidentReceipt(BaseModel):
    operation_id: UUID
    kind: Literal["purchase_cancel", "purchase_refund", "coin_adjustment"]
    season_id: UUID
    trainer_id: UUID
    purchase_id: UUID | None = None
    status: Literal["cancelled", "refunded", "applied"]
    amount: int
    ledger_id: UUID | None = None
    balance_after: int
    replayed: bool


class IncidentWallet(BaseModel):
    trainer_id: UUID
    display_name: str
    status: str
    balance: int


class IncidentPurchase(BaseModel):
    id: UUID
    trainer_id: UUID
    display_name: str
    item_name: str
    item_code: str | None = None
    total_price: int
    status: Literal["pending", "used", "cancelled", "refunded"]
    acquisition_type: str
    purchased_at: datetime
    linked_operation: bool
    cancellable: bool
    refundable: bool


class IncidentRobbery(BaseModel):
    authorization_id: UUID
    purchase_id: UUID
    requester: str | None = None
    donor: str | None = None
    state: str | None = None
    source_obligation: str | None = None
    destination_obligation: str | None = None
    created_at: datetime


class IncidentHistory(BaseModel):
    operation_id: UUID
    kind: str
    actor: str | None = None
    target: str | None = None
    purchase_id: UUID | None = None
    amount: int
    reason: str
    status: str | None = None
    created_at: datetime


class IncidentOverview(BaseModel):
    season_id: UUID
    season_status: str
    wallets: list[IncidentWallet]
    purchases: list[IncidentPurchase]
    robberies: list[IncidentRobbery]
    history: list[IncidentHistory]
