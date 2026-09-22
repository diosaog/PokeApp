from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any

from app.domain.normal_purchases import NormalPurchaseReceipt, NormalPurchaseRequest
from app.repositories.errors import PersistenceError, PurchaseRejectedError


REJECTIONS = {
    "trainer_disabled": 403, "participant_inactive": 403, "store_banned": 403,
    "season_not_found": 404, "item_not_found": 404,
    "season_not_active": 409, "current_matchday_required": 409,
    "current_matchday_invalid": 409, "item_unavailable": 409,
    "promotion_pending": 409, "promotion_available": 409,
    "base_price_confirmation_required": 409, "insufficient_funds": 409,
    "idempotency_conflict": 409, "invalid_purchase_request": 409,
}


class SupabaseNormalPurchaseRepository:
    def __init__(self, client: Any):
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str) -> "SupabaseNormalPurchaseRepository":
        from supabase import create_client

        return cls(create_client(url, service_role_key))

    def create_normal_purchase(self, request: NormalPurchaseRequest) -> NormalPurchaseReceipt:
        try:
            data = self._client.rpc("api_create_normal_purchase", {
                "p_" + key: value for key, value in asdict(request).items()
            }).execute().data
        except Exception as exc:
            code = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(code)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise PurchaseRejectedError(code.upper(), status) from exc
            raise PersistenceError("Purchase backend is unavailable.") from exc
        try:
            receipt = NormalPurchaseReceipt(**{f.name: data[f.name] for f in fields(NormalPurchaseReceipt)})
            if any(getattr(receipt, key) != getattr(request, key) for key in ("season_id", "trainer_id", "item_id")):
                raise ValueError("Mismatched purchase receipt")
            return receipt
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise PersistenceError("Purchase backend returned an invalid receipt.") from exc
