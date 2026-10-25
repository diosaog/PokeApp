from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.repositories.errors import ItemUseRejectedError, PersistenceError


REJECTIONS = {
    "trainer_disabled": 403,
    "item_use_forbidden": 403,
    "participant_inactive": 403,
    "season_not_found": 404,
    "purchase_not_found": 404,
    "item_use_not_found": 404,
    "invalid_item_use_request": 409,
    "invalid_item_use_completion": 409,
    "item_use_conflict": 409,
    "purchase_not_redeemable": 409,
    "item_use_not_required": 409,
    "save_context_changed": 409,
    "pokemon_target_invalid": 409,
    "pokemon_not_owned": 409,
    "steal_self_target": 409,
    "pokemon_identity_ambiguous": 409,
    "pokemon_not_revivable": 409,
    "steal_target_ineligible": 409,
}


class SupabaseItemUseRepository:
    def __init__(self, client: Any):
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str):
        from supabase import create_client

        return cls(create_client(url, service_role_key))

    def _rpc(self, name: str, args: dict):
        try:
            data = self._client.rpc(name, args).execute().data
        except Exception as exc:
            code = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(code)
            if status:
                raise ItemUseRejectedError(code.upper(), status) from exc
            raise PersistenceError("Item-use backend unavailable.") from exc
        if not isinstance(data, dict) and not isinstance(data, list):
            raise PersistenceError("Item-use backend returned an invalid receipt.")
        return data

    def prepare(self, request):
        return self._rpc(
            "api_prepare_item_use",
            {"p_" + key: value for key, value in asdict(request).items()},
        )

    def complete(self, authorization_id: str, season_id: str, trainer_id: str, request):
        return self._rpc(
            "api_complete_item_use",
            {
                "p_authorization_id": authorization_id,
                "p_season_id": season_id,
                "p_trainer_id": trainer_id,
                "p_operation_id": request["operation_id"],
                "p_status": request["status"],
                "p_observed_sha256": request.get("observed_sha256"),
                "p_error_code": request.get("error_code"),
            },
        )

    def list(self, season_id: str, trainer_id: str):
        data = self._rpc(
            "api_list_item_uses",
            {"p_season_id": season_id, "p_trainer_id": trainer_id},
        )
        if not isinstance(data, list):
            raise PersistenceError("Item-use list is invalid.")
        return data
