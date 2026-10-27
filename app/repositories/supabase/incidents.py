"""Admin incident center: one service-only RPC per command (062, robbery 064).

A mutation is never retried here: the caller retries with the same operation
id, and the database returns the stored receipt instead of a second effect.
"""

from typing import Protocol

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

ERRORS = {
    "admin_required": ("ADMIN_REQUIRED", 403),
    "season_not_found": ("SEASON_NOT_FOUND", 404),
    "purchase_not_found": ("PURCHASE_NOT_FOUND", 404),
    "robbery_not_found": ("ROBBERY_NOT_FOUND", 404),
    "robbery_already_cancelled": ("ROBBERY_ALREADY_CANCELLED", 409),
    "admin_incident_robbery_once": ("ROBBERY_ALREADY_CANCELLED", 409),
    "robbery_reconciliation_required": ("ROBBERY_RECONCILIATION_REQUIRED", 409),
    "participant_not_found": ("PARTICIPANT_NOT_FOUND", 404),
    "idempotency_conflict": ("IDEMPOTENCY_CONFLICT", 409),
    "purchase_not_cancellable": ("PURCHASE_NOT_CANCELLABLE", 409),
    "purchase_not_refundable": ("PURCHASE_NOT_REFUNDABLE", 409),
    "purchase_linked_to_save_operation": ("PURCHASE_LINKED_TO_SAVE_OPERATION", 409),
    "coin_purchase_reversal_once": ("PURCHASE_ALREADY_REVERSED", 409),
    "admin_incident_purchase_once": ("PURCHASE_ALREADY_REVERSED", 409),
    "insufficient_funds": ("INSUFFICIENT_FUNDS", 409),
    "historical_artifact_immutable": ("HISTORICAL_ARTIFACT_IMMUTABLE", 409),
    "item_unavailable": ("ITEM_UNAVAILABLE", 409),
    "incident_reason_required": ("INCIDENT_REASON_REQUIRED", 422),
    "invalid_incident_request": ("INVALID_INCIDENT_REQUEST", 422),
}


class IncidentRepository(Protocol):
    def read(self, actor: str, season: str) -> dict: ...

    def resolve_purchase(
        self, actor, season, purchase, kind, operation, digest, reason
    ) -> dict: ...

    def adjust_coins(
        self, actor, season, trainer, amount, operation, digest, reason
    ) -> dict: ...

    def cancel_robbery(
        self, actor, season, authorization, operation, digest, reason
    ) -> dict: ...


class SupabaseIncidentRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client

        return cls(create_client(url, key))

    def _rpc(self, name, params):
        try:
            return self.client.rpc(name, params).execute().data
        except Exception as exc:  # noqa: BLE001 - every client failure maps to a stable code or a 503
            text = f"{getattr(exc, 'message', '')} {exc}"
            for marker, (code, status) in ERRORS.items():
                if marker in text:
                    raise SeasonAdminRejected(code, status) from None
            raise PersistenceError("Incident backend unavailable") from None

    def read(self, actor, season):
        return self._rpc("admin_incident_read", {"p_actor": actor, "p_season": season})

    def resolve_purchase(
        self, actor, season, purchase, kind, operation, digest, reason
    ):
        return self._rpc(
            "admin_purchase_resolve",
            {
                "p_actor": actor,
                "p_season": season,
                "p_purchase": purchase,
                "p_kind": kind,
                "p_operation": operation,
                "p_hash": digest,
                "p_reason": reason,
            },
        )

    def cancel_robbery(self, actor, season, authorization, operation, digest, reason):
        return self._rpc(
            "admin_robbery_cancel",
            {
                "p_actor": actor,
                "p_season": season,
                "p_authorization": authorization,
                "p_operation": operation,
                "p_hash": digest,
                "p_reason": reason,
            },
        )

    def adjust_coins(self, actor, season, trainer, amount, operation, digest, reason):
        return self._rpc(
            "admin_coin_adjust",
            {
                "p_actor": actor,
                "p_season": season,
                "p_trainer": trainer,
                "p_amount": amount,
                "p_operation": operation,
                "p_hash": digest,
                "p_reason": reason,
            },
        )
