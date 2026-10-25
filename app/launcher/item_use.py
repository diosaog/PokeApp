"""Engineering-only item-use bridge on the existing physical journal/controller.

No production IPC command or trusted-proof issuer lives in the Launcher.
The isolated harness can bind a server-derived revive plan or the older synthetic
test_marking. Neither a local receipt nor this capability is server evidence.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.launcher.write_engine import EngineeringCapability
from app.launcher.write_files import WriteSafetyError


class EngineeringItemUse:
    def __init__(self, controller, repository, *, season_id, trainer_id):
        self.controller, self.repo = controller, repository
        self.engine = controller.engine
        self.season_id, self.trainer_id = season_id, trainer_id
        if type(getattr(self.engine, "capability", None)) is not EngineeringCapability:
            raise WriteSafetyError("ITEM_APPLICATION_DISABLED")
        with self.engine._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS item_use_bindings "
                "(id TEXT PRIMARY KEY, native_id TEXT UNIQUE NOT NULL, record TEXT NOT NULL)"
            )
            pending = db.execute("SELECT record FROM item_use_bindings").fetchall()
        if any(json.loads(r[0])["state"] != "APPLIED_VERIFIED" for r in pending):
            controller.gate.recovery_required = True

    def bind_fixture(self, authorization, intent, *, pokemon_entity_id):
        """Retained synthetic fixture seam; it never certifies physical revival."""
        if intent.mutation.get("kind") != "test_marking":
            raise WriteSafetyError("ITEM_BINDING_MISMATCH")
        return self._bind(authorization, intent, pokemon_entity_id=pokemon_entity_id)

    def bind_revive(self, authorization, intent, *, pokemon_entity_id):
        """Engineering-only intake of the independently derived server plan."""
        if (
            authorization.get("effect_code") != "revive"
            or intent.mutation.get("kind") != "revive"
        ):
            raise WriteSafetyError("ITEM_BINDING_MISMATCH")
        return self._bind(authorization, intent, pokemon_entity_id=pokemon_entity_id)

    def _bind(self, authorization, intent, *, pokemon_entity_id):
        a = authorization
        if (
            a["season_id"] != self.season_id
            or a["trainer_id"] != self.trainer_id
            or a["target_pokemon_entity_id"] != pokemon_entity_id
            or a["save_sha256"] != intent.expected_sha256
        ):
            raise WriteSafetyError("ITEM_BINDING_MISMATCH")
        binding = {
            k: a[k]
            for k in (
                "id",
                "operation_id",
                "season_id",
                "trainer_id",
                "purchase_id",
                "target_pokemon_entity_id",
                "save_file_id",
                "save_sha256",
                "expires_at",
                "identity_revision_id",
                "effect_code",
            )
        }
        binding["intent"] = intent.to_payload()
        binding["path"] = str(Path(self.controller.selected()).absolute())
        record = {"binding": binding, "claim_id": str(uuid4()), "state": "PREPARED"}
        with self.engine._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT record FROM item_use_bindings WHERE id=?", (a["id"],)
            ).fetchone()
            if old:
                if json.loads(old[0])["binding"] != binding:
                    raise WriteSafetyError("ITEM_BINDING_MISMATCH")
                return
            if a["status"] != "PREPARED" or datetime.fromisoformat(
                a["expires_at"]
            ) <= datetime.now(UTC):
                raise WriteSafetyError("ITEM_AUTHORIZATION_UNAVAILABLE")
            db.execute(
                "INSERT INTO item_use_bindings VALUES (?,?,?)",
                (a["id"], intent.operation_id, json.dumps(record)),
            )

    def _load(self, identifier):
        with self.engine._db() as db:
            row = db.execute(
                "SELECT native_id,record FROM item_use_bindings WHERE id=?",
                (identifier,),
            ).fetchone()
        if not row:
            raise WriteSafetyError("ITEM_BINDING_NOT_FOUND")
        native_id, raw = row
        record = json.loads(raw)
        b = record["binding"]
        if (
            b["season_id"] != self.season_id
            or b["trainer_id"] != self.trainer_id
            or b["path"] != str(Path(self.controller.selected()).absolute())
        ):
            raise WriteSafetyError("ITEM_BINDING_MISMATCH")
        return native_id, record

    def _state(self, identifier, record, state):
        record["state"] = state
        with self.engine._db() as db:
            db.execute(
                "UPDATE item_use_bindings SET record=? WHERE id=?",
                (json.dumps(record), identifier),
            )
            remaining = db.execute("SELECT record FROM item_use_bindings").fetchall()
        self.controller.gate.recovery_required = any(
            json.loads(row[0])["state"] != "APPLIED_VERIFIED" for row in remaining
        ) or bool(self.engine.pending())
        return state

    def _claim(self, identifier, record):
        result = self.repo.claim(
            identifier,
            self.season_id,
            self.trainer_id,
            {
                "operation_id": record["binding"]["operation_id"],
                "claim_id": record["claim_id"],
            },
        )
        self._check_remote(result, record)
        return result

    @staticmethod
    def _check_remote(result, record):
        if not isinstance(result, dict) or any(
            result.get(k) != v
            for k, v in record["binding"].items()
            if k not in ("intent", "path")
        ):
            raise WriteSafetyError("ITEM_RECEIPT_MISMATCH")

    def apply(self, identifier, *, closed_emulator_confirmed):
        if closed_emulator_confirmed is not True:
            raise WriteSafetyError("WRITE_CONFIRMATION_REQUIRED")
        with self.controller._operation(recovery=True):
            native_id, record = self._load(identifier)
            self._state(identifier, record, "RECOVERY_REQUIRED")
            remote = self._claim(
                identifier, record
            )  # stable claimant survives lost responses
            with self.engine._db() as db:
                exists = db.execute(
                    "SELECT 1 FROM physical_writes WHERE id=?", (native_id,)
                ).fetchone()
            if exists:
                receipt = self.engine.reconcile(native_id)
            else:
                if remote["status"] != "PENDING_APPLICATION":
                    return self._state(identifier, record, "BLOCKED_UNCERTAIN")
                from app.launcher.write_engine import WriteIntent

                intent = WriteIntent.create(**record["binding"]["intent"])
                receipt = self.engine.prepare(
                    self.engine.enroll(Path(record["binding"]["path"])),
                    intent,
                    closed_emulator_confirmed=True,
                )
            if (
                receipt.status == "AWAITING_CONFIRMATION"
                and remote["status"] == "PENDING_APPLICATION"
            ):
                receipt = self.engine.confirm(native_id, closed_emulator_confirmed=True)
            self.controller._record(receipt)
            state = (
                "LOCAL_VERIFIED_AWAITING_CONFIRMATION"
                if receipt.status == "APPLIED_VERIFIED"
                else "RECOVERY_REQUIRED"
            )
            return self._state(identifier, record, state)

    def complete(self, identifier):
        # No application/reapplication here, including after a lost HTTP response.
        with self.controller._operation(recovery=True):
            native_id, record = self._load(identifier)
            self._state(identifier, record, "RECOVERY_REQUIRED")
            receipt = self.engine.reconcile(native_id)
            if (
                receipt.status != "APPLIED_VERIFIED"
                or receipt.current_matches_receipt is not True
            ):
                return self._state(identifier, record, "RECOVERY_REQUIRED")
            _, _, prepared = self.engine._materials(self.engine._load(native_id))
            remote = self.repo.complete(
                identifier,
                self.season_id,
                self.trainer_id,
                {
                    "operation_id": record["binding"]["operation_id"],
                    "claim_id": record["claim_id"],
                    "status": "APPLIED_VERIFIED",
                    "observed_sha256": prepared.output_hash,
                },
            )
            self._check_remote(remote, record)
            state = (
                remote["status"]
                if remote["status"]
                in ("APPLIED_VERIFIED", "BLOCKED_UNCERTAIN", "RECOVERY_REQUIRED")
                else "BLOCKED_UNCERTAIN"
            )
            if (
                state == "APPLIED_VERIFIED"
                and remote.get("observed_sha256") != prepared.output_hash
            ):
                state = "BLOCKED_UNCERTAIN"
            return self._state(identifier, record, state)
