"""Local confirmation/controller seam. No remote intent or entitlement intake."""

from contextlib import contextmanager
from pathlib import Path
import threading

from app.launcher.write_files import WriteSafetyError
from app.launcher.save_activity import SaveBusy


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

    def state(self):
        with self._lock:
            receipt = self._receipt
            state = receipt.status if receipt else "IDLE"
            if self.gate.recovery_required:
                state = "RECOVERY_REQUIRED"
            return {
                "status": state,
                "operation_id": receipt.operation_id if receipt else None,
                "game": receipt.game if receipt else None,
                "can_confirm": not self._busy and state == "AWAITING_CONFIRMATION",
                "can_reconcile": not self._busy and bool(self._pending or receipt),
                "busy": self._busy,
                "production_operations_enabled": False,
                "description": self._description,
                # Exact private errors, fingerprints, paths and parameters stay local.
                "message": "Comprobando la operación local. Mantén el juego cerrado."
                if self._busy
                else self._message(state),
            }

    @staticmethod
    def _message(state):
        return {
            "IDLE": "No hay cambios autorizados pendientes. Los canjes sobre el save siguen desactivados.",
            "PREPARED": "Cambio preparado. Falta comprobarlo antes de pedir confirmación.",
            "AWAITING_CONFIRMATION": "Hay un cambio local preparado. Cierra el juego y el emulador antes de confirmarlo.",
            "APPLIED_VERIFIED": "Cambio guardado y comprobado. La copia original se conserva.",
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
        description = self._describe(self.engine.intent_for(receipt.operation_id))
        with self._lock:
            self._receipt = receipt
            self._pending = pending
            self._description = description
        self.gate.recovery_required = any(
            r.status in ("RECOVERY_REQUIRED", "PREPARED") for r in pending
        )

    @staticmethod
    def _describe(intent):
        change = intent.mutation
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
            if current.path != self.engine.target_path(operation_id):
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
