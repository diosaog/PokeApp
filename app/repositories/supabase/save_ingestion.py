from hashlib import sha256

from httpx import HTTPError
from storage3.exceptions import StorageApiError

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected


class SupabaseSaveIngestionRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client

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
                raise SeasonAdminRejected(
                    "SAVE_REQUEST_REJECTED", int(code[2:])
                ) from error
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
