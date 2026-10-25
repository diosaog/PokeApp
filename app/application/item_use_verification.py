"""Private bytes-verification service; not wired to a production route/issuer.

Authority and original bytes MUST come from trusted server storage. The client
supplies only its scoped authorization/claim identifiers and resulting bytes.
This proves the received artifact, never continuous use on a player's machine.
The repository must atomically recheck the captured context when recording,
reject incompatible proof replay, and retain result bytes before granting proof.
Neither the Launcher nor normal API service_role may insert proof rows.
"""

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256

from app.domain.pokemon_identity import digest, trusted_native_identity
from app.launcher.write_engine import WriteIntent
from app.save_parser.writer import NATIVE_SIZES


class VerificationRejected(Exception):
    pass


def require(ok, code):
    if not ok:
        raise VerificationRejected(code)


class TrustedItemUseVerification:
    def __init__(self, repository, parser, native, *, now=None):
        self.repository, self.parser, self.native = repository, parser, native
        self.now = now or (lambda: datetime.now(UTC))

    def _plan(self, authorization_id, season_id, trainer_id):
        c = self.repository.load(authorization_id, season_id, trainer_id)
        a, e, o, saved = c["authorization"], c["entity"], c["observation"], c["save"]
        require(
            a["id"] == authorization_id
            and a["season_id"] == season_id
            and a["trainer_id"] == trainer_id
            and a["effect_code"] == "revive",
            "AUTHORIZATION_SCOPE",
        )
        require(
            a["status"]
            in (
                "PREPARED",
                "PENDING_APPLICATION",
                "RECOVERY_REQUIRED",
                "BLOCKED_UNCERTAIN",
            ),
            "AUTHORIZATION_STATE",
        )
        require(
            datetime.fromisoformat(a["expires_at"]) > self.now(),
            "AUTHORIZATION_EXPIRED",
        )
        require(
            c["trainer_enabled"]
            and c["participant_active"]
            and c["purchase_pending"]
            and c["purchase_effect"] == "revive",
            "ENTITLEMENT_UNAVAILABLE",
        )
        require(
            saved["id"] == a["save_file_id"] == c["current_save_id"]
            and saved["trainer_id"] == trainer_id
            and saved["season_id"] == season_id
            and saved["sha256"] == a["save_sha256"]
            and c["head_id"] == a["identity_revision_id"],
            "SOURCE_CONTEXT_CHANGED",
        )
        require(
            e["id"] == a["target_pokemon_entity_id"] == o["pokemon_entity_id"]
            and e["owner_trainer_id"] == trainer_id
            and e["season_id"] == season_id
            and e["identity_status"] == "unambiguous"
            and o["revision_id"] == a["identity_revision_id"]
            and o["source"] == "box"
            and o["box_number"] == 8
            and o["outcome"] in ("NEW", "MATCHED"),
            "TARGET_UNPROVEN",
        )
        source = self.repository.read_source(saved)
        require(
            type(source) is bytes
            and len(source) in NATIVE_SIZES.values()
            and sha256(source).hexdigest() == saved["sha256"],
            "SOURCE_BYTES_UNPROVEN",
        )
        obs = self.parser.parse(source)
        require(
            obs.game in NATIVE_SIZES and len(source) == NATIVE_SIZES[obs.game],
            "UNSUPPORTED_GAME",
        )
        identity = {"game": obs.game, "trainer": obs.trainer.model_dump(mode="json")}
        require(
            saved["metadata"].get("save_identity") == identity,
            "SAVE_OWNERSHIP_UNPROVEN",
        )
        box = next((b for b in obs.boxes if b.number == 8), None)
        slot = o["slot_number"] - 1
        require(
            box is not None and 0 <= slot < 30 and box.slots[slot] is not None,
            "TARGET_MISSING",
        )
        p = box.slots[slot]
        evidence = trusted_native_identity(
            p.identity, trainer=obs.trainer, is_egg=p.is_egg
        )
        require(
            evidence.unresolved_reason is None
            and digest(asdict(evidence)) == digest(o["evidence"])
            and evidence.candidate_key == e["candidate_key"],
            "TARGET_IDENTITY_CHANGED",
        )
        require(
            sum(
                1
                for _, q in obs.occupied()
                if q.identity.pid == evidence.pid
                or q.identity.encryption_constant == evidence.encryption_constant
            )
            == 1,
            "TARGET_AMBIGUOUS",
        )
        destination = next(
            (
                (b.number - 1, i)
                for b in sorted(obs.boxes, key=lambda b: b.number)
                if 1 <= b.number <= 7
                for i, q in enumerate(b.slots)
                if q is None
            ),
            None,
        )
        require(destination is not None, "NO_FREE_SLOT")
        t = obs.trainer
        key = sha256(
            "\0".join(
                map(str, (obs.game, t.name, t.tid, t.sid, t.gender, t.language))
            ).encode()
        ).hexdigest()
        intent = WriteIntent.create(
            game=obs.game,
            expected_sha256=saved["sha256"],
            trainer_key=key,
            mutation={
                "kind": "revive",
                "location": "box",
                "box_index": 7,
                "slot_index": slot,
                "target_pid": evidence.pid,
                "target_ec": evidence.encryption_constant,
                "destination_box_index": destination[0],
                "destination_slot_index": destination[1],
            },
        )
        return c, source, intent

    def plan(self, authorization_id, season_id, trainer_id):
        return self._plan(authorization_id, season_id, trainer_id)[2]

    def verify(self, authorization_id, season_id, trainer_id, claim_id, result):
        require(
            type(result) is bytes and len(result) in NATIVE_SIZES.values(),
            "INVALID_RESULT",
        )
        c, source, intent = self._plan(authorization_id, season_id, trainer_id)
        a = c["authorization"]
        require(
            a["status"] != "PREPARED"
            and claim_id is not None
            and a["claim_id"] == claim_id,
            "CLAIM_MISMATCH",
        )
        prepared = self.native.prepare(source, intent)
        self.native.verify(source, result, intent, prepared)
        # Reparse submitted bytes independently too; no local receipt/hash trusted.
        self.parser.parse(result)
        proof = {
            "authorization_id": a["id"],
            "claim_id": claim_id,
            "operation_id": a["operation_id"],
            "source_sha256": sha256(source).hexdigest(),
            "result_sha256": sha256(result).hexdigest(),
            "target_pokemon_entity_id": a["target_pokemon_entity_id"],
            "identity_revision_id": a["identity_revision_id"],
            "native_operation_id": intent.operation_id,
            "plan_sha256": digest(
                {
                    "authorization": {
                        k: a[k]
                        for k in (
                            "id",
                            "operation_id",
                            "purchase_id",
                            "season_id",
                            "trainer_id",
                            "claim_id",
                            "save_file_id",
                            "save_sha256",
                            "identity_revision_id",
                            "target_pokemon_entity_id",
                            "expires_at",
                        )
                    },
                    "native_intent": intent.to_payload(),
                    "writer_version": self.native.version,
                }
            ),
        }
        self.repository.record_verified(c, proof, result)
        return proof
