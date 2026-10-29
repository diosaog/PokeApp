from hashlib import sha256

from httpx import HTTPError
from storage3.exceptions import StorageApiError

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

# The SQL reason, as a stable public code the Launcher can explain. Anything
# else stays the generic refusal; no SQL text ever reaches a client.
REJECTIONS = {
    "save_owner_required": "SEASON_PARTICIPANT_REQUIRED",
    "save_context_not_active": "SEASON_NOT_ACCEPTING_SAVES",
    "save_current_changed": "SAVE_CONTEXT_CHANGED",
    "save_identity_changed": "SAVE_IDENTITY_CHANGED",
    "save_identity_other_owner": "SAVE_IDENTITY_OTHER_OWNER",
    "save_not_registered": "SAVE_NOT_REGISTERED",
    "save_parse_changed": "SAVE_PARSE_MISMATCH",
    "save_existing_unproven": "SAVE_EXISTING_UNPROVEN",
    "transfer_reconciliation_required": "TRANSFER_RECONCILIATION_REQUIRED",
}


class SupabaseSaveIngestionRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def execute(self, operation, request):
        try:
            return (
                self._client.rpc(
                    "api_register_save",
                    {"p_request": request | {"operation": operation}},
                )
                .execute()
                .data
            )
        except Exception as error:
            code = str(getattr(error, "code", ""))
            if code in ("PT403", "PT404", "PT409", "PT422"):
                reason = REJECTIONS.get(
                    str(getattr(error, "message", "")), "SAVE_REQUEST_REJECTED"
                )
                raise SeasonAdminRejected(reason, int(code[2:])) from error
            raise PersistenceError("save_registration_unavailable") from error

    def store_raw(self, key, data, raw_hash):
        bucket = self._client.storage.from_("raw-saves")
        try:
            bucket.upload(
                key,
                data,
                {"content-type": "application/octet-stream", "upsert": "false"},
            )
        except (HTTPError, StorageApiError):
            # Includes an unknown upload outcome. Read the immutable deterministic key,
            # never overwrite it and never delete possibly accepted source bytes.
            try:
                if sha256(bucket.download(key)).hexdigest() == raw_hash:
                    return
            except (HTTPError, StorageApiError) as error:
                raise PersistenceError("raw_save_storage_unavailable") from error
            raise PersistenceError("raw_save_storage_unavailable") from None
