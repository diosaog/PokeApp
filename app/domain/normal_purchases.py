from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NormalPurchaseRequest:
    season_id: str
    trainer_id: str
    item_id: str
    idempotency_key: str
    confirm_base_price: bool = False

    def __post_init__(self):
        for value in (self.season_id, self.trainer_id, self.item_id):
            UUID(value)
        if not 1 <= len(self.idempotency_key) <= 128 or any(not 33 <= ord(c) <= 126 for c in self.idempotency_key):
            raise ValueError("invalid_idempotency_key")
        if type(self.confirm_base_price) is not bool:
            raise ValueError("invalid_confirmation")


@dataclass(frozen=True)
class NormalPurchaseReceipt:
    id: str
    season_id: str
    trainer_id: str
    season_player_id: str
    item_id: str
    quantity: int
    unit_price: int
    total_price: int
    status: str
    purchased_at: str
    balance_after: int
    ledger_id: str
    event_id: str
    matchday_id: str
    matchday_number: int

    def __post_init__(self):
        for value in (self.id, self.season_id, self.trainer_id, self.season_player_id,
                      self.item_id, self.ledger_id, self.event_id, self.matchday_id):
            UUID(value)
        date = datetime.fromisoformat(self.purchased_at)
        if date.tzinfo is None:
            raise ValueError("invalid_receipt_date")
        for value in (self.quantity, self.unit_price, self.total_price, self.balance_after, self.matchday_number):
            if type(value) is not int:
                raise ValueError("invalid_receipt_number")
        if (self.quantity != 1 or self.unit_price <= 0 or self.unit_price != self.total_price
                or self.balance_after < 0 or self.matchday_number <= 0 or self.status != "pending"):
            raise ValueError("invalid_purchase_receipt")
