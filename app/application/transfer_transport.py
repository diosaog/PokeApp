"""Disabled-by-default paired artifact seam; no public route or proof issuer."""

from hashlib import sha256

from app.application.item_use_verification import require
from app.save_parser.writer import NATIVE_SIZES


class TransferTransport:
    def __init__(self, repository, blobs):
        self.repository, self.blobs = repository, blobs

    def status(self, aid, sid, tid, claim):
        return self.repository.leg(
            {
                "operation": "get",
                "authorization_id": aid,
                "season_id": sid,
                "trainer_id": tid,
                "claim_id": claim,
            }
        )

    def submit(self, aid, sid, tid, claim, data):
        require(
            type(data) is bytes and len(data) in NATIVE_SIZES.values(), "TRANSFER_SIZE"
        )
        scope = {
            "authorization_id": aid,
            "season_id": sid,
            "trainer_id": tid,
            "claim_id": claim,
        }
        job = self.repository.leg(
            dict(
                **scope,
                operation="reserve_result",
                result_sha256=sha256(data).hexdigest(),
                byte_size=len(data),
            )
        )
        self.blobs.put(job["result_key"], data, job["result_sha256"])
        return self.repository.leg(
            dict(
                **scope,
                operation="queue_result",
                result_url=self.blobs.sign(job["result_key"]),
            )
        )
