"""Local confirmation/controller seam. No remote intent or entitlement intake."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from app.launcher.save_activity import SaveBusy
from app.launcher.write_engine import EngineeringCapability
from app.launcher.write_files import WriteSafetyError


class LocalWriteController:
    def __init__(self, gate, selected, engine=None, *, on_verified=None):
        self.gate, self.selected, self.engine = gate, selected, engine
        self.on_verified = on_verified or (lambda: None)
        self._lock = threading.RLock()
        self._operation_lock = threading.Lock()
        self._busy = False
        self._receipt = None
        self._pending = ()
        self._selection = None
        self._error = None
        self._description = None
        self._export_intent = None
        self._backups = []
        self._backup_selection = None
        self._backup_message = None
        self._notice_key = self._notice = None
        if engine is not None:
            try:
                self._pending = engine.pending()
                if self._pending:
                    self.gate.recovery_required = True
                    self._receipt = self._pending[0]
            except (
                Exception
            ):  # journal uncertainty blocks sync, never implies no intent
                self.gate.recovery_required = True
                self._error = "RECOVERY_REQUIRED"
            if self._transfer_notice() is not None:
                self.gate.recovery_required = True

    def _transfer_notice(self):
        if self.engine is None:
            return None
        # A pure read of the engine database for the selected save. The 1 s
        # state poll reuses it while neither changes, instead of reopening the
        # database and re-running its path checks every time; any change to
        # the file (including a path now resolving to another file) or to the
        # selection reads it again with every check.
        # Two commits inside one timestamp tick can leave mtime and size equal,
        # so SQLite's own file change counter (header bytes 24-27, bumped on
        # every commit in rollback-journal mode) is part of the key.
        try:
            info = self.engine.database.stat()
            with self.engine.database.open("rb") as handle:
                counter = handle.read(28)[24:28]
            selected = self.selected()
            key = (
                info.st_ino,
                info.st_mtime_ns,
                info.st_size,
                counter,
                str(Path(selected).absolute()) if selected else None,
            )
        except (OSError, TypeError, ValueError):
            key = None
        if key is not None and key == self._notice_key:
            return self._notice
        notice = self._read_transfer_notice()
        self._notice_key, self._notice = key, notice
        return notice

    def _read_transfer_notice(self):
        from app.launcher.transfer import TRANSFER_MESSAGES

        try:
            with self.engine._db() as db:
                if not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transfer_bindings'"
                ).fetchone():
                    return None
                rows = [
                    row
                    for row in db.execute(
                        "SELECT record FROM transfer_bindings"
                    ).fetchall()
                    if json.loads(row[0]).get("state") not in ("COMMITTED", "CANCELLED")
                ]
            for row in rows:
                record = json.loads(row[0])
                if record["binding"]["path"] == str(Path(self.selected()).absolute()):
                    return TRANSFER_MESSAGES.get(
                        record["state"], TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
                    )
            if rows:
                return TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
        except (sqlite3.Error, ValueError, TypeError, KeyError, OSError):
            return TRANSFER_MESSAGES["RECOVERY_REQUIRED"]
        return None

    def state(self):
        with self._lock:
            receipt = self._receipt
            transfer_notice = self._transfer_notice()
            state = receipt.status if receipt else "IDLE"
            if self.gate.recovery_required:
                state = "RECOVERY_REQUIRED"
            return {
                "status": state,
                "operation_id": receipt.operation_id if receipt else None,
                "game": receipt.game if receipt else None,
                "can_confirm": not self._busy
                and transfer_notice is None
                and state == "AWAITING_CONFIRMATION"
                and self._confirmable(receipt),
                "can_export": not self._busy
                and self._export_intent is not None
                and type(getattr(self.engine, "capability", None))
                is EngineeringCapability,
                "export_intent": self._export_intent.to_payload()
                if self._export_intent is not None
                else None,
                "can_reconcile": not self._busy and bool(self._pending or receipt),
                "busy": self._busy,
                "production_operations_enabled": False,
                "description": self._description,
                "mode": receipt.mode if receipt else None,
                "export_path": receipt.export_path if receipt else None,
                "applied_to_source": receipt.applied_to_source if receipt else False,
                "backups": self._backups
                if self._backup_selection == self.selected()
                else [],
                "backup_message": self._backup_message,
                "restart_blocked_by_recovery": self._busy
                or self.gate.recovery_required,
                "emulator_restart_allowed": False,  # no real lifecycle adapter qualified
                "emulator_qualified": False,
                # Exact private errors, fingerprints, paths and parameters stay local.
                "message": "Comprobando la operación local. Mantén el juego cerrado."
                if self._busy
                else transfer_notice or self._message(state),
            }

    def _confirmable(self, receipt):
        try:
            return bool(receipt) and self.engine.allows_operation(receipt.operation_id)
        except Exception:  # noqa: BLE001 - unreadable journal never becomes a confirmable write
            return False

    @staticmethod
    def _message(state):
        return {
            "IDLE": "No hay cambios autorizados pendientes. Los canjes sobre el save siguen desactivados.",
            "PREPARED": "Cambio preparado. Falta comprobarlo antes de pedir confirmación.",
            "AWAITING_CONFIRMATION": "Hay un cambio local preparado. Cierra el juego y el emulador antes de confirmarlo.",
            "APPLIED_VERIFIED": "Cambio guardado y comprobado. La copia original se conserva.",
            "EXPORTED_VERIFIED": "Copia exportada y comprobada. La partida original no se ha modificado.",
            "RESTORED_VERIFIED": "Se ha recuperado y comprobado la copia original.",
            "REJECTED": "El cambio no se ha aplicado. Revisa el archivo y vuelve a preparar la acción.",
            "RECOVERY_REQUIRED": "Hay una operación pendiente de comprobar. Se ha pausado la sincronización. Conserva las copias de recuperación.",
        }.get(
            state,
            "No se puede confirmar el estado de la operación. Conserva las copias.",
        )

    @contextmanager
    def _operation(self, *, recovery=False):
        if not self._operation_lock.acquire(blocking=False):
            raise SaveBusy("SAVE_WRITE_BUSY")
        try:
            with self.gate.writing(recovery=recovery):
                with self._lock:
                    self._busy = True
                try:
                    yield
                except Exception:
                    # Reconcile durable uncertainty before releasing the lease.
                    # Even a callback/UI failure cannot resume a stale upload.
                    try:
                        pending = self.engine.pending()
                        self.gate.recovery_required = (
                            self.gate.recovery_required
                            or any(
                                r.status in ("RECOVERY_REQUIRED", "PREPARED")
                                for r in pending
                            )
                        )
                    except Exception:
                        self.gate.recovery_required = True
                    raise
                finally:
                    with self._lock:
                        self._busy = False
        finally:
            self._operation_lock.release()

    def _record(self, receipt):
        pending = self.engine.pending()
        if receipt.status in ("APPLIED_VERIFIED", "RESTORED_VERIFIED"):
            try:
                # The cloud/read lease cannot resume with the previous receipt.
                self.on_verified()
            except Exception:
                self.gate.recovery_required = True
                raise
        try:
            description = self._describe(self.engine.intent_for(receipt.operation_id))
        except (AttributeError, WriteSafetyError):
            description = "Exportación preparada. Se creará un archivo nuevo y se conservará el save original."
        with self._lock:
            self._receipt = receipt
            self._pending = pending
            self._description = description
        self.gate.recovery_required = any(
            r.status in ("RECOVERY_REQUIRED", "PREPARED") for r in pending
        )
        if self.engine is not None and hasattr(self.engine, "backups_for"):
            self._backups = self.engine.backups_for(self.selected())
            self._backup_selection = self.selected()

    def _selected_backup(self, operation_id):
        if (
            self.engine is None
            or not self.selected()
            or self.engine.target_path(operation_id) != Path(self.selected()).absolute()
        ):
            raise WriteSafetyError("BACKUP_SELECTION_CHANGED")

    def refresh_backups(self):
        with self._operation(recovery=True):
            if self.engine is None:
                raise WriteSafetyError("LOCAL_BACKUPS_UNAVAILABLE")
            with self._lock:
                self._backups = self.engine.backups_for(self.selected())
                self._backup_selection = self.selected()
                self._backup_message = None
        return self.state()

    def export_backup(self, operation_id, destination, role="original"):
        with self._operation(recovery=True):
            self._selected_backup(operation_id)
            self.engine.export_backup(
                operation_id, destination=Path(destination), role=role
            )
            with self._lock:
                self._backup_message = (
                    "Copia diaria guardada y verificada. La partida activa no se ha modificado."
                    if role == "daily"
                    else "Copia original guardada y verificada. La partida activa no se ha modificado."
                )
        return self.state()

    def restore_backup(
        self, operation_id, *, closed_emulator_confirmed, restore_confirmed
    ):
        if closed_emulator_confirmed is not True or restore_confirmed is not True:
            raise WriteSafetyError("RESTORE_CONFIRMATION_REQUIRED")
        with self._operation(recovery=True):
            self._selected_backup(operation_id)
            receipt = self.engine.restore(operation_id, closed_emulator_confirmed=True)
            self._record(receipt)
        return self.state()

    @staticmethod
    def _describe(intent):
        change = intent.mutation
        if change.get("kind") == "revive":
            if (
                change.get("location") != "box"
                or change.get("box_index") != 7
                or any(
                    type(change.get(k)) is not int
                    for k in (
                        "slot_index",
                        "destination_box_index",
                        "destination_slot_index",
                    )
                )
                or not 0 <= change["slot_index"] < 30
                or not 0 <= change["destination_box_index"] < 7
                or not 0 <= change["destination_slot_index"] < 30
            ):
                raise WriteSafetyError("INVALID_WRITE_INTENT")
            return (
                f"Revivir: mover el Pokémon de la Caja 8, posición {change['slot_index'] + 1}, "
                f"a la Caja {change['destination_box_index'] + 1}, posición "
                f"{change['destination_slot_index'] + 1}. Se conservan sus atributos y una copia original. "
                "El canje requiere además verificación del servidor."
            )
        if change.get("kind") == "add_item":
            from app.launcher.quick_items import describe

            return describe(change)
        if change.get("kind") != "test_marking":
            raise WriteSafetyError("PRODUCTION_WRITES_DISABLED")
        if change.get("location") == "party":
            location = "equipo"
        elif change.get("location") == "box" and type(change.get("box_index")) is int:
            location = f"caja {change['box_index'] + 1}"
        else:
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        if any(
            type(change.get(key)) is not int
            for key in ("slot_index", "expected_original", "new_value")
        ):
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        return (
            f"Prueba sobre una copia: cambiar la marca del Pokémon en {location}, "
            f"posición {change['slot_index'] + 1}, de {change['expected_original']} "
            f"a {change['new_value']}."
        )

    def offer(self, intent, *, closed_emulator_confirmed):
        """In-process extension point only. Never called with renderer/server plans.

        Production operation registry is empty. A fixture engine is injected
        explicitly by engineering tests; packaged commands cannot grant that capability.
        """
        if self.engine is None or not self.selected():
            raise WriteSafetyError("NO_SELECTED_WRITE_TARGET")
        with self._operation():
            selection = self.engine.enroll(Path(self.selected()))
            # The sole present mutation is a fixture-only marking proof.
            # Unknown future actions cannot borrow this confirmation text.
            self._describe(intent)
            receipt = self.engine.prepare(
                selection,
                intent,
                closed_emulator_confirmed=closed_emulator_confirmed,
            )
            self._record(receipt)
        return self.state()

    def confirm(self, operation_id, *, closed_emulator_confirmed):
        if self.engine is None:
            raise WriteSafetyError("LOCAL_WRITER_UNAVAILABLE")
        with self._operation():
            state = self.state()
            if (
                self.engine is None
                or state["status"] != "AWAITING_CONFIRMATION"
                or operation_id != state["operation_id"]
                or closed_emulator_confirmed is not True
            ):
                raise WriteSafetyError("WRITE_CONFIRMATION_REQUIRED")
            if not self.selected():
                raise WriteSafetyError("NO_SELECTED_WRITE_TARGET")
            current = self.engine.enroll(Path(self.selected()))
            receipt_info = self.engine.status(operation_id)
            if receipt_info.mode == "apply" and current.path != self.engine.target_path(
                operation_id
            ):
                raise WriteSafetyError("WRITE_TARGET_CHANGED")
            receipt = self.engine.confirm(
                operation_id,
                closed_emulator_confirmed=True,
            )
            self._record(receipt)
        return self.state()

    def reconcile(self):
        """Reads/reconciles durable outcomes; never restores or replays a mutation."""
        if self.engine is None:
            raise WriteSafetyError("LOCAL_WRITER_UNAVAILABLE")
        with self._operation(recovery=True):
            pending = self.engine.pending()
            with self._lock:
                receipt = self._receipt
            if not pending and receipt:
                pending = (receipt,)
            for receipt in pending:
                self._record(self.engine.reconcile(receipt.operation_id))
            if not pending:
                self.gate.recovery_required = False
        return self.state()

    # Export is deliberately kept on the same serialized controller seam as
    # physical writes.  The export engine is supplied by the runtime when it
    # becomes available; this small adapter also keeps older engines read-only.
    def prepare_export(self, destination, *, intent, closed_emulator_confirmed):
        if self.engine is None or not self.selected():
            raise WriteSafetyError("NO_SELECTED_WRITE_TARGET")
        method = getattr(self.engine, "prepare_export", None)
        if method is None:
            raise WriteSafetyError("LOCAL_EXPORT_UNAVAILABLE")
        if isinstance(intent, dict):
            if (
                self._export_intent is None
                or intent != self._export_intent.to_payload()
            ):
                raise WriteSafetyError("EXPORT_INTENT_NOT_AUTHORIZED")
            intent = self._export_intent
        with self._operation():
            source = Path(self.selected())
            target = self.engine.enroll(source)
            receipt = method(
                target,
                intent,
                destination_directory=Path(destination),
                closed_emulator_confirmed=closed_emulator_confirmed,
            )
            self._record(receipt)
        return self.state()

    def register_export(self, intent):
        """Install a local, capability-backed export offer.

        This is intentionally an in-process seam. Renderer supplied mutation
        plans never become offers; production currently registers none.
        """
        self._describe(intent)
        with self._lock:
            self._export_intent = intent
            self._description = (
                "Exportar una copia validada; la partida original no se modifica."
            )
        return self.state()

    def confirm_export(self, operation_id, *, closed_emulator_confirmed):
        if self.engine is None:
            raise WriteSafetyError("LOCAL_EXPORT_UNAVAILABLE")
        method = getattr(self.engine, "confirm_export", None) or getattr(
            self.engine, "confirm", None
        )
        if method is None:
            raise WriteSafetyError("LOCAL_EXPORT_UNAVAILABLE")
        with self._operation():
            receipt = method(
                operation_id, closed_emulator_confirmed=closed_emulator_confirmed
            )
            self._record(receipt)
        return self.state()
