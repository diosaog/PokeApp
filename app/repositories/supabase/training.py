"""Service-only virtual training RPC and canonical trusted-save bytes."""

from hashlib import sha256

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

ERRORS = {
    **dict.fromkeys(("training_participant_required",), 403),
    **dict.fromkeys(("training_not_found",), 404),
    **dict.fromkeys(("training_invalid_request",), 422),
    **dict.fromkeys(("training_season_inactive", "training_save_required", "training_save_busy",
                    "training_competitive_lock", "training_already_applied", "training_idempotency_conflict",
                    "training_not_reserved", "training_purchase_unavailable", "training_source_changed",
                    "training_verification_required", "training_reconciliation_required"), 409),
}


class SupabaseTrainingRepository:
    def __init__(self, client):
        self.client = client

    def execute(self, operation, season_id, trainer_id, **values):
        try:
            return self.client.rpc("api_training_operation", {"r": {
                "operation": operation, "season_id": season_id, "trainer_id": trainer_id, **values,
            }}).execute().data
        except Exception as error:
            code = str(getattr(error, "message", ""))
            status = ERRORS.get(code)
            if status and str(getattr(error, "code", "")) == f"PT{status}":
                raise SeasonAdminRejected(code.upper(), status) from None
            raise PersistenceError("Virtual training unavailable") from None

    def read_source(self, saved):
        # Never use a client URL or path. Only the immutable accepted server row.
        key = saved["storage_key"]
        expected = f"trusted/{saved['trainer_id']}/{saved['season_id']}/{saved['sha256']}.sav"
        if saved["storage_bucket"] != "raw-saves" or key != expected:
            raise PersistenceError("Training source is not trusted")
        try:
            data = self.client.storage.from_("raw-saves").download(key)
        except Exception:
            raise PersistenceError("Training source unavailable") from None
        if type(data) is not bytes or sha256(data).hexdigest() != saved["sha256"]:
            raise PersistenceError("Training source changed")
        return data

    def store_raw(self, key, data, digest):
        # Reuse deterministic, non-overwriting trusted-save storage semantics.
        from app.repositories.supabase.save_ingestion import SupabaseSaveIngestionRepository

        SupabaseSaveIngestionRepository(self.client).store_raw(key, data, digest)
