"""Private robbery verifier, reusing native/Storage boundaries from 23D.

27A: the competitive decision is taken from the server-held accepted saves
(adjudicate). Each side's physical obligation is then proven independently
(verify) and registered (settle); a side whose file moved on is re-planned on
its current bytes (rebase). Proofs never imply continued local possession.
"""

from dataclasses import asdict
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.application.item_use_verification import require
from app.application.save_ingestion import registration_request
from app.domain.pokemon_identity import digest, trusted_native_identity
from app.launcher.write_engine import WriteIntent
from app.save_parser.models import SaveError
from app.save_parser.writer import NativeWriteError


class TransferVerification:
    def __init__(self, rpc, read_source, reader, parser, native, *, store_raw=None):
        self.rpc, self.read_source, self.reader = rpc, read_source, reader
        self.parser, self.native = parser, native
        self.store_raw = store_raw

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
            and (
                o["source"] == "box"
                and 1 <= o["box_number"] <= 7
                or o["source"] == "party"
                and 1 <= o["slot_number"] <= 6
            )
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
        if o["source"] == "party":
            target = observed.party[o["slot_number"] - 1]
        else:
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
            location=o["source"],
            box_index=o["box_number"] - 1 if o["source"] == "box" else -1,
            slot_index=o["slot_number"] - 1,
            target_pid=identity.pid,
            target_ec=identity.encryption_constant,
        )
        prepared = {
            side: self.native.prepare(originals[side], plan)
            for side, plan in plans.items()
        }
        return c, originals, plans, prepared

    @staticmethod
    def _persisted(plans, prepared):
        return {
            side: {
                "intent": plan.to_payload(),
                "output_sha256": prepared[side].output_hash,
                "plan_sha256": digest(plan.to_payload()),
            }
            for side, plan in plans.items()
        }

    def prepare(self, aid):
        c, _, plans, prepared = self.derive(aid)
        self.rpc(
            {
                "operation": "plan",
                "authorization_id": aid,
                "context": c,
                "plans": self._persisted(plans, prepared),
            }
        )
        # Private engineering seam only. Do not return peer plans in an HTTP DTO.
        return plans

    def adjudicate(self, aid):
        """Competitive decision from the server-held accepted saves only.

        Both plans are re-derived and must equal the persisted ones; neither
        Launcher nor any physical proof takes part. Idempotent.
        """
        state = self.rpc({"operation": "status", "authorization_id": aid})
        if state.get("adjudicated"):
            return state
        c, _, plans, prepared = self.derive(aid)
        return self.rpc(
            {
                "operation": "adjudicate",
                "authorization_id": aid,
                "context": c,
                "plans": self._persisted(plans, prepared),
            }
        )

    def _decided(self, aid):
        snap = self.rpc({"operation": "adjudicated_context", "authorization_id": aid})
        require(
            isinstance(snap, dict) and snap.get("adjudication"),
            "TRANSFER_NOT_ADJUDICATED",
        )
        return snap

    def _canonical(self, snap, side):
        """Accepted save captured by the decision; never a client-provided file."""
        saved = snap["adjudication"]["context"]["legs"][side]["save"]
        raw = self.read_source(saved)
        require(sha256(raw).hexdigest() == saved["sha256"], "TRANSFER_SOURCE_HASH")
        return raw

    def _basis(self, snap, side):
        """Exact bytes the side's current plan was derived from."""
        leg = snap["legs"][side]
        if leg["basis_key"] is None:
            raw = self._canonical(snap, side)
        else:
            raw = self.read_source({"storage_key": leg["basis_key"]})
        require(sha256(raw).hexdigest() == leg["source_sha256"], "TRANSFER_SOURCE_HASH")
        return raw

    def _planned(self, snap, side, original):
        plan = snap["plans"][side]
        intent = WriteIntent.create(**plan["intent"])
        require(
            digest(intent.to_payload()) == plan["plan_sha256"]
            and intent.expected_sha256 == sha256(original).hexdigest(),
            "TRANSFER_PLAN",
        )
        prepared = self.native.prepare(original, intent)
        require(prepared.output_hash == plan["output_sha256"], "TRANSFER_PLAN")
        return intent, prepared

    def verify(self, aid, side):
        """Independent proof of ONE side's physical obligation."""
        require(side in ("source", "destination"), "TRANSFER_SIDE")
        snap = self._decided(aid)
        if snap["legs"][side]["verified"]:
            return snap["legs"][side]  # lost reply: the proof already exists
        original = self._basis(snap, side)
        intent, prepared = self._planned(snap, side, original)
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
        self.native.verify(original, result, intent, prepared)
        # Independent native reparse; exact byte comparison above also constrains
        # every unrelated field and the original OT/individual bytes.
        self.parser.parse(result)
        proof = {
            "authorization_id": aid,
            "side": side,
            "claim_id": job["claim_id"],
            "source_sha256": sha256(original).hexdigest(),
            "result_sha256": sha256(result).hexdigest(),
            "plan_sha256": digest(intent.to_payload()),
        }
        return self.rpc(
            {
                "operation": "finish",
                "authorization_id": aid,
                "side": side,
                "proof": proof,
            }
        )

    def settle(self, aid, side, *, absent=False):
        """Register a verified side, or a victim save proven not to hold the
        Pokémon, as that trainer's accepted save. Releases only that trainer."""
        require(self.store_raw is not None, "TRANSFER_ACCEPTANCE_STORAGE_REQUIRED")
        snap = self._decided(aid)
        leg = snap["legs"][side]
        if leg["obligation"] in ("VERIFIED", "ABSENT_VERIFIED"):
            return leg  # lost reply: already registered exactly once
        if absent:
            data = self.reader.read(
                leg["candidate_url"],
                leg["candidate_key"],
                leg["candidate_sha256"],
                leg["candidate_size"],
            )
        else:
            require(leg["verified"], "TRANSFER_PROOF_REQUIRED")
            data = self.reader.read(
                leg["result_url"],
                leg["result_key"],
                leg["result_sha256"],
                leg["byte_size"],
            )
        observed = self.parser.parse(data)
        context = self.rpc(
            {"operation": "settle_context", "authorization_id": aid, "side": side}
        )
        saved = snap["adjudication"]["context"]["legs"][side]["save"]
        digest_hex = sha256(data).hexdigest()
        request = registration_request(
            saved["season_id"],
            leg["trainer_id"],
            digest_hex,
            saved["id"],
            observed,
            self.parser.version,
            context["registration"],
        )
        self.store_raw(request["storage_key"], data, digest_hex)
        return self.rpc(
            {
                "operation": "settle",
                "authorization_id": aid,
                "side": side,
                "mode": "absent" if absent else "proof",
                "request": request,
            }
        )

    def _reject(self, aid, side, code, *, blocking):
        return self.rpc(
            {
                "operation": "reject_candidate",
                "authorization_id": aid,
                "side": side,
                "code": code,
                "blocking": blocking,
            }
        )

    def rebase(self, aid, side):
        """Re-plan a pending side on the trainer's CURRENT file.

        The decision never changes: the robbed identity is located by its
        immutable evidence. The recipient's Pokémon bytes always come from the
        victim's canonical accepted save, never from a victim upload. Absent from
        the victim's file: that file is accepted as is. Ambiguous or another
        save: blocked for assisted recovery.
        """
        require(self.store_raw is not None, "TRANSFER_ACCEPTANCE_STORAGE_REQUIRED")
        snap = self._decided(aid)
        leg = snap["legs"][side]
        require(leg["candidate_url"] is not None, "TRANSFER_CANDIDATE")
        data = self.reader.read(
            leg["candidate_url"],
            leg["candidate_key"],
            leg["candidate_sha256"],
            leg["candidate_size"],
        )
        context = snap["adjudication"]["context"]
        try:
            observed = self.parser.parse(data)
        except SaveError:
            return self._reject(
                aid, side, "TRANSFER_CANDIDATE_UNREADABLE", blocking=False
            )
        if context["legs"][side]["save"]["metadata"].get("save_identity") != {
            "game": observed.game,
            "trainer": observed.trainer.model_dump(mode="json"),
        }:
            return self._reject(
                aid, side, "TRANSFER_CANDIDATE_OTHER_SAVE", blocking=True
            )
        o = context["observation"]
        location = (o["source"], o["box_number"], o["slot_number"])
        if side == "source":
            found = [
                place
                for place, slot in _slots(observed)
                if slot is not None
                and digest(
                    asdict(
                        trusted_native_identity(
                            slot.identity, trainer=observed.trainer, is_egg=slot.is_egg
                        )
                    )
                )
                == digest(o["evidence"])
            ]
            if not found:
                return self.settle(aid, side, absent=True)
            if len(found) > 1:
                return self._reject(
                    aid, side, "TRANSFER_CANDIDATE_AMBIGUOUS", blocking=True
                )
            location = found[0]
        donor = data if side == "source" else self._canonical(snap, "source")
        recipient = (
            data if side == "destination" else self._canonical(snap, "destination")
        )
        revision = len(snap["plan_history"]) + 1
        pair_id = str(uuid5(NAMESPACE_URL, f"pokeapp-transfer-plan:{aid}:{revision}"))
        try:
            plans = self.native.plan_transfer(
                donor,
                recipient,
                pair_id=pair_id,
                location=location[0],
                box_index=location[1] - 1 if location[0] == "box" else -1,
                slot_index=location[2] - 1,
                target_pid=o["evidence"]["pid"],
                target_ec=o["evidence"]["encryption_constant"],
            )
            prepared = self.native.prepare(data, plans[side])
        except NativeWriteError as error:
            return self._reject(
                aid, side, "TRANSFER_REPLAN_" + error.code, blocking=False
            )
        digest_hex = sha256(data).hexdigest()
        basis_key = f"transfer-basis/{aid}/{side}/{digest_hex}.sav"
        self.store_raw(basis_key, data, digest_hex)
        return self.rpc(
            {
                "operation": "rebase",
                "authorization_id": aid,
                "side": side,
                "candidate_sha256": digest_hex,
                "basis_key": basis_key,
                "pair_id": pair_id,
                "plan": self._persisted({side: plans[side]}, {side: prepared})[side],
            }
        )


def _slots(observed):
    for index, slot in enumerate(observed.party, 1):
        yield ("party", None, index), slot
    for box in observed.boxes:
        if box.number <= 7:
            for index, slot in enumerate(box.slots, 1):
                yield ("box", box.number, index), slot
