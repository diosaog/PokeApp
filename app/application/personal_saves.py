"""A trainer's own save outside any season, for «Mi PC» (065).

Same trust boundary as season ingestion: the server parses the uploaded bytes
itself and the Launcher's observation digest must match its own, so a client
cannot claim Pokémon its file does not hold. Unlike season saves it is not a
competitive record: no participation, identities or CAS against other
devices — the latest synced file of the trainer is the personal save.

The wire receipt is a SaveRegistration with season_id "personal" and the
trainer's id as save_id, so the Launcher reuses its outbox, retries and
readback unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from threading import BoundedSemaphore

from app.api.read_models import PCRead
from app.application.save_ingestion import parsed_payload, reject
from app.save_parser.files import MAX_SAVE_BYTES
from app.save_parser.models import SaveError
from app.save_parser.registration import SaveRegistration, observation_digest

PERSONAL = "personal"
GAMES = {"X", "Y", "OR", "AS", "SN", "MN", "US", "UM"}


class PersonalSaves:
    def __init__(self, repository, parser):
        self.repository, self.parser = repository, parser
        self.slots = BoundedSemaphore(2)

    def context(self, trainer_id):
        row = self.repository.get(trainer_id)
        return {"current_save_id": trainer_id if row else None}

    def _receipt(self, trainer_id, row, raw_hash):
        return SaveRegistration.model_validate(
            {
                "status": "registered",
                "save_id": trainer_id,
                "trainer_id": trainer_id,
                "season_id": PERSONAL,
                "sha256": raw_hash,
                "observation_digest": row["observation_digest"],
                "parser_version": row["parser_version"],
                "is_current": row["sha256"] == raw_hash,
            }
        )

    def receipt(self, trainer_id, raw_hash):
        row = self.repository.get(trainer_id)
        if not row or row["sha256"] != raw_hash:
            reject("SAVE_NOT_FOUND", 404)
        return self._receipt(trainer_id, row, raw_hash)

    def receive(self, trainer_id, raw_hash, local_digest, data):
        if not data or len(data) > MAX_SAVE_BYTES:
            reject("INVALID_SAVE_SIZE", 413)
        if sha256(data).hexdigest() != raw_hash:
            reject("SAVE_HASH_MISMATCH")
        current = self.repository.get(trainer_id)
        if current and current["sha256"] == raw_hash:
            if current["observation_digest"] != local_digest:
                reject("SAVE_PARSE_MISMATCH")
            return self._receipt(trainer_id, current, raw_hash)  # exact replay
        if not self.slots.acquire(blocking=False):
            reject("SAVE_PARSER_BUSY", 429)
        try:
            try:
                observed = self.parser.parse(data)
            except SaveError as error:
                reject(error.code.value, 422)
            if observation_digest(observed, self.parser.version) != local_digest:
                reject("SAVE_PARSE_MISMATCH")
            row = {
                "trainer_id": trainer_id,
                "sha256": raw_hash,
                "observation_digest": local_digest,
                "parser_version": self.parser.version,
                "game": observed.game,
                "payload": parsed_payload(observed, trainer_id, trainer_id, raw_hash),
                "uploaded_at": datetime.now(UTC).isoformat(),
            }
            self.repository.upsert(row)
        finally:
            self.slots.release()
        return self._receipt(trainer_id, row, raw_hash)

    def pc(self, trainer_id):
        row = self.repository.get(trainer_id)
        if not row:
            return PCRead(save=None, status="no_current_save", pokemon=[])
        payload = row["payload"]
        save = {
            "id": trainer_id,
            "parser_status": "parsed",
            "parser_version": row["parser_version"],
            "uploaded_at": row["uploaded_at"],
            "game": row["game"] if row["game"] in GAMES else None,
        }
        party, boxes = payload.get("party"), payload.get("boxes")
        if not isinstance(party, list) or not isinstance(boxes, list):
            return PCRead(save=save, status="unsupported_payload", pokemon=[])
        pokemon = [
            {"location": f"Equipo · {s['slot_number']}", "pokemon": {**s["pokemon"], "status_flags": []}}
            for s in party
            if s.get("pokemon")
        ]
        for box in boxes:
            for slot in box.get("slots", []):
                if slot.get("pokemon"):
                    pokemon.append(
                        {
                            "location": f"Caja {box['box_number']} · {slot['slot_number']}",
                            "pokemon": {**slot["pokemon"], "status_flags": []},
                        }
                    )
        return PCRead(save=save, status="ready", pokemon=pokemon)
