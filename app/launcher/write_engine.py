"""Durable local write protocol; no production mutation kinds are enabled.

Only an explicit in-process engineering capability admits the isolated fixture
mutation. Neither an API/renderer JSON object nor a database right grants it.
This does not certify a hostile same-user filesystem or arbitrary emulator
discovery. The NTFS pathname replacement limitation is in write_files.py.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from app.launcher.export_files import WindowsExportFiles
from app.launcher.write_files import EnrolledTarget, WindowsWriteFiles, WriteSafetyError

GAMES = frozenset(("X", "Y", "OR", "AS", "SN", "MN", "US", "UM"))
PRODUCTION_MUTATIONS: frozenset[str] = frozenset()
PENDING = ("PREPARED", "AWAITING_CONFIRMATION", "RECOVERY_REQUIRED")


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._mutex:
            if self._operation_depth:
                return method(self, *args, **kwargs)
            if method.__name__ in ("prepare", "prepare_export"):
                target = args[0] if args else kwargs["target"]
                intent = args[1] if len(args) > 1 else kwargs["intent"]
                self._authorize(target, intent)
            else:
                identifier = args[0] if args else kwargs["operation_id"]
                target = self._target(self._load(identifier))
            target_key = _hash(os.path.normcase(target.path.name).encode("utf-8"))[:32]
            target_lock = target.path.parent / (
                ".pokeapp-write-" + target_key + ".lock"
            )
            with self.files.operation_lock(self.profile / "physical-write.lock"):
                # The path-derived lease also excludes other PokeApp profiles.
                # It does not claim to control external programs ignoring it.
                with self.files.operation_lock(target_lock):
                    self._operation_depth += 1
                    try:
                        return method(self, *args, **kwargs)
                    finally:
                        self._operation_depth -= 1

    return call


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class WriteIntent:
    expected_sha256: str
    game: str
    trainer_key: str
    mutation: dict

    @classmethod
    def create(
        cls, *, expected_sha256: str, game: str, trainer_key: str, mutation: dict
    ):
        if (
            game not in GAMES
            or not re.fullmatch("[0-9a-f]{64}", expected_sha256)
            or not re.fullmatch("[0-9a-f]{64}", trainer_key)
            or not isinstance(mutation, dict)
        ):
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        # Deep-copy removes caller-owned mutable references from the authorized intent.
        clean = json.loads(_json(mutation))
        if len(_json(clean)) > 4096:
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        return cls(expected_sha256, game, trainer_key, clean)

    def to_payload(self) -> dict:
        return {
            "expected_sha256": self.expected_sha256,
            "game": self.game,
            "trainer_key": self.trainer_key,
            "mutation": json.loads(_json(self.mutation)),
        }

    @property
    def operation_id(self) -> str:
        return str(
            uuid5(NAMESPACE_URL, "pokeapp-local-write/1:" + _json(self.to_payload()))
        )


@dataclass(frozen=True)
class PreparedNative:
    output: bytes
    game: str
    trainer_key: str
    source_hash: str
    output_hash: str
    semantic_diff: dict
    contract: dict


class NativeWriter(Protocol):
    def prepare(self, source: bytes, intent: WriteIntent) -> PreparedNative: ...
    def verify(
        self,
        original: bytes,
        persisted: bytes,
        intent: WriteIntent,
        prepared: PreparedNative,
    ) -> None: ...


@dataclass(frozen=True)
class EngineeringCapability:
    """Held only by the explicit local fixture harness; never reconstructed from JSON."""

    fixture_root: Path

    @classmethod
    def for_fixture_root(cls, root: Path):
        return cls(WindowsWriteFiles().directory(root))


@dataclass(frozen=True)
class WriteReceipt:
    operation_id: str
    status: str
    game: str
    error: str | None = None
    current_matches_receipt: bool | None = None
    mode: str = "apply"
    export_path: str | None = None
    applied_to_source: bool = False

    def public_status(self) -> dict:
        result = {
            "operation_id": self.operation_id,
            "status": self.status,
            "game": self.game,
            "error": self.error,
            "current_matches_receipt": self.current_matches_receipt,
        }
        if self.mode == "export" or self.status == "EXPORTED_VERIFIED":
            result.update(
                mode=self.mode,
                export_path=self.export_path,
                applied_to_source=self.applied_to_source,
            )
        return result


class LocalWriteEngine:
    def __init__(
        self,
        profile: Path,
        native: NativeWriter,
        *,
        files: WindowsWriteFiles | None = None,
        engineering_capability: EngineeringCapability | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ):
        self.files = files or WindowsWriteFiles()
        self.profile = self.files.directory(profile, create=True)
        self.artifacts = self.files.directory(
            self.profile / "write-backups", create=True
        )
        self.database = self.profile / "physical-writes.sqlite3"
        self.native, self.capability = native, engineering_capability
        self.export_files = WindowsExportFiles()
        self.fault_hook = fault_hook or (lambda _stage: None)
        self._mutex, self._operation_depth = RLock(), 0
        self._db_check()
        with self._db() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS physical_writes "
                "(id TEXT PRIMARY KEY, record TEXT NOT NULL)"
            )

    def _db_check(self):
        self.files.path(self.profile, directory=True)
        self.files.path(self.artifacts, directory=True)
        if self.database.exists():
            self.files.path(self.database)

    @contextmanager
    def _db(self):
        self._db_check()
        connection = sqlite3.connect(self.database, timeout=5)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=DELETE")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _load(self, operation_id: str) -> dict:
        operation_id = str(UUID(operation_id))
        with self._db() as connection:
            row = connection.execute(
                "SELECT record FROM physical_writes WHERE id=?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise WriteSafetyError("WRITE_OPERATION_NOT_FOUND")
        record = json.loads(row[0])
        if record["operation_id"] != operation_id:
            raise WriteSafetyError("WRITE_JOURNAL_INVALID")
        return record

    def _save(self, record: dict, *, insert: bool = False):
        with self._db() as connection:
            if insert:
                connection.execute(
                    "INSERT INTO physical_writes VALUES (?,?)",
                    (record["operation_id"], _json(record)),
                )
            else:
                count = connection.execute(
                    "UPDATE physical_writes SET record=? WHERE id=?",
                    (_json(record), record["operation_id"]),
                ).rowcount
                if count != 1:
                    raise WriteSafetyError("WRITE_JOURNAL_INVALID")

    @staticmethod
    def _receipt(record: dict, current_matches: bool | None = None) -> WriteReceipt:
        return WriteReceipt(
            record["operation_id"],
            record["status"],
            record["intent"]["game"],
            record.get("error"),
            current_matches,
            record.get("mode", record.get("phase", "apply")),
            record.get("final_path"),
            record.get("status") == "APPLIED_VERIFIED",
        )

    def status(self, operation_id: str) -> WriteReceipt:
        return self._receipt(self._load(operation_id))

    def target_path(self, operation_id: str) -> Path:
        """Local controller only; this path is never part of the public receipt."""
        return self._target(self._load(operation_id)).path

    def intent_for(self, operation_id: str) -> WriteIntent:
        return WriteIntent.create(**self._load(operation_id)["intent"])

    def pending(self) -> tuple[WriteReceipt, ...]:
        with self._db() as connection:
            records = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT record FROM physical_writes ORDER BY id"
                )
            ]
        return tuple(self._receipt(row) for row in records if row["status"] in PENDING)

    def enroll(self, path: Path) -> EnrolledTarget:
        return self.files.enroll(path)

    def _authorize(self, target: EnrolledTarget, intent: WriteIntent):
        # Revalidate even if code constructed the dataclass directly.
        valid = WriteIntent.create(**intent.to_payload())
        if valid != intent:
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        capability = self.capability
        if (
            type(capability) is not EngineeringCapability
            or intent.mutation.get("kind") != "test_marking"
            or target.path == capability.fixture_root
            or not target.path.is_relative_to(capability.fixture_root)
        ):
            raise WriteSafetyError("PRODUCTION_WRITES_DISABLED")
        self.files.path(capability.fixture_root, directory=True)

    def _native_prepare(self, source: bytes, intent: WriteIntent) -> PreparedNative:
        try:
            result = self.native.prepare(source, intent)
            if (
                not isinstance(result, PreparedNative)
                or result.game != intent.game
                or result.trainer_key != intent.trainer_key
                or result.source_hash != _hash(source)
                or result.output_hash != _hash(result.output)
                or len(source) != len(result.output)
                or result.output == source
                or not isinstance(result.semantic_diff, dict)
                or not result.semantic_diff
                or not isinstance(result.contract, dict)
                or not result.contract
                or len(_json(result.semantic_diff)) > 16384
                or len(_json(result.contract)) > 16384
            ):
                raise WriteSafetyError("INVALID_NATIVE_RESULT")
            self.native.verify(source, result.output, intent, result)
            return result
        except WriteSafetyError:
            raise
        except Exception:
            raise WriteSafetyError("NATIVE_VERIFICATION_FAILED") from None

    def _verify(
        self,
        original: bytes,
        persisted: bytes,
        intent: WriteIntent,
        prepared: PreparedNative,
    ):
        if (
            _hash(original) != intent.expected_sha256
            or _hash(persisted) != prepared.output_hash
        ):
            raise WriteSafetyError("ARTIFACT_HASH_CHANGED")
        try:
            self.native.verify(original, persisted, intent, prepared)
        except Exception:
            raise WriteSafetyError("NATIVE_VERIFICATION_FAILED") from None

    @staticmethod
    def _target(record: dict) -> EnrolledTarget:
        return EnrolledTarget(Path(record["target"]), record["device"], record["inode"])

    def _materials(self, record: dict) -> tuple[WriteIntent, bytes, PreparedNative]:
        intent = WriteIntent.create(**record["intent"])
        backup_path = self.artifacts / (record["operation_id"] + ".original")
        original = self.files.read_path(backup_path)
        if _hash(original) != intent.expected_sha256 or len(original) != record["size"]:
            raise WriteSafetyError("BACKUP_INVALID")
        prepared = PreparedNative(
            b"",
            intent.game,
            intent.trainer_key,
            intent.expected_sha256,
            record["output_hash"],
            record["semantic_diff"],
            record["contract"],
        )
        return intent, original, prepared

    def _verify_displaced_original(self, record: dict, original: bytes):
        if not record["commit_started"]:
            raise WriteSafetyError("UNEXPECTED_OUTPUT_WITHOUT_COMMIT")
        witness = Path(record["target"]).parent / (
            ".pokeapp-" + record["operation_id"] + ".displaced"
        )
        if self.files.read_path(witness) != original:
            raise WriteSafetyError("DISPLACED_SOURCE_CHANGED")

    @_serialized
    def prepare(
        self,
        target: EnrolledTarget,
        intent: WriteIntent,
        *,
        closed_emulator_confirmed: bool,
    ) -> WriteReceipt:
        self._authorize(target, intent)
        self.files.assert_closed(closed_emulator_confirmed)
        operation_id = intent.operation_id
        try:
            existing = self._load(operation_id)
        except WriteSafetyError as error:
            if error.code != "WRITE_OPERATION_NOT_FOUND":
                raise
        else:
            if existing["intent"] != intent.to_payload() or existing["target"] != str(
                target.path
            ):
                raise WriteSafetyError("OPERATION_ID_REUSED")
            return self.reconcile(operation_id)
        with self.files.locked(target) as stream:
            original = self.files.read(stream)
            if _hash(original) != intent.expected_sha256:
                raise WriteSafetyError("SOURCE_HASH_CHANGED")
            prepared = self._native_prepare(original, intent)
            record = {
                "operation_id": operation_id,
                "intent": intent.to_payload(),
                "target": str(target.path),
                "device": target.device,
                "inode": target.inode,
                "size": len(original),
                "output_hash": prepared.output_hash,
                "semantic_diff": prepared.semantic_diff,
                "contract": prepared.contract,
                "status": "PREPARED",
                "error": None,
                "commit_started": False,
                "phase": "apply",
            }
            self._save(record, insert=True)
            try:
                self.fault_hook("prepared")
                self.files.create_verified(
                    self.artifacts / (operation_id + ".original"),
                    original,
                    immutable=True,
                )
                self.fault_hook("backup_verified")
                self.files.create_verified(
                    target.path.parent / (".pokeapp-" + operation_id + ".stage"),
                    prepared.output,
                )
                self.fault_hook("stage_verified")
                if self.files.read(stream) != original:
                    raise WriteSafetyError("SOURCE_HASH_CHANGED")
                self.files.assert_same_path(target.path, target.device, target.inode)
                record["status"] = "AWAITING_CONFIRMATION"
                self._save(record)
            except Exception as error:
                record.update(
                    status="REJECTED", error=self._error(error, "PREPARATION_FAILED")
                )
                self._save(record)
                raise WriteSafetyError(record["error"]) from None
        return self._receipt(record)

    @_serialized
    def prepare_export(
        self,
        target: EnrolledTarget,
        intent: WriteIntent,
        *,
        destination_directory: Path,
        closed_emulator_confirmed: bool,
    ) -> WriteReceipt:
        """Prepare a verified new-file export; the selected source is never written."""
        self._authorize(target, intent)
        self.files.assert_closed(closed_emulator_confirmed)
        destination = self.export_files.directory(Path(destination_directory))
        if destination == target.path.parent:
            raise WriteSafetyError("EXPORT_DESTINATION_MUST_BE_SEPARATE")
        operation_id = intent.operation_id
        try:
            existing = self._load(operation_id)
        except WriteSafetyError as error:
            if error.code != "WRITE_OPERATION_NOT_FOUND":
                raise
        else:
            if (
                existing.get("mode") != "export"
                or existing["intent"] != intent.to_payload()
                or existing["target"] != str(target.path)
                or existing["destination"] != str(destination)
            ):
                raise WriteSafetyError("OPERATION_ID_REUSED")
            return self.reconcile(operation_id)
        with self.export_files.strict_source(target.path) as stream:
            original = self.files.read(stream)
            if _hash(original) != intent.expected_sha256:
                raise WriteSafetyError("SOURCE_HASH_CHANGED")
            prepared = self._native_prepare(original, intent)
            final = destination / f"export-{operation_id}.save"
            if final.exists():
                raise WriteSafetyError("EXPORT_DESTINATION_OCCUPIED")
            record = {
                "operation_id": operation_id,
                "intent": intent.to_payload(),
                "target": str(target.path),
                "device": target.device,
                "inode": target.inode,
                "size": len(original),
                "output_hash": prepared.output_hash,
                "semantic_diff": prepared.semantic_diff,
                "contract": prepared.contract,
                "status": "AWAITING_CONFIRMATION",
                "error": None,
                "commit_started": False,
                "phase": "export",
                "mode": "export",
                "destination": str(destination),
                "final_path": str(final),
                "stage_path": None,
                "stage_identity": None,
            }
            self._save(record, insert=True)
            try:
                self.files.create_verified(
                    self.artifacts / (operation_id + ".original"),
                    original,
                    immutable=True,
                )
                self.files.create_verified(
                    self.artifacts / (operation_id + ".export"),
                    prepared.output,
                )
                self.fault_hook("export_prepared")
            except Exception as error:
                record.update(
                    status="REJECTED",
                    error=self._error(error, "EXPORT_PREPARATION_FAILED"),
                )
                self._save(record)
                raise WriteSafetyError(record["error"]) from None
        return self._receipt(record)

    @staticmethod
    def _error(error: Exception, fallback: str) -> str:
        return error.code if isinstance(error, WriteSafetyError) else fallback

    @_serialized
    def confirm(
        self, operation_id: str, *, closed_emulator_confirmed: bool
    ) -> WriteReceipt:
        record = self._load(operation_id)
        if record.get("mode") == "export":
            return self._confirm_export(
                record, closed_emulator_confirmed=closed_emulator_confirmed
            )
        if record["status"] != "AWAITING_CONFIRMATION":
            return self.reconcile(operation_id)
        intent, original, prepared = self._materials(record)
        target = self._target(record)
        self._authorize(target, intent)
        self.files.assert_closed(closed_emulator_confirmed)
        try:
            with self.files.locked(target) as stream:
                if self.files.read(stream) != original:
                    raise WriteSafetyError("SOURCE_HASH_CHANGED")
                stage = target.path.parent / (".pokeapp-" + operation_id + ".stage")
                output = self.files.read_path(stage)
                self._verify(original, output, intent, prepared)
                # Durably record uncertainty BEFORE the only replacement call.
                record.update(
                    status="RECOVERY_REQUIRED",
                    commit_started=True,
                    error="COMMIT_INTERRUPTED",
                )
                self._save(record)
                self.fault_hook("before_replace")
                self.files.assert_closed(closed_emulator_confirmed)
                self.files.assert_same_path(target.path, target.device, target.inode)
                if self.files.read(stream) != original:
                    raise WriteSafetyError("SOURCE_HASH_CHANGED")
                witness = target.path.parent / (
                    ".pokeapp-" + operation_id + ".displaced"
                )
                self.files.replace(target.path, stage, witness)
                self.fault_hook("after_replace")
                if self.files.read_path(witness) != original:
                    raise WriteSafetyError("DISPLACED_SOURCE_CHANGED")
                self.files.flush(target.path)
                current = self.files.enroll(target.path)
                with self.files.locked(current) as final_stream:
                    persisted = self.files.read(final_stream)
                    self._verify(original, persisted, intent, prepared)
                    self.fault_hook("after_verify")
                    self.files.assert_same_path(
                        current.path, current.device, current.inode
                    )
                    record.update(status="APPLIED_VERIFIED", error=None)
                    self._save(record)
                return self._receipt(record, True)
        except Exception as error:
            record.update(
                status="RECOVERY_REQUIRED" if record["commit_started"] else "REJECTED",
                error=self._error(error, "WRITE_FAILED"),
            )
            self._save(record)
            return self._receipt(record)

    def _confirm_export(self, record, *, closed_emulator_confirmed: bool):
        intent, original, prepared = self._materials(record)
        target = self._target(record)
        self._authorize(target, intent)
        self.files.assert_closed(closed_emulator_confirmed)
        final = Path(record["final_path"])
        stage = Path(
            record["stage_path"]
            or (
                Path(record["destination"])
                / f".export-{record['operation_id']}.partial"
            )
        )
        record["stage_path"] = str(stage)
        try:
            with self.export_files.strict_source(target.path) as source:
                if self.files.read(source) != original:
                    raise WriteSafetyError("SOURCE_HASH_CHANGED")
                if final.exists():
                    raise WriteSafetyError("EXPORT_DESTINATION_OCCUPIED")
                record.update(
                    status="RECOVERY_REQUIRED",
                    commit_started=True,
                    error="EXPORT_COMMIT_INTERRUPTED",
                )
                self._save(record)
                with self.export_files.new_stage(stage) as output:
                    data = self.files.read_path(
                        self.artifacts / (record["operation_id"] + ".export")
                    )
                    self._verify(original, data, intent, prepared)
                    if output.write(data) != len(data):
                        raise WriteSafetyError("SHORT_WRITE")
                    output.flush()
                    os.fsync(output.fileno())
                    if self.files.read(output) != data:
                        raise WriteSafetyError("EXPORT_CHANGED_DURING_WRITE")
                    self._verify(original, self.files.read(output), intent, prepared)
                    identity = os.fstat(output.fileno())
                    record["stage_identity"] = [identity.st_dev, identity.st_ino]
                    self._save(record)
                    self.fault_hook("export_stage_created")
                    self.export_files.publish_new(output, final)
                    self.fault_hook("export_after_publish")
                with self.export_files.strict_source(final) as published:
                    persisted = self.files.read(published)
                    self._verify(original, persisted, intent, prepared)
                record.update(
                    status="EXPORTED_VERIFIED", error=None, commit_started=False
                )
                self._save(record)
                return self._receipt(record, False)
        except Exception as error:
            record.update(
                status="RECOVERY_REQUIRED"
                if record.get("commit_started")
                else "REJECTED",
                error=self._error(error, "EXPORT_FAILED"),
            )
            self._save(record)
            return self._receipt(record, False)

    @_serialized
    def reconcile(self, operation_id: str) -> WriteReceipt:
        """Observe before retry; this method NEVER replaces a save."""
        record = self._load(operation_id)
        if record.get("mode") == "export":
            return self._reconcile_export(record)
        if record["status"] == "REJECTED":
            return self._receipt(record)
        try:
            intent, original, prepared = self._materials(record)
            target = self._target(record)
            current = self.files.read_path(target.path)
            digest = _hash(current)
            if record["status"] == "RESTORED_VERIFIED":
                return self._receipt(record, digest == intent.expected_sha256)
            if digest == record["output_hash"]:
                self._verify(original, current, intent, prepared)
                self._verify_displaced_original(record, original)
                if record["phase"] == "restore":
                    record.update(
                        status="RECOVERY_REQUIRED", error="RESTORE_NOT_APPLIED"
                    )
                else:
                    if record["status"] != "APPLIED_VERIFIED":
                        # A failed/crashed post-replace flush is not proof of durability.
                        self.files.flush(target.path)
                        if self.files.read_path(target.path) != current:
                            raise WriteSafetyError("EXTERNAL_CHANGE_PRESERVED")
                    record.update(status="APPLIED_VERIFIED", error=None)
                self._save(record)
                return self._receipt(record, True)
            if record["status"] == "APPLIED_VERIFIED":
                # A later legitimate edit does not undo an established historical receipt.
                return self._receipt(record, False)
            if digest == intent.expected_sha256:
                if record["phase"] == "restore":
                    record.update(status="RESTORED_VERIFIED", error=None)
                elif (
                    record["status"] == "AWAITING_CONFIRMATION"
                    and not record["commit_started"]
                ):
                    stage = target.path.parent / (".pokeapp-" + operation_id + ".stage")
                    self._verify(
                        original, self.files.read_path(stage), intent, prepared
                    )
                    return self._receipt(record, True)
                else:
                    record.update(
                        status="REJECTED", error="INTERRUPTED_WITH_ORIGINAL_PRESERVED"
                    )
                self._save(record)
                return self._receipt(record, True)
            record.update(status="RECOVERY_REQUIRED", error="EXTERNAL_CHANGE_PRESERVED")
        except Exception as error:
            record.update(
                status="RECOVERY_REQUIRED",
                error=self._error(error, "RECOVERY_CHECK_FAILED"),
            )
        self._save(record)
        return self._receipt(record)

    def _reconcile_export(self, record):
        """Read-only export recovery; never retries publication or touches source."""
        if record["status"] == "REJECTED":
            return self._receipt(record)
        try:
            intent, original, prepared = self._materials(record)
            final = Path(record["final_path"])
            if final.name != f"export-{record['operation_id']}.save":
                raise WriteSafetyError("INVALID_EXPORT_DESTINATION")
            if final.exists():
                with self.export_files.strict_source(final) as stream:
                    persisted = self.files.read(stream)
                self._verify(original, persisted, intent, prepared)
                record.update(
                    status="EXPORTED_VERIFIED", error=None, commit_started=False
                )
                self._save(record)
                return self._receipt(record, False)
            stage = Path(record["stage_path"]) if record.get("stage_path") else None
            if stage is not None and stage.exists():
                # A partial is never treated as a completed export.
                record.update(
                    status="RECOVERY_REQUIRED", error="EXPORT_PARTIAL_UNPUBLISHED"
                )
            else:
                record.update(status="RECOVERY_REQUIRED", error="EXPORT_NOT_PUBLISHED")
        except Exception as error:
            record.update(
                status="RECOVERY_REQUIRED",
                error=self._error(error, "EXPORT_RECOVERY_REQUIRED"),
            )
        self._save(record)
        return self._receipt(record, False)

    @_serialized
    def restore(
        self, operation_id: str, *, closed_emulator_confirmed: bool
    ) -> WriteReceipt:
        record = self._load(operation_id)
        if record["status"] == "RESTORED_VERIFIED":
            return self.reconcile(operation_id)
        intent, original, prepared = self._materials(record)
        target = self.files.enroll(Path(record["target"]))
        self._authorize(target, intent)
        self.files.assert_closed(closed_emulator_confirmed)
        try:
            self._verify_displaced_original(record, original)
            with self.files.locked(target) as stream:
                output = self.files.read(stream)
                self._verify(original, output, intent, prepared)
                restore_stage = target.path.parent / (
                    ".pokeapp-" + operation_id + ".restore"
                )
                self.files.create_verified(restore_stage, original)
                record.update(
                    phase="restore",
                    status="RECOVERY_REQUIRED",
                    error="RESTORE_INTERRUPTED",
                    commit_started=True,
                )
                self._save(record)
                self.fault_hook("before_restore")
                self.files.assert_closed(closed_emulator_confirmed)
                self.files.assert_same_path(target.path, target.device, target.inode)
                if self.files.read(stream) != output:
                    raise WriteSafetyError("EXTERNAL_CHANGE_PRESERVED")
                witness = target.path.parent / (
                    ".pokeapp-" + operation_id + ".restored-output"
                )
                self.files.replace(target.path, restore_stage, witness)
                self.fault_hook("after_restore")
                if self.files.read_path(witness) != output:
                    raise WriteSafetyError("DISPLACED_SOURCE_CHANGED")
                self.files.flush(target.path)
                current = self.files.enroll(target.path)
                with self.files.locked(current) as final_stream:
                    if self.files.read(final_stream) != original:
                        raise WriteSafetyError("RESTORE_VERIFICATION_FAILED")
                    self.files.assert_same_path(
                        current.path, current.device, current.inode
                    )
                    record.update(status="RESTORED_VERIFIED", error=None)
                    self._save(record)
                return self._receipt(record, True)
        except Exception as error:
            record.update(
                status="RECOVERY_REQUIRED", error=self._error(error, "RESTORE_FAILED")
            )
            self._save(record)
            return self._receipt(record)


WriteEngine = LocalWriteEngine
