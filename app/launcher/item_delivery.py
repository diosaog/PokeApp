"""Paid Shop objects into the bag of the league save (072; owner decision
2026-10-29, «Tienda honesta + entrega en bolsa»).

One delivery is one purchase and one object:
  reserve  - the server holds the purchase; nothing is spent;
  prepare  - verified independent backup, the native one-object change staged
             and natively verified (emulator closed, exact source bytes);
  apply    - only with this flow's in-process permit (the generic «confirm» of
             a prepared change never applies it), then a native re-read;
  complete - the server spends the purchase once, with the source and result
             hashes of the verified write.
Nothing written -> release: the purchase stays usable. The journal
(delivery_bindings, in the write engine's own database) lets any later start
finish an interrupted delivery: a written one is completed, an unwritten one
released, an uncertain one waits for the write journal's recovery. A purchase
is never completed without the verified write, and a new attempt starts only
when the previous one is settled, so an object is never delivered twice.
"""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.shop_item_uses import BAG_ITEMS
from app.launcher.backend import BackendError
from app.launcher.write_engine import PairedApplyPermit, WriteIntent
from app.launcher.write_files import WriteSafetyError

SETTLED = ("DELIVERED", "RELEASED")
FIELDS = {"kind", "item", "quantity", "expected_count", "purchase_id", "attempt"}


class DeliveryRefused(Exception):
    """The server refused the reservation (its API code): nothing was held."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def describe(change):
    if (
        set(change) != FIELDS
        or change["kind"] != "deliver_item"
        or change["item"] not in BAG_ITEMS
        or type(change["quantity"]) is not int
        or change["quantity"] != 1
        or type(change["expected_count"]) is not int
        or change["expected_count"] < 0
    ):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    return (
        f"Añadir 1 × {BAG_ITEMS[change['item']][1]} comprado en la Tienda "
        f"(ahora tienes {change['expected_count']}). Solo cambia esa bolsa; "
        "se conserva una copia del archivo original."
    )


class DeliveryRemote:
    """The trainer's own session: the server derives the trainer from it."""

    def __init__(self, session, season_id):
        self.session = session
        self.sid = str(UUID(season_id))

    def _path(self, operation_id=None, step=""):
        base = f"/v1/launcher/seasons/{self.sid}/deliveries"
        return base if operation_id is None else f"{base}/{UUID(operation_id)}{step}"

    def list(self):
        return self.session.request("GET", self._path())

    def reserve(self, operation_id, purchase_id, item, game):
        body = {"purchase_id": str(UUID(purchase_id)), "item": item, "game": game}
        return self.session.request("PUT", self._path(operation_id), body=body)

    def complete(self, operation_id, source_sha256, output_sha256):
        body = {"source_sha256": source_sha256, "output_sha256": output_sha256}
        return self.session.request(
            "PUT", self._path(operation_id, "/complete"), body=body
        )

    def release(self, operation_id):
        # A reservation that never reached the server has nothing to release.
        return self.session.request(
            "PUT", self._path(operation_id, "/release"), body={}, missing=True
        )


class LauncherDeliveries:
    def __init__(self, controller, remote, *, trainer_id):
        self.controller, self.remote = controller, remote
        self.engine = controller.engine
        self.sid, self.tid = remote.sid, str(UUID(trainer_id))
        if self.engine is None or not self.engine.allows("deliver_item"):
            raise WriteSafetyError("DELIVERY_DISABLED")
        with self.engine._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS delivery_bindings"
                "(id TEXT PRIMARY KEY,record TEXT NOT NULL)"
            )

    # Journal -------------------------------------------------------------
    def bindings(self):
        with self.engine._db() as db:
            rows = db.execute("SELECT record FROM delivery_bindings").fetchall()
        return [json.loads(row[0]) for row in rows]

    def _write(self, record, *, insert=False):
        record["updated_at"] = datetime.now(UTC).isoformat()
        with self.engine._db() as db:
            if insert:
                db.execute(
                    "INSERT INTO delivery_bindings VALUES(?,?)",
                    (record["operation_id"], json.dumps(record)),
                )
            elif (
                db.execute(
                    "UPDATE delivery_bindings SET record=? WHERE id=?",
                    (json.dumps(record), record["operation_id"]),
                ).rowcount
                != 1
            ):
                raise WriteSafetyError("DELIVERY_JOURNAL_INVALID")

    def _state(self, record, state, error=None):
        record.update(state=state, error=error)
        self._write(record)

    def _mine(self, record):
        return record["season_id"] == self.sid and record["trainer_id"] == self.tid

    def pending(self):
        """This trainer's unsettled deliveries in this season."""
        return [r for r in self.bindings() if self._mine(r) and r["state"] not in SETTLED]

    # Server receipts ---------------------------------------------------------
    @staticmethod
    def _receipt(data, record, status):
        if (
            not isinstance(data, dict)
            or data.get("operation_id") != record["operation_id"]
            or data.get("purchase_id") != record["purchase_id"]
            or data.get("status") != status
        ):
            raise WriteSafetyError("DELIVERY_RECEIPT_MISMATCH")
        return data

    def _release(self, record, error=None):
        data = self.remote.release(record["operation_id"])
        if data is not None:
            self._receipt(data, record, "RELEASED")
        self._state(record, "RELEASED", error)

    def _complete(self, record):
        local = self.engine._load(record["operation_id"])
        data = self.remote.complete(
            record["operation_id"], local["intent"]["expected_sha256"], local["output_hash"]
        )
        self._receipt(data, record, "DELIVERED")
        self._state(record, "DELIVERED")
        return data

    def _local(self, operation_id):
        try:
            return self.engine._load(operation_id)
        except WriteSafetyError as error:
            if str(error) == "WRITE_OPERATION_NOT_FOUND":
                return None
            raise

    def _abandon(self, record, error=None):
        """Prepared, never applied: retire the local change, free the purchase."""
        local = self._local(record["operation_id"])
        if local is not None and local.get("commit_started"):
            raise WriteSafetyError("DELIVERY_RECOVERY_REQUIRED")
        if local is not None and local["status"] == "AWAITING_CONFIRMATION":
            try:
                self.engine.cancel_paired_prepared(
                    record["operation_id"],
                    paired_permit=PairedApplyPermit(record["operation_id"]),
                )
            except WriteSafetyError:
                pass  # never applied either way: the reservation is still free
        self._release(record, error)

    # Recovery ----------------------------------------------------------------
    def settle(self):
        """Finish what earlier attempts left (under the write lease). Returns
        the operations still waiting for the write journal's recovery."""
        with self.controller._operation(recovery=True):
            return self._settle()

    def _settle(self):
        waiting = []
        for record in self.pending():
            try:
                if record["state"] == "APPLIED":
                    self._complete(record)
                    continue
                local = self._local(record["operation_id"])
                status = local["status"] if local else None
                if status == "APPLIED_VERIFIED":
                    self._state(record, "APPLIED")
                    self._complete(record)
                elif status in (None, "REJECTED", "RESTORED_VERIFIED"):
                    # Nothing of this attempt is in the save.
                    self._release(record, record.get("error"))
                elif status == "AWAITING_CONFIRMATION" and not local.get("commit_started"):
                    self._abandon(record, record.get("error"))
                else:
                    waiting.append(record["operation_id"])
            except BackendError:
                waiting.append(record["operation_id"])  # offline: next time
        return waiting

    # Delivery ----------------------------------------------------------------
    def deliver(self, purchase_id, item):
        purchase_id = str(UUID(purchase_id))
        if item not in BAG_ITEMS:
            raise WriteSafetyError("DELIVERY_ITEM_INVALID")
        with self.controller._operation(recovery=True):
            self._settle()
            if any(r["purchase_id"] == purchase_id for r in self.pending()):
                raise WriteSafetyError("DELIVERY_PENDING")
        with self.controller._operation():
            path = Path(self.controller.selected())
            data = self.engine.files.read_path(path)
            reading = self.engine.native.inventory(data, (item,))
            if reading["source_sha256"] != sha256(data).hexdigest():
                raise WriteSafetyError("STALE_SOURCE")
            slot = reading["items"][item]
            if slot["max"] == 0:
                raise WriteSafetyError("ITEM_NOT_IN_GAME")
            if slot["addable"] < 1:
                raise WriteSafetyError("INVENTORY_FULL")
            intent = WriteIntent.create(
                expected_sha256=reading["source_sha256"],
                game=reading["game"],
                trainer_key=reading["trainer_key"],
                mutation={
                    "kind": "deliver_item",
                    "item": item,
                    "quantity": 1,
                    "expected_count": slot["count"],
                    "purchase_id": purchase_id,
                    "attempt": str(uuid4()),
                },
            )
            operation = intent.operation_id
            record = {
                "operation_id": operation,
                "season_id": self.sid,
                "trainer_id": self.tid,
                "purchase_id": purchase_id,
                "item": item,
                "game": intent.game,
                "path": str(path.absolute()),
                "intent": intent.to_payload(),
                "state": "RESERVING",
                "error": None,
                "created_at": datetime.now(UTC).isoformat(),
            }
            self._write(record, insert=True)
            try:
                reserved = self.remote.reserve(operation, purchase_id, item, intent.game)
            except BackendError as error:
                if error.status in (403, 404, 409, 422):
                    # A refusal holds nothing on the server.
                    self._state(record, "RELEASED", error.detail)
                    raise DeliveryRefused(error.detail or "DELIVERY_REFUSED") from None
                raise  # unknown outcome: settle() releases it later
            self._receipt(reserved, record, "RESERVED")
            self._state(record, "RESERVED")
            try:
                prepared = self.engine.prepare(
                    self.engine.enroll(path), intent, closed_emulator_confirmed=True
                )
            except Exception as error:
                # Preparation never touches the save.
                self._abandon(record, getattr(error, "code", None))
                raise
            if prepared.status != "AWAITING_CONFIRMATION":
                self._abandon(record, prepared.error)
                raise WriteSafetyError(prepared.error or "PREPARATION_FAILED")
            try:
                applied = self.engine.confirm(
                    operation,
                    closed_emulator_confirmed=True,
                    paired_permit=PairedApplyPermit(operation),
                )
            except WriteSafetyError as error:
                # Raised before any change (e.g. the emulator opened meanwhile).
                self._abandon(record, error.code)
                raise
            self.controller._record(applied)
            if applied.status == "REJECTED":
                self._release(record, applied.error)
                raise WriteSafetyError(applied.error or "NATIVE_VERIFICATION_FAILED")
            if (
                applied.status != "APPLIED_VERIFIED"
                or applied.current_matches_receipt is not True
            ):
                # Uncertain: the reservation stays until the journal decides.
                raise WriteSafetyError("DELIVERY_RECOVERY_REQUIRED")
            self._state(record, "APPLIED")
        # The object is in the bag; the server now spends the purchase once.
        try:
            receipt = self._complete(record)
        except BackendError:
            return {"status": "APPLIED", "operation_id": operation, "game": intent.game}
        return {
            "status": "DELIVERED",
            "operation_id": operation,
            "game": intent.game,
            "purchase_status": receipt.get("purchase_status"),
        }
