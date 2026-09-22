from __future__ import annotations

from uuid import UUID

from app.domain.shop_eligibility import CompetitiveMatchday
from app.repositories.errors import ConflictError, NotFoundError, PersistenceError


class SupabaseShopEligibilityRepository:
    def __init__(self, client):
        self._client = client

    def _rpc(self, name, args):
        try:
            return self._client.rpc(name, args).execute().data
        except Exception as exc:
            error = {"PT404": NotFoundError, "PT409": ConflictError}.get(str(getattr(exc, "code", "")), PersistenceError)
            raise error("Shop eligibility is unavailable or invalid.") from exc

    def resolve_current_matchday(self, season_id: str) -> CompetitiveMatchday:
        season_id = str(UUID(season_id))
        rows = self._rpc("api_resolve_current_matchday", {"p_season_id": season_id})
        try:
            if not isinstance(rows, list) or len(rows) != 1 or rows[0]["season_id"] != season_id:
                raise ValueError("invalid receipt")
            return CompetitiveMatchday(**{key: rows[0][key] for key in ("id", "season_id", "number", "status")})
        except (ValueError, KeyError, TypeError) as exc:
            raise PersistenceError("Invalid competitive matchday receipt.") from exc

    def is_store_banned(self, season_id: str, trainer_id: str, current_matchday_number: int) -> bool:
        if type(current_matchday_number) is not int or current_matchday_number <= 0:
            raise ValueError("invalid_current_matchday")
        value = self._rpc("api_is_store_banned", {"p_season_id": str(UUID(season_id)),
            "p_trainer_id": str(UUID(trainer_id)), "p_matchday_number": current_matchday_number})
        if type(value) is not bool:
            raise PersistenceError("Invalid store-ban receipt.")
        return value
