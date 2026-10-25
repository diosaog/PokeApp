"""Engineering-only two-save journal bridge. No renderer capability or business use.

Both original backups are prepared before donor removal. Remote authority only
admits insertion after independent donor proof. Neither local receipt closes a
transfer; sync/reopening stay blocked until the server reports COMMITTED.
"""

import json
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.launcher.write_engine import (
    EngineeringCapability,
    PairedApplyPermit,
    WriteIntent,
)
from app.launcher.write_files import WriteSafetyError

UUID_TEXT = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
HASH_TEXT = r"^[0-9a-f]{64}$"
TransferState = Literal[
    "PREPARING",
    "WAITING_OTHER",
    "PENDING_SOURCE",
    "VERIFYING_SOURCE",
    "PENDING_DESTINATION",
    "VERIFYING_BOTH",
    "BOTH_VERIFIED_PENDING_IDENTITY",
    "COMMITTED",
    "CANCELLED",
    "BLOCKED_UNCERTAIN",
]


class _Wire(BaseModel):
    # Launcher-local wire contract: no app.api import. Newer server fields ignored.
    model_config = ConfigDict(extra="ignore", frozen=True)


class TransferLegWire(_Wire):
    authorization_id: str = Field(pattern=UUID_TEXT)
    side: Literal["source", "destination"]
    status: TransferState
    source_sha256: str = Field(pattern=HASH_TEXT)
    apply_started: bool
    result_sha256: str | None = Field(default=None, pattern=HASH_TEXT)
    verified: bool
    accepted_save_id: str | None = Field(default=None, pattern=UUID_TEXT)


class TransferAssignmentWire(_Wire):
    authorization_id: str = Field(pattern=UUID_TEXT)
    side: Literal["source", "destination"]
    status: TransferState
    intent: dict | None = None


class TransferAssignmentsWire(_Wire):
    items: list[TransferAssignmentWire] = Field(max_length=20)
    transfer_enabled: bool = False


TRANSFER_MESSAGES = {
    "REQUESTED": "Robo solicitado. Pendiente de preparar ambos guardados.",
    "PREPARING": "Preparando las copias de seguridad de ambos guardados.",
    "WAITING_OTHER": "Esperando la preparación del otro entrenador.",
    "PENDING_SOURCE": "Ambos guardados preparados. Pendiente de retirar en origen.",
    "VERIFYING_SOURCE": "Verificando el guardado de origen. El robo aún no está completado.",
    "PENDING_DESTINATION": "Origen verificado. Pendiente de aplicar en destino.",
    "VERIFYING_BOTH": "Verificando los dos guardados. El robo aún no está completado.",
    "BOTH_VERIFIED_PENDING_IDENTITY": "Los dos guardados están verificados; PokeApp está registrando la propiedad. Robo aún sin confirmar.",
    "BLOCKED_UNCERTAIN": "Operación bloqueada. Conserva ambos backups y mantén los emuladores cerrados hasta la recuperación asistida.",
    "RECOVERY_REQUIRED": "Recuperación necesaria. Conserva ambos backups y mantén los emuladores cerrados.",
    "COMMITTED": "Robo confirmado: ambos guardados y la propiedad competitiva están verificados.",
    "CANCELLED": "Operación cancelada antes de aplicar. El objeto no se ha consumido y las copias se conservan.",
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
        self.controller.gate.recovery_required = (
            self.controller._transfer_notice() is not None
            or bool(self.engine.pending())
        )
        return {
            "status": state,
            "message": TRANSFER_MESSAGES.get(
                state, TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
            ),
            "completed": state == "COMMITTED",
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
        with self.controller._operation(recovery=True):
            record, intent = self._load(aid)
            self._state(record, "RECOVERY_REQUIRED")
            remote = self._remote("get", record)
            if remote["status"] == "COMMITTED":
                receipt = self.engine.reconcile(intent.operation_id)
                local = self.engine._load(intent.operation_id)
                if (
                    receipt.status != "APPLIED_VERIFIED"
                    or receipt.current_matches_receipt is not True
                    or remote.get("result_sha256") != local["output_hash"]
                    or not remote.get("accepted_save_id")
                ):
                    return self._state(record, "RECOVERY_REQUIRED")
            elif remote["status"] == "CANCELLED":
                try:
                    self.engine.cancel_paired_prepared(
                        intent.operation_id,
                        paired_permit=PairedApplyPermit(intent.operation_id),
                    )
                except WriteSafetyError as error:
                    if str(error) != "WRITE_OPERATION_NOT_FOUND":
                        raise
                    # Unprepared side: no local apply ever existed. Verify bytes
                    # before releasing its journal gate, still never restore.
                    if (
                        sha256(
                            self.engine.files.read_path(Path(record["binding"]["path"]))
                        ).hexdigest()
                        != intent.expected_sha256
                    ):
                        return self._state(record, "RECOVERY_REQUIRED")
            return self._state(record, remote["status"])

    def cancel(self, aid):
        # Remote compare/cancel is serialized against BOTH begin calls. A lost
        # reply is reconciled with get/state; it never causes physical rollback.
        with self.controller._operation(recovery=True):
            record, _ = self._load(aid)
            self._state(record, "RECOVERY_REQUIRED")
            self._remote("cancel", record)
        return self.state(aid)


class AuthenticatedTransferRemote:
    """User-JWT transport with the same leg/submit seam; never grants capability.

    The server derives trainer scope from the session. Results are revalidated
    here so a malformed or foreign receipt never reaches the local journal.
    """

    def __init__(self, session, season_id, trainer_id):
        self.session = session
        self.sid, self.tid = str(UUID(season_id)), str(UUID(trainer_id))

    def _path(self, aid):
        return f"/v1/launcher/seasons/{self.sid}/transfers/{UUID(aid)}"

    def _scope(self, sid, tid):
        if sid != self.sid or tid != self.tid:
            raise WriteSafetyError("TRANSFER_BINDING_MISMATCH")

    @staticmethod
    def _leg(data, aid):
        try:
            leg = TransferLegWire.model_validate(data).model_dump()
        except (ValidationError, TypeError, ValueError):
            raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH") from None
        if leg["authorization_id"] != aid:
            raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH")
        return leg

    def leg(self, request):
        self._scope(request.get("season_id"), request.get("trainer_id"))
        aid, op = str(UUID(request["authorization_id"])), request["operation"]
        if op == "get":
            return self._leg(self.session.request("GET", self._path(aid)), aid)
        if op not in ("ready", "begin", "cancel"):
            raise WriteSafetyError("TRANSFER_OPERATION_DENIED")
        body = {"operation": op}
        if op != "cancel":
            body["claim_id"] = str(UUID(request["claim_id"]))
        if op == "ready":
            body["backup_sha256"] = request["backup_sha256"]
        return self._leg(self.session.request("PUT", self._path(aid), body=body), aid)

    def submit(self, aid, sid, tid, claim, data):
        self._scope(sid, tid)
        aid = str(UUID(aid))
        path = f"{self._path(aid)}/result?claim_id={UUID(claim)}"
        return self._leg(self.session.upload(path, data), aid)

    def assignments(self):
        raw = self.session.request(
            "GET", f"/v1/launcher/seasons/{self.sid}/transfers", missing=True
        )
        if raw is None:
            return None
        try:
            return TransferAssignmentsWire.model_validate(raw).model_dump()
        except (ValidationError, TypeError, ValueError):
            raise WriteSafetyError("TRANSFER_RECEIPT_MISMATCH") from None


class LauncherTransfers:
    """Runtime seam over EngineeringTransfer and the existing physical journal.

    Only this trainer's own server-planned leg is bound; the native engine still
    revalidates game, trainer, exact source bytes and target before any change.
    Construction fails closed without an in-process EngineeringCapability.
    """

    def __init__(self, controller, remote):
        self.controller, self.remote = controller, remote

    def _bridge(self):
        return EngineeringTransfer(
            self.controller,
            self.remote,
            season_id=self.remote.sid,
            trainer_id=self.remote.tid,
        )

    @staticmethod
    def _bound(bridge, aid):
        try:
            bridge._load(aid)
        except WriteSafetyError as error:
            if str(error) == "TRANSFER_BINDING_NOT_FOUND":
                return False
            raise
        return True

    def prepare(self, aid, *, closed_emulator_confirmed):
        if closed_emulator_confirmed is not True:
            raise WriteSafetyError("WRITE_CONFIRMATION_REQUIRED")
        bridge = self._bridge()
        if not self._bound(bridge, aid):
            listing = self.remote.assignments() or {"items": []}
            item = next(
                (i for i in listing["items"] if i["authorization_id"] == aid), None
            )
            if item is None or item["intent"] is None:
                raise WriteSafetyError("TRANSFER_NOT_PLANNED")
            bridge.bind(aid, item["side"], WriteIntent.create(**item["intent"]))
        return bridge.prepare(aid, closed_emulator_confirmed=True)

    def apply(self, aid, *, closed_emulator_confirmed):
        bridge = self._bridge()
        result = bridge.apply(aid, closed_emulator_confirmed=closed_emulator_confirmed)
        if result["status"] == "RECOVERY_REQUIRED":
            return result
        # Local application is NOT the robbery: upload for independent proof.
        return bridge.submit(aid, self.remote)

    def refresh(self, aid):
        return self._bridge().state(aid)

    def cancel(self, aid):
        bridge = self._bridge()
        if self._bound(bridge, aid):
            return bridge.cancel(aid)
        # Nothing was prepared locally, so there is nothing physical to release.
        leg = self.remote.leg(
            {
                "operation": "cancel",
                "authorization_id": aid,
                "season_id": self.remote.sid,
                "trainer_id": self.remote.tid,
            }
        )
        return {
            "status": leg["status"],
            "message": TRANSFER_MESSAGES.get(
                leg["status"], TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
            ),
            "completed": False,
        }
