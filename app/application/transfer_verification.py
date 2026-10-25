"""Private paired verifier, reusing native/Storage boundaries from23D.

The result is two verified artifacts, NOT proof of continued local possession,
competitive completion or permission to consume an entitlement.
"""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256

from app.application.item_use_verification import require
from app.application.save_ingestion import registration_request
from app.domain.pokemon_identity import digest, trusted_native_identity


class TransferVerification:
    def __init__(self, rpc, read_source, reader, parser, native, *, store_raw=None):
        self.rpc, self.read_source, self.reader = rpc, read_source, reader
        self.parser, self.native = parser, native
        self.store_raw = store_raw

    def finalization_request(self, aid):
        """Private server-side parse/store boundary, never a Launcher payload.

        Storage is immutable and precedes the atomic SQL operation. Failed SQL may
        leave unreferenced private bytes, never a partial competitive transfer.
        """
        require(self.store_raw is not None, "TRANSFER_ACCEPTANCE_STORAGE_REQUIRED")
        c, originals, plans, prepared = self.derive(aid)
        registration = self.rpc(
            {"operation": "registration_context", "authorization_id": aid}
        )
        require(registration["context"] == c, "TRANSFER_CONTEXT_CHANGED")
        requests = {}
        entity = c["entity"]
        for side in ("source", "destination"):
            job = self.rpc(
                {"operation": "artifact", "authorization_id": aid, "side": side}
            )
            require(job["proof"] is not None, "TRANSFER_BOTH_PROOFS_REQUIRED")
            result = self.reader.read(
                job["result_url"],
                job["result_key"],
                job["result_sha256"],
                job["byte_size"],
            )
            self.native.verify(originals[side], result, plans[side], prepared[side])
            observed = self.parser.parse(result)
            context = deepcopy(registration["registration"][side])
            if side == "source":
                context["entities"] = [
                    e for e in context["entities"] if e["id"] != entity["id"]
                ]
                context["foreign_transfer_evidence"].append(entity["initial_evidence"])
            else:
                context["entities"].append(entity)
                context["proven_entity_ids"].append(entity["id"])
            leg = c["legs"][side]
            request = registration_request(
                c["authorization"]["season_id"],
                leg["trainer_id"],
                job["result_sha256"],
                leg["save"]["id"],
                observed,
                self.parser.version,
                context,
            )
            self.store_raw(request["storage_key"], result, job["result_sha256"])
            requests[side] = request
        return {
            "operation": "finalize",
            "authorization_id": aid,
            "context": c,
            "requests": requests,
        }

    def finalize(self, aid):
        # An unknown commit outcome is reconciled BEFORE derive/read/store; after
        # success the old ownership context is intentionally no longer valid.
        state = self.rpc({"operation": "status", "authorization_id": aid})
        if state["status"] == "COMMITTED":
            return state
        require(
            state["status"] == "BOTH_VERIFIED_PENDING_IDENTITY",
            "TRANSFER_BOTH_PROOFS_REQUIRED",
        )
        return self.rpc(self.finalization_request(aid))

    def derive(self, aid):
        c = self.rpc({"operation": "context", "authorization_id": aid})
        a, e, o = c["authorization"], c["entity"], c["observation"]
        require(
            a["id"] == aid
            and a["effect_code"] == "steal"
            and c["purchase_pending"]
            and c["eligible"],
            "TRANSFER_SCOPE",
        )
        require(
            e["id"] == o["pokemon_entity_id"] == a["target_pokemon_entity_id"]
            and e["identity_status"] == "unambiguous"
            and e["owner_trainer_id"] == c["legs"]["source"]["trainer_id"]
            and a["trainer_id"] == c["legs"]["destination"]["trainer_id"]
            and e["owner_trainer_id"] != a["trainer_id"]
            and o["revision_id"] == a["identity_revision_id"]
            and o["source"] == "box"
            and 1 <= o["box_number"] <= 7
            and o["outcome"] in ("NEW", "MATCHED"),
            "TRANSFER_IDENTITY",
        )
        originals, observations = {}, {}
        for side, leg in c["legs"].items():
            saved = leg["save"]
            require(
                leg["trainer_enabled"]
                and leg["participant_active"]
                and saved["id"] == leg["current_save_id"]
                and saved["trainer_id"] == leg["trainer_id"]
                and saved["season_id"] == a["season_id"]
                and saved["parser_status"] == "parsed"
                and saved["deleted_at"] is None,
                "TRANSFER_SOURCE",
            )
            raw = self.read_source(saved)
            require(sha256(raw).hexdigest() == saved["sha256"], "TRANSFER_SOURCE_HASH")
            parsed = self.parser.parse(raw)
            require(
                saved["metadata"].get("save_identity")
                == {
                    "game": parsed.game,
                    "trainer": parsed.trainer.model_dump(mode="json"),
                },
                "TRANSFER_TRAINER",
            )
            originals[side], observations[side] = raw, parsed
        observed = observations["source"]
        box = next(b for b in observed.boxes if b.number == o["box_number"])
        target = box.slots[o["slot_number"] - 1]
        require(target is not None, "TRANSFER_TARGET_MISSING")
        identity = trusted_native_identity(
            target.identity, trainer=observed.trainer, is_egg=target.is_egg
        )
        require(
            identity.unresolved_reason is None
            and digest(asdict(identity)) == digest(o["evidence"])
            and identity.candidate_key == e["candidate_key"],
            "TRANSFER_IDENTITY",
        )
        plans = self.native.plan_transfer(
            originals["source"],
            originals["destination"],
            pair_id=aid,
            box_index=o["box_number"] - 1,
            slot_index=o["slot_number"] - 1,
            target_pid=identity.pid,
            target_ec=identity.encryption_constant,
        )
        prepared = {
            side: self.native.prepare(originals[side], plan)
            for side, plan in plans.items()
        }
        return c, originals, plans, prepared

    def prepare(self, aid):
        c, _, plans, prepared = self.derive(aid)
        persisted = {
            side: {
                "intent": plan.to_payload(),
                "output_sha256": prepared[side].output_hash,
                "plan_sha256": digest(plan.to_payload()),
            }
            for side, plan in plans.items()
        }
        self.rpc(
            {
                "operation": "plan",
                "authorization_id": aid,
                "context": c,
                "plans": persisted,
            }
        )
        # Private engineering seam only. Do not return peer plans in an HTTP DTO.
        return plans

    def verify(self, aid, side):
        require(side in ("source", "destination"), "TRANSFER_SIDE")
        c, originals, plans, prepared = self.derive(aid)
        job = self.rpc({"operation": "artifact", "authorization_id": aid, "side": side})
        require(
            job["authorization_id"] == aid
            and job["side"] == side
            and job["apply_started"]
            and job["claim_id"] is not None
            and job["result_sha256"] is not None,
            "TRANSFER_ARTIFACT",
        )
        result = self.reader.read(
            job["result_url"], job["result_key"], job["result_sha256"], job["byte_size"]
        )
        self.native.verify(originals[side], result, plans[side], prepared[side])
        # Independent native reparse; exact byte comparison above also constrains
        # every unrelated field and the original OT/individual bytes.
        self.parser.parse(result)
        proof = {
            "authorization_id": aid,
            "side": side,
            "claim_id": job["claim_id"],
            "source_sha256": sha256(originals[side]).hexdigest(),
            "result_sha256": sha256(result).hexdigest(),
            "plan_sha256": digest(plans[side].to_payload()),
        }
        return self.rpc(
            {
                "operation": "finish",
                "authorization_id": aid,
                "side": side,
                "context": c,
                "proof": proof,
            }
        )
