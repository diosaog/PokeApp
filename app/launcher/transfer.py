"""Engineering-only two-save journal bridge. No renderer capability or business use.

Both original backups are prepared before donor removal. Remote authority only
admits insertion after independent donor proof. Neither local receipt closes a
transfer; sync/reopening stay blocked pending competitive identity reconciliation.
"""

import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.launcher.write_engine import (
    EngineeringCapability,
    PairedApplyPermit,
    WriteIntent,
)
from app.launcher.write_files import WriteSafetyError

TRANSFER_MESSAGES = {
    "REQUESTED": "Robo solicitado. Pendiente de preparar ambos guardados.",
    "PREPARING": "Preparando las copias de seguridad de ambos guardados.",
    "WAITING_OTHER": "Esperando la preparación del otro entrenador.",
    "PENDING_SOURCE": "Ambos guardados preparados. Pendiente de retirar en origen.",
    "VERIFYING_SOURCE": "Verificando el guardado de origen. El robo aún no está completado.",
    "PENDING_DESTINATION": "Origen verificado. Pendiente de aplicar en destino.",
    "VERIFYING_BOTH": "Verificando los dos guardados. El robo aún no está completado.",
    "BOTH_VERIFIED_PENDING_IDENTITY": "Los dos archivos están verificados; falta reconciliar la identidad. Robo sin confirmar.",
    "RECOVERY_REQUIRED": "Recuperación necesaria. Conserva ambos backups y mantén los emuladores cerrados.",
}


class EngineeringTransfer:
    def __init__(self, controller, repository, *, season_id, trainer_id):
        self.controller, self.repo = controller, repository
        self.engine = controller.engine
        self.sid, self.tid = season_id, trainer_id
        if type(getattr(self.engine, "capability", None)) is not EngineeringCapability:
            raise WriteSafetyError("TRANSFER_APPLICATION_DISABLED")
        with self.engine._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS transfer_bindings(id TEXT PRIMARY KEY,record TEXT NOT NULL)"
            )
            if db.execute("SELECT 1 FROM transfer_bindings LIMIT 1").fetchone():
                controller.gate.recovery_required = True

    def bind(self, aid, side, intent):
        if (
            side not in ("source", "destination")
            or intent.mutation.get("kind")
            != ("transfer_remove" if side == "source" else "transfer_insert")
            or intent.mutation.get("pair_id") != aid
        ):
            raise WriteSafetyError("TRANSFER_BINDING_MISMATCH")
        remote = self.repo.leg(
            {
                "operation": "get",
                "authorization_id": aid,
                "season_id": self.sid,
                "trainer_id": self.tid,
            }
        )
        if (
            remote.get("side") != side
            or remote.get("source_sha256") != intent.expected_sha256
        ):
            raise WriteSafetyError("TRANSFER_BINDING_MISMATCH")
        binding = {
            "authorization_id": aid,
            "side": side,
            "trainer_id": self.tid,
            "season_id": self.sid,
            "path": str(Path(self.controller.selected()).absolute()),
            "intent": intent.to_payload(),
        }
        with self.engine._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT record FROM transfer_bindings WHERE id=?", (aid,)
            ).fetchone()
            if row:
                if json.loads(row[0])["binding"] != binding:
                    raise WriteSafetyError("TRANSFER_BINDING_MISMATCH")
            else:
                db.execute(
                    "INSERT INTO transfer_bindings VALUES(?,?)",
                    (
                        aid,
                        json.dumps(
                            {
                                "binding": binding,
                                "claim_id": str(uuid4()),
                                "state": "REQUESTED",
                            }
                        ),
                    ),
                )
        self.controller.gate.recovery_required = True

    def _load(self, aid):
        with self.engine._db() as db:
            row = db.execute(
                "SELECT record FROM transfer_bindings WHERE id=?", (aid,)
            ).fetchone()
        if not row:
            raise WriteSafetyError("TRANSFER_BINDING_NOT_FOUND")
        record = json.loads(row[0])
        b = record["binding"]
        if (
            b["trainer_id"] != self.tid
            or b["season_id"] != self.sid
            or b["path"] != str(Path(self.controller.selected()).absolute())
        ):
            raise WriteSafetyError("TRANSFER_BINDING_MISMATCH")
        return record, WriteIntent.create(**b["intent"])

    def _remote(self, op, record, **fields):
        b = record["binding"]
        result = self.repo.leg(
            dict(
                operation=op,
                authorization_id=b["authorization_id"],
                trainer_id=self.tid,
                season_id=self.sid,
                claim_id=record["claim_id"],
                **fields,
            )
        )
        if (
            result.get("authorization_id") != b["authorization_id"]
            or result.get("side") != b["side"]
            or result.get("source_sha256") != b["intent"]["expected_sha256"]
        ):
            raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH")
        return result

    def _state(self, record, state):
        record["state"] = state
        with self.engine._db() as db:
            db.execute(
                "UPDATE transfer_bindings SET record=? WHERE id=?",
                (json.dumps(record), record["binding"]["authorization_id"]),
            )
        self.controller.gate.recovery_required = True  # BOTH_VERIFIED is not final
        return {
            "status": state,
            "message": TRANSFER_MESSAGES.get(
                state, TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
            ),
            "completed": False,
        }

    def prepare(self, aid, *, closed_emulator_confirmed):
        if closed_emulator_confirmed is not True:
            raise WriteSafetyError("WRITE_CONFIRMATION_REQUIRED")
        with self.controller._operation(recovery=True):
            record, intent = self._load(aid)
            self._state(record, "RECOVERY_REQUIRED")
            receipt = self.engine.prepare(
                self.engine.enroll(Path(record["binding"]["path"])),
                intent,
                closed_emulator_confirmed=True,
            )
            if receipt.status != "AWAITING_CONFIRMATION":
                return self._state(record, "RECOVERY_REQUIRED")
            original = self.engine._backup_bytes(self.engine._load(intent.operation_id))
            remote = self._remote(
                "ready", record, backup_sha256=sha256(original).hexdigest()
            )
            return self._state(record, remote["status"])

    def apply(self, aid, *, closed_emulator_confirmed):
        if closed_emulator_confirmed is not True:
            raise WriteSafetyError("WRITE_CONFIRMATION_REQUIRED")
        with self.controller._operation(recovery=True):
            record, intent = self._load(aid)
            self._state(record, "RECOVERY_REQUIRED")
            receipt = self.engine.reconcile(intent.operation_id)
            remote = self._remote("get", record)
            if receipt.status == "AWAITING_CONFIRMATION":
                remote = self._remote("begin", record)
                if remote.get("apply_started") is not True:
                    raise WriteSafetyError("TRANSFER_PEER_PENDING")
                receipt = self.engine.confirm(
                    intent.operation_id,
                    closed_emulator_confirmed=True,
                    paired_permit=PairedApplyPermit(intent.operation_id),
                )
            if (
                receipt.status != "APPLIED_VERIFIED"
                or receipt.current_matches_receipt is not True
            ):
                return self._state(record, "RECOVERY_REQUIRED")
            return self._state(record, remote["status"])

    def submit(self, aid, transport):
        with self.controller._operation(recovery=True):
            record, intent = self._load(aid)
            self._state(record, "RECOVERY_REQUIRED")
            receipt = self.engine.reconcile(intent.operation_id)
            if (
                receipt.status != "APPLIED_VERIFIED"
                or receipt.current_matches_receipt is not True
            ):
                return self._state(record, "RECOVERY_REQUIRED")
            _, _, prepared = self.engine._materials(
                self.engine._load(intent.operation_id)
            )
            remote = self._remote("get", record)
            if remote["result_sha256"] not in (None, prepared.output_hash):
                raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH")
            if not remote["verified"]:
                result = self.engine.files.read_path(Path(record["binding"]["path"]))
                if sha256(result).hexdigest() != prepared.output_hash:
                    raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH")
                transport.submit(aid, self.sid, self.tid, record["claim_id"], result)
            return self._state(record, self._remote("get", record)["status"])

    def state(self, aid):
        record, _ = self._load(aid)
        return self._state(record, self._remote("get", record)["status"])
