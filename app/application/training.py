"""Virtual consumables: authority from accepted saves, independent native proof.

The Launcher chooses only a paid purchase, an entity and the desired field.
Source bytes, identity revision, slot and native intent all come from server
authority. Consumption, output registration and identity continuity are atomic.
"""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from threading import BoundedSemaphore

from app.application.save_ingestion import registration_request
from app.domain.pokemon_identity import digest, trusted_native_identity
from app.domain.shop_item_uses import GAMES, use_of
from app.repositories.supabase.season_admin import SeasonAdminRejected

STATS = ("hp", "atk", "defense", "spa", "spd", "spe")
EFFECTS = {"menta_naturaleza": "nature", "chapa_plateada": "iv", "chapa_dorada": "ivs"}


def refuse(code, status=409):
    raise SeasonAdminRejected(code, status)


def slot(payload, source, box_number, slot_number):
    if source == "party":
        rows = payload["party"]
    else:
        rows = next(b["slots"] for b in payload["boxes"] if b["box_number"] == box_number)
    return next(r["pokemon"] for r in rows if r["slot_number"] == slot_number)


class VirtualTraining:
    def __init__(self, repository, parser, native):
        self.repository, self.parser, self.native = repository, parser, native
        self.slots = BoundedSemaphore(2)

    def _call(self, operation, sid, tid, **values):
        return self.repository.execute(operation, sid, tid, **values)

    def listing(self, sid, tid):
        context = self._call("context", sid, tid)
        saved = context["save"]
        payload = context["payload"]
        targets = []
        for observation in context["observations"]:
            p = slot(payload, observation["source"], observation["box_number"], observation["slot_number"])
            if not p or p.get("is_egg") is not False:
                continue
            targets.append({
                "pokemon_entity_id": observation["pokemon_entity_id"],
                "source_sha256": saved["sha256"], "game": payload["game"],
                "source": observation["source"], "box_number": observation["box_number"],
                "slot_number": observation["slot_number"],
                "pokemon": {"species": p["species"], "nickname": p["nickname"], "level": p["level"],
                    "nature_id": int(p["nature"].removeprefix("Nature #")), "ivs": p["ivs"],
                    "is_shiny": p["is_shiny"], "form": p.get("form", 0)},
            })
        return {"items": [dict(p, effect=EFFECTS[p["item_code"]]) for p in context["purchases"]],
                "targets": targets, "operations": context["operations"]}

    def reserve(self, sid, tid, operation_id, body):
        if not self.slots.acquire(blocking=False):
            refuse("TRAINING_VERIFIER_BUSY", 429)
        try:
            return self._reserve(sid, tid, operation_id, body)
        finally:
            self.slots.release()

    def _reserve(self, sid, tid, operation_id, body):
        request_hash = digest(body)
        previous = self._call("load", sid, tid, operation_id=operation_id)
        if previous is not None:
            # SQL checks exact request replay before any source read or native work.
            return self._call("reserve", sid, tid, operation_id=operation_id, request_hash=request_hash)
        context = self._call("context", sid, tid)
        saved, head = context["save"], context["revision"]
        if body["source_sha256"] != saved["sha256"]:
            refuse("TRAINING_SOURCE_CHANGED")
        purchase = next((p for p in context["purchases"] if p["purchase_id"] == body["purchase_id"]), None)
        observation = next((o for o in context["observations"] if o["pokemon_entity_id"] == body["pokemon_entity_id"]), None)
        if purchase is None:
            refuse("TRAINING_PURCHASE_UNAVAILABLE")
        if observation is None:
            refuse("TRAINING_TARGET_UNAVAILABLE")
        code, change = purchase["item_code"], body["change"]
        if use_of(code)["mode"] != "training" or change["kind"] != EFFECTS[code]:
            refuse("TRAINING_CHANGE_NOT_OFFERED")
        source = self.repository.read_source(saved)
        inspected = self.native.inspect_training(source, location=observation["source"],
            box_index=observation["box_number"] - 1 if observation["source"] == "box" else None,
            slot_index=observation["slot_number"] - 1)
        if inspected["source_sha256"] != saved["sha256"] or inspected["game"] not in GAMES or inspected["is_egg"]:
            refuse("TRAINING_SOURCE_CHANGED")
        if change["kind"] == "nature" and inspected["nature"] == change["nature_id"]:
            refuse("TRAINING_NO_CHANGE")
        if change["kind"] == "iv" and inspected["ivs"][STATS.index(change["stat"])] == 31:
            refuse("TRAINING_NO_CHANGE")
        if change["kind"] == "ivs" and all(v == 31 for v in inspected["ivs"]):
            refuse("TRAINING_NO_CHANGE")
        mutation = {"kind": "virtual_training", "item_code": code, "attempt": operation_id,
            "location": observation["source"], "box_index": observation["box_number"] - 1 if observation["source"] == "box" else None,
            "slot_index": observation["slot_number"] - 1, "expected_pokemon_sha256": inspected["pokemon_sha256"],
            "expected_nature": inspected["nature"], "expected_ivs": inspected["ivs"],
            "nature_id": change.get("nature_id"), "stat": change.get("stat")}
        intent = {"expected_sha256": saved["sha256"], "game": inspected["game"],
                  "trainer_key": inspected["trainer_key"], "mutation": mutation}
        from app.save_parser.write_models import WriteIntent

        # Pure bytes-only preparation also enforces legality before a reservation
        # is issued. It never opens or modifies the player's local save.
        self.native.prepare(source, WriteIntent.create(**intent))
        return self._call("reserve", sid, tid, operation_id=operation_id, request_hash=request_hash,
            purchase_id=body["purchase_id"], pokemon_entity_id=body["pokemon_entity_id"],
            save_file_id=saved["id"], identity_revision_id=head["id"], intent=intent)

    def complete(self, sid, tid, operation_id, output):
        if not self.slots.acquire(blocking=False):
            refuse("TRAINING_VERIFIER_BUSY", 429)
        try:
            return self._complete(sid, tid, operation_id, output)
        finally:
            self.slots.release()

    def _complete(self, sid, tid, operation_id, output):
        operation = self._call("load", sid, tid, operation_id=operation_id)
        if operation is None:
            refuse("TRAINING_NOT_FOUND", 404)
        output_hash = sha256(output).hexdigest()
        if operation["status"] == "APPLIED":
            return self._call("complete", sid, tid, operation_id=operation_id, output_sha256=output_hash)
        if operation["status"] != "RESERVED":
            refuse("TRAINING_NOT_RESERVED")
        context = self._call("context", sid, tid)
        saved = context["save"]
        if saved["id"] != operation["save_file_id"] or context["revision"]["id"] != operation["identity_revision_id"]:
            refuse("TRAINING_SOURCE_CHANGED")
        source = self.repository.read_source(saved)
        # Portable module imported only when bytes are verified. Neither SQL nor
        # the API trusts a client-provided output hash or semantic difference.
        from app.save_parser.write_models import WriteIntent

        intent = WriteIntent.create(**operation["intent"])
        prepared = self.native.prepare(source, intent)
        self.native.verify(source, output, intent, prepared)
        observed = self.parser.parse(output)
        m = intent.mutation
        place = (m["location"], (m["box_index"] + 1) if m["box_index"] is not None else 0, m["slot_index"] + 1)
        target = next(p for location, p in observed.occupied()
                      if (location.source, location.box_number, location.slot_number) == place)
        observed_after = asdict(trusted_native_identity(target.identity, trainer=observed.trainer, is_egg=target.is_egg))
        registration_context = deepcopy(context["registration"])
        entity = next(e for e in registration_context["entities"] if e["id"] == operation["pokemon_entity_id"])
        before = entity["initial_evidence"]
        # A proven foreign-OT entity retains its original canonical evidence flag;
        # actual observations still record False and match via transfer proof.
        after = dict(observed_after, source_trainer_match=before["source_trainer_match"])
        if {k: v for k, v in before.items() if k not in ("ivs", "source_trainer_match")} != {
            k: v for k, v in after.items() if k not in ("ivs", "source_trainer_match")
        }:
            refuse("TRAINING_VERIFICATION_REQUIRED")
        entity["initial_evidence"] = after
        entity["candidate_key"] = digest(after)
        request = registration_request(sid, tid, output_hash, saved["id"], observed,
                                       self.parser.version, registration_context)
        matches = [b for b in request["identity_plan"]["bindings"] if b["pokemon_entity_id"] == entity["id"]]
        if len(matches) != 1 or matches[0]["outcome"] != "MATCHED":
            refuse("TRAINING_IDENTITY_UNPROVEN")
        self.repository.store_raw(request["storage_key"], output, output_hash)
        return self._call("complete", sid, tid, operation_id=operation_id, output_sha256=output_hash,
            before_evidence=before, after_evidence=after, after_candidate_key=digest(after), registration=request,
            observed_evidence=observed_after, observed_candidate_key=digest(observed_after),
            result={"semantic_diff": prepared.semantic_diff})

    def release(self, sid, tid, operation_id):
        return self._call("release", sid, tid, operation_id=operation_id)
