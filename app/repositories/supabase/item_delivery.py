"""Service-role transport for 072: one RPC per command, reads for the views."""

from app.repositories.errors import ItemDeliveryRejectedError, PersistenceError

REJECTIONS = {
    "invalid_delivery_request": 422,
    "trainer_disabled": 403,
    "participant_inactive": 403,
    "purchase_not_found": 404,
    "delivery_not_found": 404,
    "purchase_not_redeemable": 409,
    "delivery_in_progress": 409,
    "delivery_not_supported": 409,
    "delivery_not_reserved": 409,
    "delivery_already_completed": 409,
    "idempotency_conflict": 409,
}


class SupabaseItemDeliveryRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, service_role_key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, service_role_key))

    def _rpc(self, name, args):
        try:
            data = self._client.rpc(name, args).execute().data
        except Exception as exc:
            message = str(getattr(exc, "message", ""))
            status = REJECTIONS.get(message)
            if status and str(getattr(exc, "code", "")) == f"PT{status}":
                raise ItemDeliveryRejectedError(message.upper(), status) from exc
            raise PersistenceError("Item delivery backend unavailable.") from exc
        if not isinstance(data, dict) or "status" not in data:
            raise PersistenceError("Invalid item delivery receipt.")
        return data

    def reserve(self, season_id, trainer_id, purchase_id, operation_id, item_code, game_item_id, game):
        return self._rpc(
            "api_reserve_item_delivery",
            {
                "p_season_id": season_id,
                "p_trainer_id": trainer_id,
                "p_purchase_id": purchase_id,
                "p_operation_id": operation_id,
                "p_item_code": item_code,
                "p_game_item_id": game_item_id,
                "p_game": game,
            },
        )

    def complete(self, season_id, trainer_id, operation_id, source_sha256, output_sha256):
        return self._rpc(
            "api_complete_item_delivery",
            {
                "p_season_id": season_id,
                "p_trainer_id": trainer_id,
                "p_operation_id": operation_id,
                "p_source_sha256": source_sha256,
                "p_output_sha256": output_sha256,
            },
        )

    def release(self, season_id, trainer_id, operation_id):
        return self._rpc(
            "api_release_item_delivery",
            {"p_season_id": season_id, "p_trainer_id": trainer_id, "p_operation_id": operation_id},
        )

    def use_permission(self, season_id, trainer_id, purchase_id, operation_id):
        return self._rpc(
            "api_use_permission_item",
            {
                "p_season_id": season_id,
                "p_trainer_id": trainer_id,
                "p_purchase_id": purchase_id,
                "p_operation_id": operation_id,
            },
        )

    def _rows(self, table, columns, **filters):
        try:
            query = self._client.table(table).select(columns)
            for key, value in filters.items():
                query = query.eq(key, value)
            return query.execute().data or []
        except Exception as exc:
            raise PersistenceError("Item delivery backend unavailable.") from exc

    def purchase_code(self, season_id, trainer_id, purchase_id):
        """The shop item code of this trainer's purchase, or None."""
        rows = self._rows(
            "purchases", "shop_item_id", id=purchase_id, season_id=season_id, trainer_id=trainer_id
        )
        if not rows:
            return None
        items = self._rows("shop_items", "code", id=rows[0]["shop_item_id"])
        return items[0]["code"] if items else None

    def item_code(self, item_id):
        rows = self._rows("shop_items", "code", id=item_id)
        return rows[0]["code"] if rows else None

    def promotion_item_code(self, season_id, promotion_id):
        rows = self._rows("shop_promotions", "shop_item_id", id=promotion_id, season_id=season_id)
        return self.item_code(rows[0]["shop_item_id"]) if rows else None

    def purchases(self, season_id, trainer_id):
        """This trainer's paid purchases in the season, with the item code."""
        rows = [
            r
            for r in self._rows(
                "purchases",
                "id,shop_item_id,status,acquisition_type",
                season_id=season_id,
                trainer_id=trainer_id,
            )
            if r["acquisition_type"] == "paid"
        ]
        if not rows:
            return []
        catalog = {i["id"]: i for i in self._rows("shop_items", "id,code,name")}
        return [
            {
                "id": r["id"],
                "status": r["status"],
                "code": catalog[r["shop_item_id"]]["code"],
                "name": catalog[r["shop_item_id"]]["name"],
            }
            for r in rows
            if r["shop_item_id"] in catalog
        ]

    def deliveries(self, season_id, trainer_id):
        """Every delivery row of this trainer in this season (all states)."""
        return self._rows(
            "item_deliveries",
            "purchase_id,operation_id,kind,item_code,game_item_id,game,status,reserved_at,finished_at",
            season_id=season_id,
            trainer_id=trainer_id,
        )
