"""Engineering-only API seam for paired robbery; absent unless explicitly configured.

Scope always comes from the authenticated principal. BOTH participants must be in
the restricted engineering cohort, so a reservation never blocks the sync of a
trainer whose Launcher cannot take part. Peer plans, raw object names, signed
URLs and proofs never leave this boundary; no route here can issue a proof.
"""

from app.repositories.errors import TransferRejectedError

SUMMARY = (
    "authorization_id",
    "side",
    "status",
    "purchase_id",
    "pokemon_entity_id",
    "claimed",
    "apply_started",
    "verified",
    "accepted_save_id",
    "expires_at",
    "created_at",
)
LAUNCHER = SUMMARY + ("source_sha256", "result_sha256", "intent")
LEG = (
    "authorization_id",
    "side",
    "status",
    "source_sha256",
    "apply_started",
    "result_sha256",
    "verified",
    "accepted_save_id",
)


class TransferIntegration:
    def __init__(self, repository, transport, *, allowed_trainers):
        self.repo, self.transport = repository, transport
        self.allowed = frozenset(allowed_trainers)

    def enabled(self, tid):
        return tid in self.allowed

    def _require(self, tid):
        if tid not in self.allowed:
            raise TransferRejectedError("TRANSFER_FORBIDDEN", 403)

    def request(self, sid, tid, purchase_id, pokemon_entity_id, operation_id):
        self._require(tid)
        owner = self.repo.target_owner(sid, pokemon_entity_id)
        if owner is None or owner == tid:
            raise TransferRejectedError("TRANSFER_TARGET_INVALID", 409)
        if owner not in self.allowed:
            raise TransferRejectedError("TRANSFER_PEER_UNAVAILABLE", 409)
        result = self.repo.reserve(
            {
                "season_id": sid,
                "trainer_id": tid,
                "purchase_id": purchase_id,
                "pokemon_entity_id": pokemon_entity_id,
                "operation_id": operation_id,
            }
        )
        return {k: result[k] for k in ("authorization_id", "status")}

    def list(self, sid, tid, *, launcher=False):
        if tid not in self.allowed:
            return []
        keys = LAUNCHER if launcher else SUMMARY
        return [{k: row.get(k) for k in keys} for row in self.repo.list(sid, tid)]

    def leg(self, sid, tid, aid, operation, *, claim_id=None, backup_sha256=None):
        self._require(tid)
        request = {
            "operation": operation,
            "authorization_id": aid,
            "season_id": sid,
            "trainer_id": tid,
        }
        if claim_id is not None:
            request["claim_id"] = claim_id
        if backup_sha256 is not None:
            request["backup_sha256"] = backup_sha256
        return self._leg(self.repo.leg(request), aid)

    def submit(self, sid, tid, aid, claim_id, data):
        self._require(tid)
        return self._leg(self.transport.submit(aid, sid, tid, claim_id, data), aid)

    def withdraw(self, sid, tid, aid):
        """Web cancellation is the requester's choice only; the SQL still refuses
        once any side started applying."""
        if self.leg(sid, tid, aid, "get")["side"] != "destination":
            raise TransferRejectedError("TRANSFER_NOT_OWNED", 403)
        return self.leg(sid, tid, aid, "cancel")

    @staticmethod
    def _leg(row, aid):
        if not isinstance(row, dict) or row.get("authorization_id") != aid:
            raise TransferRejectedError("TRANSFER_NOT_FOUND", 404)
        return {k: row.get(k) for k in LEG}
