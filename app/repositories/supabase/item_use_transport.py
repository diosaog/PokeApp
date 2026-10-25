"""API-side artifact storage only. No proof-issuance credential is loaded here."""

from hashlib import sha256

from httpx import HTTPError
from storage3.exceptions import StorageApiError

from app.repositories.errors import PersistenceError
from app.repositories.supabase.item_use import SupabaseItemUseRepository


class SupabaseItemUseTransport(SupabaseItemUseRepository):
    def execute(self, request):
        return self._rpc("api_item_use_artifact", {"p_request": request})


class PrivateItemUseBlobs:
    def __init__(self, client):
        self.bucket = client.storage.from_("raw-saves")

    def put(self, key, data, digest):
        if not key.startswith("item-use/") or sha256(data).hexdigest() != digest:
            raise PersistenceError("Invalid private artifact.")
        try:
            self.bucket.upload(
                key,
                data,
                {"content-type": "application/octet-stream", "upsert": "false"},
            )
        except (HTTPError, StorageApiError):
            # Lost write response or collision: reconcile exact existing bytes.
            # Never overwrite/delete an unknown accepted result, never auto-consume.
            try:
                if sha256(self.bucket.download(key)).hexdigest() == digest:
                    return
            except (HTTPError, StorageApiError):
                pass
            raise PersistenceError("Private artifact storage unavailable.") from None

    def sign(self, key):
        if not isinstance(key, str) or not key.startswith(("trusted/", "item-use/")):
            raise PersistenceError("Invalid private artifact.")
        try:
            return self.bucket.create_signed_url(key, 180)["signedURL"]
        except (HTTPError, StorageApiError, KeyError):
            raise PersistenceError("Private artifact transport unavailable.") from None
