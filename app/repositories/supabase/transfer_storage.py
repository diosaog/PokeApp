"""Private worker storage for robberies. Never loaded by the public API.

Reads the server-held accepted saves the decision is based on, and stores
immutable registration/basis bytes. Keys are deterministic and never
overwritten; a lost upload reply is reconciled by reading the exact bytes.
"""

from hashlib import sha256

from httpx import HTTPError
from storage3.exceptions import StorageApiError

from app.repositories.errors import PersistenceError

WRITABLE = ("trusted/", "transfer-basis/")


class PrivateTransferStorage:
    def __init__(self, client):
        self.bucket = client.storage.from_("raw-saves")

    def read_source(self, saved):
        key = saved.get("storage_key")
        if not isinstance(key, str) or not key.startswith(WRITABLE):
            raise PersistenceError("Invalid private save.")
        try:
            return self.bucket.download(key)
        except (HTTPError, StorageApiError):
            raise PersistenceError("Private save storage unavailable.") from None

    def store_raw(self, key, data, digest):
        if (
            not isinstance(key, str)
            or not key.startswith(WRITABLE)
            or sha256(data).hexdigest() != digest
        ):
            raise PersistenceError("Invalid private save.")
        try:
            self.bucket.upload(
                key,
                data,
                {"content-type": "application/octet-stream", "upsert": "false"},
            )
        except (HTTPError, StorageApiError):
            try:
                if sha256(self.bucket.download(key)).hexdigest() == digest:
                    return
            except (HTTPError, StorageApiError):
                pass
            raise PersistenceError("Private save storage unavailable.") from None
