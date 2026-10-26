"""Server-side scope must originate from verified identity, never a public DTO.

Only the disabled-by-default engineering transfer service wires this repository.
"""

from app.repositories.errors import PersistenceError, TransferRejectedError

REJECTIONS = {
    "trainer_disabled": 403,
    "transfer_not_owned": 403,
    "transfer_not_found": 404,
    "invalid_transfer": 422,
    "invalid_transfer_operation": 422,
    "transfer_conflict": 409,
    "transfer_target_invalid": 409,
    "participant_inactive": 409,
    "purchase_not_redeemable": 409,
    "save_context_changed": 409,
    "transfer_native_scope_unqualified": 409,
    "steal_target_shielded": 409,
    "steal_victim_already_robbed": 409,
    "transfer_reserved": 409,
    "transfer_expired": 409,
    "transfer_claim_conflict": 409,
    "transfer_not_planned": 409,
    "transfer_peer_pending": 409,
    "transfer_not_started": 409,
    "transfer_result_conflict": 409,
    "transfer_not_reserved": 409,
    "transfer_assisted_recovery_required": 409,
    "transfer_terminal": 409,
    "transfer_reconciliation_required": 409,
    "transfer_not_adjudicated": 409,
    "transfer_adjudicated": 409,
    "transfer_leg_settled": 409,
    "transfer_candidate_conflict": 409,
    "transfer_cross_title_forbidden": 409,
}


class TransferRepository:
    def __init__(self, client):
        self.client = client

    def _call(self, name, request):
        try:
            return self.client.rpc(name, {"p_request": request}).execute().data
        except Exception as exc:  # noqa: BLE001 - sanitized repository boundary; no fallback/retry
            code = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(code)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise TransferRejectedError(code.upper(), status) from None
            raise PersistenceError("transfer_unavailable") from None

    def reserve(self, request):
        return self._call("api_prepare_transfer", request)

    def leg(self, request):
        return self._call("api_transfer_leg", request)

    def list(self, season_id, trainer_id):
        rows = self._call(
            "api_transfer_list", {"season_id": season_id, "trainer_id": trainer_id}
        )
        if not isinstance(rows, list):
            raise PersistenceError("transfer_unavailable")
        return rows

    def target_owner(self, season_id, pokemon_entity_id):
        try:
            rows = (
                self.client.table("pokemon_entities")
                .select("owner_trainer_id")
                .eq("id", pokemon_entity_id)
                .eq("season_id", season_id)
                .limit(1)
                .execute()
                .data
            )
        except Exception:  # noqa: BLE001
            raise PersistenceError("transfer_unavailable") from None
        return rows[0]["owner_trainer_id"] if rows else None
