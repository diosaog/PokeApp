"""API seam for paired robbery; absent unless explicitly configured.

Scope always comes from the authenticated principal. Any valid participant takes
part: identity, participation, ownership and the rules of the robbery are enforced
by the SQL functions. An optional allowlist remains as an operational brake. Peer
plans, raw object names, signed URLs and proofs never leave this boundary; no
route here can issue a proof.
"""

from app.repositories.errors import TransferRejectedError

SUMMARY = (
    "authorization_id",
    "side",
    "status",
    "obligation",
    "purchase_id",
    "pokemon_entity_id",
    "claimed",
    "apply_started",
    "verified",
    "accepted_save_id",
    "reason",
    "expires_at",
    "created_at",
)
LAUNCHER = SUMMARY + ("source_sha256", "result_sha256", "pair_id", "intent")
LEG = (
    "authorization_id",
    "side",
    "status",
    "obligation",
    "pair_id",
    "source_sha256",
    "apply_started",
    "result_sha256",
    "verified",
    "accepted_save_id",
)


class TransferIntegration:
    def __init__(self, repository, transport, *, allowed_trainers=()):
        self.repo, self.transport = repository, transport
        self.allowed = frozenset(allowed_trainers) or None

    def enabled(self, tid):
        return self.allowed is None or tid in self.allowed

    def _require(self, tid):
        if not self.enabled(tid):
            raise TransferRejectedError("TRANSFER_FORBIDDEN", 403)

    def board(self, sid, tid):
        self._require(tid)
        return self.repo.board({"season_id": sid, "trainer_id": tid})

    def request(self, sid, tid, purchase_id, pokemon_entity_id, operation_id):
        self._require(tid)
        owner = self.repo.target_owner(sid, pokemon_entity_id)
        if owner is None:
            raise TransferRejectedError("TRANSFER_TARGET_INVALID", 409)
        if owner == tid:
            raise TransferRejectedError("STEAL_SELF_TARGET", 409)
        if self.allowed is not None and owner not in self.allowed:
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
        if not self.enabled(tid):
            return []
        keys = LAUNCHER if launcher else SUMMARY
        return [{k: row.get(k) for k in keys} for row in self.repo.list(sid, tid)]

    def leg(self, sid, tid, aid, operation, *, claim_id=None, backup_sha256=None):
        self._require(tid)
        if (
            operation == "cancel"
            and self.leg(sid, tid, aid, "get")["side"] != "destination"
        ):
            # Owner rule: a valid robbery needs no consent; the victim cannot veto.
            raise TransferRejectedError("TRANSFER_VICTIM_CANNOT_CANCEL", 409)
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

    def candidate(self, sid, tid, aid, data):
        """Own CURRENT save when it no longer matches the plan; the verifier
        re-plans on it. Never a decision, never accepted as a result."""
        self._require(tid)
        return self._leg(self.transport.submit_candidate(aid, sid, tid, data), aid)

    def withdraw(self, sid, tid, aid):
        """Cancellation is the requester's choice only; the SQL still refuses
        once any side started applying."""
        return self.leg(sid, tid, aid, "cancel")

    @staticmethod
    def _leg(row, aid):
        if not isinstance(row, dict) or row.get("authorization_id") != aid:
            raise TransferRejectedError("TRANSFER_NOT_FOUND", 404)
        return {k: row.get(k) for k in LEG}
