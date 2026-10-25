"""Untrusted result intake; never issues proof or consumes an entitlement."""

from hashlib import sha256
from threading import BoundedSemaphore

from app.repositories.errors import ItemUseRejectedError
from app.save_parser.writer import NATIVE_SIZES


def public_receipt(row):
    # No raw object names, signed URLs, source identities or worker leases escape.
    return {
        key: row[key]
        for key in ("authorization_id", "status", "result_sha256")
        if key in row
    }


class ItemUseTransport:
    def __init__(self, repository, blobs, *, allowed_trainers):
        self.repository, self.blobs = repository, blobs
        self.allowed_trainers = frozenset(allowed_trainers)
        self.slots = BoundedSemaphore(2)

    def scope(self, aid, sid, tid, claim):
        if tid not in self.allowed_trainers:
            raise ItemUseRejectedError("ITEM_USE_FORBIDDEN", 403)
        return {
            "authorization_id": aid,
            "season_id": sid,
            "trainer_id": tid,
            "claim_id": claim,
        }

    def status(self, aid, sid, tid, claim):
        return public_receipt(
            self.repository.execute(
                self.scope(aid, sid, tid, claim) | {"operation": "get"}
            )
        )

    def submit(self, aid, sid, tid, claim, data):
        scope = self.scope(aid, sid, tid, claim)
        if type(data) is not bytes or len(data) not in NATIVE_SIZES.values():
            raise ItemUseRejectedError("INVALID_RESULT_SIZE", 422)
        if not self.slots.acquire(blocking=False):
            raise ItemUseRejectedError("VERIFICATION_BUSY", 429)
        try:
            digest = sha256(data).hexdigest()
            row = self.repository.execute(
                scope
                | {
                    "operation": "reserve",
                    "result_sha256": digest,
                    "byte_size": len(data),
                }
            )
            if row["status"] in ("VERIFIED", "REJECTED", "EXPIRED"):
                return public_receipt(row)
            self.blobs.put(row["storage_key"], data, digest)
            # URLs are server-to-worker capabilities, short-lived and kept private.
            row = self.repository.execute(
                scope
                | {
                    "operation": "queue",
                    "result_sha256": digest,
                    "source_url": self.blobs.sign(row["source_key"]),
                    "result_url": self.blobs.sign(row["storage_key"]),
                }
            )
            return public_receipt(row)
        finally:
            self.slots.release()
