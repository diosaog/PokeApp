"""Journaled virtual consumables; only a server-bound native write spends one.

The same write engine, independent verified backups, no-replace handoff and
native recovery used by existing physical operations own every filesystem step.
An uncertain write keeps its purchase reserved and pauses save synchronization.
"""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from app.launcher.backend import BackendError
from app.launcher.write_engine import PairedApplyPermit, WriteIntent
from app.launcher.write_files import WriteSafetyError

SETTLED = ("APPLIED", "RELEASED")
STATS = ("hp", "atk", "defense", "spa", "spd", "spe")
TRAINING_PENDING_NOTICE = "Hay una mejora de Pokémon pendiente de verificar con PokeApp. Conserva las copias y abre Mejorar Pokémon con la cuenta que la inició."


def validate_arguments(args):
    if not isinstance(args, dict) or set(args) != {"purchase_id", "pokemon_entity_id", "source_sha256", "change"}:
        return False
    try:
        for key in ("purchase_id", "pokemon_entity_id"):
            if not isinstance(args[key], str) or str(UUID(args[key])) != args[key]:
                return False
    except (ValueError, TypeError, AttributeError):
        return False
    import re
    if not isinstance(args["source_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", args["source_sha256"]):
        return False
    change = args["change"]
    if not isinstance(change, dict):
        return False
    if change.get("kind") == "nature":
        return set(change) == {"kind", "nature_id"} and type(change["nature_id"]) is int and 0 <= change["nature_id"] <= 24
    if change.get("kind") == "iv":
        return set(change) == {"kind", "stat"} and change["stat"] in STATS
    return change == {"kind": "ivs"}


class TrainingRemote:
    def __init__(self, session, season_id):
        self.session, self.sid = session, str(UUID(season_id))

    def _path(self, operation=None, step=""):
        base = f"/v1/launcher/seasons/{self.sid}/training"
        return base if operation is None else f"{base}/{UUID(operation)}{step}"

    def list(self):
        return self.session.request("GET", self._path())

    def reserve(self, operation, args):
        return self.session.request("PUT", self._path(operation), body=args)

    def complete(self, operation, output):
        return self.session.upload(self._path(operation, "/complete"), output)

    def release(self, operation):
        return self.session.request("PUT", self._path(operation, "/release"), body={}, missing=True)


class LauncherTraining:
    def __init__(self, controller, remote, *, trainer_id):
        self.controller, self.remote, self.engine = controller, remote, controller.engine
        self.sid, self.tid = remote.sid, str(UUID(trainer_id))
        if self.engine is None or not self.engine.allows("virtual_training"):
            raise WriteSafetyError("TRAINING_DISABLED")
        with self.engine._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS training_bindings (id TEXT PRIMARY KEY,record TEXT NOT NULL)")

    def _records(self):
        with self.engine._db() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT record FROM training_bindings")]

    def pending(self):
        return [r for r in self._records() if r["state"] not in SETTLED and r["season_id"] == self.sid and r["trainer_id"] == self.tid]

    def _state(self, record, state, error=None):
        record.update(state=state, error=error)
        with self.engine._db() as db:
            db.execute("INSERT INTO training_bindings(id,record) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET record=excluded.record",
                       (record["operation_id"], json.dumps(record, sort_keys=True, separators=(",", ":"))))
        self._gate()

    def _gate(self):
        self.controller.gate.recovery_required = (
            any(r["state"] not in SETTLED for r in self._records())
            or any(r.status in ("PREPARED", "RECOVERY_REQUIRED") for r in self.engine.pending())
            or self.controller._transfer_notice() is not None
        )

    def _receipt(self, receipt, record, status):
        if (not isinstance(receipt, dict) or receipt.get("operation_id") != record["operation_id"]
            or receipt.get("purchase_id") != record["args"]["purchase_id"]
            or receipt.get("season_id") != self.sid or receipt.get("trainer_id") != self.tid
            or receipt.get("status") != status):
            raise WriteSafetyError("TRAINING_BINDING_MISMATCH")

    def _local(self, record):
        if not record.get("native_id"):
            return None
        try:
            return self.engine._load(record["native_id"])
        except WriteSafetyError as error:
            if error.code == "WRITE_OPERATION_NOT_FOUND":
                return None
            raise

    def _release(self, record):
        receipt = self.remote.release(record["operation_id"])
        if receipt is not None:
            self._receipt(receipt, record, "RELEASED")
        self._state(record, "RELEASED")

    def _abandon(self, record):
        local = self._local(record)
        if local and local["status"] == "AWAITING_CONFIRMATION" and not local.get("commit_started"):
            self.engine.cancel_paired_prepared(record["native_id"], paired_permit=PairedApplyPermit(record["native_id"]))
        self._release(record)

    def _complete(self, record, output=None):
        local = self._local(record)
        if not local or local["status"] != "APPLIED_VERIFIED":
            raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
        intent = WriteIntent.create(**record["intent"])
        original = self.engine._backup_bytes(local)
        prepared = self.engine.native.prepare(original, intent)
        if prepared.output_hash != local["output_hash"] or record.get("output_sha256") not in (None, prepared.output_hash):
            raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
        # A fresh independent native verify also covers restart recovery. The
        # durable APPLIED_VERIFIED receipt proves the handoff/readback happened;
        # merely prepared bytes can never enter this completion branch.
        self.engine.native.verify(original, prepared.output, intent, prepared)
        if output is not None and output != prepared.output:
            raise WriteSafetyError("TRAINING_BINDING_MISMATCH")
        receipt = self.remote.complete(record["operation_id"], prepared.output)
        self._receipt(receipt, record, "APPLIED")
        self._state(record, "APPLIED")
        return receipt

    def settle(self):
        with self.controller._operation(recovery=True):
            return self._settle()

    def _settle(self):
        waiting, completed = [], []
        for record in self.pending():
            try:
                local = self._local(record)
                status = local["status"] if local else None
                if status == "APPLIED_VERIFIED":
                    self._complete(record)
                    completed.append(record["operation_id"])
                elif status in (None, "REJECTED", "RESTORED_VERIFIED"):
                    self._release(record)
                elif status == "AWAITING_CONFIRMATION" and not local.get("commit_started"):
                    self._abandon(record)
                else:
                    waiting.append(record["operation_id"])
            except (BackendError, WriteSafetyError):
                waiting.append(record["operation_id"])
        self._gate()
        return {"waiting": waiting, "completed": completed}

    def apply(self, args):
        if not validate_arguments(args):
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        with self.controller._operation(recovery=True):
            self._settle()
            if any(r["state"] not in SETTLED for r in self._records()):
                raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
            if any(r.status in ("PREPARED", "AWAITING_CONFIRMATION", "RECOVERY_REQUIRED") for r in self.engine.pending()):
                raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
            path = Path(self.controller.selected())
            source = self.engine.files.read_path(path)
            if sha256(source).hexdigest() != args["source_sha256"]:
                raise WriteSafetyError("STALE_SOURCE")
            # The controller's recovery lease allows only reconciliation until
            # the pending journal is settled. Start a new write only now.
            if self.controller._transfer_notice() is not None:
                raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
            record = dict(operation_id=str(uuid4()), native_id=None, season_id=self.sid,
                trainer_id=self.tid, args=json.loads(json.dumps(args)), path=str(path.absolute()),
                intent=None, output_sha256=None, state="RESERVING", error=None,
                created_at=datetime.now(UTC).isoformat())
            self._state(record, "RESERVING")
            try:
                receipt = self.remote.reserve(record["operation_id"], args)
            except BackendError as error:
                if error.status in (403, 404, 409, 422):
                    self._state(record, "RELEASED", error.detail)
                raise
            self._receipt(receipt, record, "RESERVED")
            intent = WriteIntent.create(**receipt["intent"])
            choice = args["change"]
            expected_code = {"nature": "menta_naturaleza", "iv": "chapa_plateada", "ivs": "chapa_dorada"}[choice["kind"]]
            if (intent.expected_sha256 != args["source_sha256"] or receipt.get("pokemon_entity_id") != args["pokemon_entity_id"]
                or intent.mutation.get("kind") != "virtual_training"
                or intent.mutation.get("attempt") != record["operation_id"]
                or intent.mutation.get("item_code") != expected_code
                or intent.mutation.get("nature_id") != choice.get("nature_id")
                or intent.mutation.get("stat") != choice.get("stat")):
                self._release(record)
                raise WriteSafetyError("TRAINING_BINDING_MISMATCH")
            record.update(native_id=intent.operation_id, intent=intent.to_payload())
            self._state(record, "RESERVED")
            try:
                prepared = self.engine.prepare(self.engine.enroll(path), intent, closed_emulator_confirmed=True)
                if prepared.status != "AWAITING_CONFIRMATION":
                    raise WriteSafetyError(prepared.error or "NATIVE_VERIFICATION_FAILED")
            except Exception:
                self._abandon(record)
                raise
            try:
                applied = self.engine.confirm(intent.operation_id, closed_emulator_confirmed=True,
                    paired_permit=PairedApplyPermit(intent.operation_id))
            except WriteSafetyError:
                local = self._local(record)
                if local and not local.get("commit_started"):
                    self._abandon(record)
                raise
            self.controller._record(applied)
            self._gate()
            if applied.status == "REJECTED":
                self._release(record)
                raise WriteSafetyError(applied.error or "NATIVE_VERIFICATION_FAILED")
            if applied.status != "APPLIED_VERIFIED" or applied.current_matches_receipt is not True:
                raise WriteSafetyError("TRAINING_RECOVERY_REQUIRED")
            local = self._local(record)
            record["output_sha256"] = local["output_hash"]
            self._state(record, "WRITTEN")
            try:
                self._complete(record)
                status = "APPLIED"
            except BackendError:
                status = "PENDING"  # never release after a verified write
            return {"status": status, "operation_id": record["operation_id"],
                    "purchase_id": args["purchase_id"], "game": intent.game}
