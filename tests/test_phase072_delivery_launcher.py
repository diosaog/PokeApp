"""072 Launcher delivery on the REAL write engine and NTFS, disposable files only.

A synthetic native writer stands in for PKHeX (its byte format is proven by
the C# --shop-item-checks gate on the eight games) and an in-memory server
applies 072's rules: reserve once, complete once with proof, release when
nothing was written. No real save, account or network is used.
"""

import os
import stat
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.launcher.backend import BackendError
from app.launcher.item_delivery import DeliveryRefused, LauncherDeliveries, describe
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import (
    LocalWriteEngine,
    PairedApplyPermit,
    PreparedNative,
    WriteIntent,
)
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError

TRAINER = str(uuid4())
SEASON = str(uuid4())
TRAINER_KEY = sha256(b"fixture trainer").hexdigest()
SLOTS = ("sitrus_berry", "leftovers", "bottle_cap", "fire_gem")
HEADER = b"PKAPP-072-TEST-ONLY"


def save(game="SN", counts=(0, 0, 0, 0)):
    return HEADER + game.encode().ljust(2) + bytes(counts) + b"\0" * 64


class Native:
    """Counts live in fixed bytes; one delivery adds one to its byte."""

    def __init__(self, maximum=999):
        self.maximum = maximum

    @staticmethod
    def _read(data):
        if not data.startswith(HEADER):
            raise ValueError("not a fixture")
        game = data[len(HEADER) : len(HEADER) + 2].decode().strip()
        counts = data[len(HEADER) + 2 : len(HEADER) + 6]
        return game, counts

    def inventory(self, data, items=None):
        game, counts = self._read(data)
        result = {}
        for name in items:
            holdable = name != "bottle_cap" or game in ("SN", "MN", "US", "UM")
            count = counts[SLOTS.index(name)]
            maximum = min(self.maximum, 255) if holdable else 0
            result[name] = {
                "count": count if holdable else 0,
                "max": maximum,
                "addable": max(0, maximum - count) if holdable else 0,
            }
        return {
            "game": game,
            "trainer_key": TRAINER_KEY,
            "source_sha256": sha256(data).hexdigest(),
            "items": result,
        }

    def validate_original(self, source, intent):
        game, _ = self._read(source)
        if game != intent.game or intent.trainer_key != TRAINER_KEY:
            raise ValueError("wrong trainer")

    def prepare(self, source, intent):
        game, counts = self._read(source)
        m = intent.mutation
        index = SLOTS.index(m["item"])
        if m["kind"] != "deliver_item" or counts[index] != m["expected_count"]:
            raise ValueError("stale")
        changed = bytearray(source)
        changed[len(HEADER) + 2 + index] += 1
        output = bytes(changed)
        return PreparedNative(
            output,
            game,
            TRAINER_KEY,
            sha256(source).hexdigest(),
            sha256(output).hexdigest(),
            dict(m, preserved_unrelated=True),
            {"writer_version": "test-only"},
        )

    def verify(self, original, persisted, intent, prepared):
        expected = self.prepare(original, intent)
        if persisted != expected.output:
            raise ValueError("unintended difference")


class Server:
    """072's SQL rules for one trainer, in memory."""

    def __init__(self, purchases):
        self.sid = SEASON
        self.purchases = dict(purchases)
        self.deliveries = {}
        self.calls = []
        self.fail = {}

    def _receipt(self, op):
        d = self.deliveries[op]
        return dict(d, operation_id=op, purchase_status=self.purchases[d["purchase_id"]])

    def _maybe_fail(self, step):
        error = self.fail.pop(step, None)
        if error is not None and not getattr(error, "after", False):
            raise error
        return error

    def reserve(self, op, purchase_id, item, game):
        self.calls.append(("reserve", op))
        self._maybe_fail("reserve")
        if op in self.deliveries:
            return self._receipt(op)
        if self.purchases.get(purchase_id) != "pending":
            raise BackendError(
                "OBSERVATION_REJECTED", status=409, detail="PURCHASE_NOT_REDEEMABLE"
            )
        if any(
            d["purchase_id"] == purchase_id and d["status"] != "RELEASED"
            for d in self.deliveries.values()
        ):
            raise BackendError(
                "OBSERVATION_REJECTED", status=409, detail="DELIVERY_IN_PROGRESS"
            )
        self.deliveries[op] = {
            "purchase_id": purchase_id,
            "item_code": item,
            "game": game,
            "status": "RESERVED",
        }
        return self._receipt(op)

    def complete(self, op, source, output):
        self.calls.append(("complete", op))
        lost = self._maybe_fail("complete")
        d = self.deliveries[op]
        if d["status"] == "RESERVED":
            assert source != output
            d.update(status="DELIVERED", source=source, output=output)
            self.purchases[d["purchase_id"]] = "used"
        elif d["status"] != "DELIVERED" or (d["source"], d["output"]) != (source, output):
            raise BackendError("OBSERVATION_REJECTED", status=409, detail="DELIVERY_NOT_RESERVED")
        if lost is not None:
            raise lost  # applied on the server, answer lost on the way back
        return self._receipt(op)

    def release(self, op):
        self.calls.append(("release", op))
        if op not in self.deliveries:
            return None  # 404: the reservation never reached the server
        d = self.deliveries[op]
        if d["status"] == "DELIVERED":
            raise BackendError("OBSERVATION_REJECTED", status=409, detail="DELIVERY_ALREADY_COMPLETED")
        d["status"] = "RELEASED"
        return self._receipt(op)


def lost(code="BACKEND_UNAVAILABLE"):
    error = BackendError(code)
    error.after = True
    return error


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class DeliveryFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-072-")
        self.root = Path(self.tmp.name)
        self.saves = self.root / "emulator"
        self.saves.mkdir()
        self.target = self.saves / "main"
        self.target.write_bytes(save())
        self.processes = []
        self.engine = LocalWriteEngine(
            self.root / "profile",
            Native(),
            files=WindowsWriteFiles(process_names=lambda: list(self.processes)),
        )
        self.gate = SaveActivityGate()
        self.controller = LocalWriteController(
            self.gate, lambda: str(self.target), self.engine
        )
        self.purchase = str(uuid4())
        self.server = Server({self.purchase: "pending"})
        self.flow = LauncherDeliveries(self.controller, self.server, trainer_id=TRAINER)

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.tmp.cleanup()

    def counts(self):
        return Native._read(self.target.read_bytes())[1]

    def states(self):
        return sorted(r["state"] for r in self.flow.bindings())

    def test_delivery_reserves_writes_rereads_and_spends_once(self):
        result = self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual("DELIVERED", result["status"])
        self.assertEqual("SN", result["game"])
        self.assertEqual(1, self.counts()[0])
        self.assertEqual("used", self.server.purchases[self.purchase])
        self.assertEqual(["reserve", "complete"], [c[0] for c in self.server.calls])
        self.assertEqual(["DELIVERED"], self.states())
        local = self.engine.status(result["operation_id"])
        self.assertEqual("APPLIED_VERIFIED", local.status)
        # The independent backup holds the original bytes.
        backups = list((self.root / "profile" / "write-backups").glob("*.original"))
        self.assertEqual([save()], [b.read_bytes() for b in backups])
        # The purchase is spent: a second click writes nothing.
        with self.assertRaises(DeliveryRefused) as refused:
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual("PURCHASE_NOT_REDEEMABLE", refused.exception.code)
        self.assertEqual(1, self.counts()[0])

    def test_refused_reservation_never_touches_the_save(self):
        self.server.purchases[self.purchase] = "refunded"
        with self.assertRaises(DeliveryRefused):
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual(save(), self.target.read_bytes())
        self.assertEqual(["RELEASED"], self.states())
        self.assertEqual((), self.engine.pending())

    def test_open_emulator_releases_the_purchase(self):
        self.processes.append("Lime3DS.exe")
        with self.assertRaises(WriteSafetyError) as caught:
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual("EMULATOR_RUNNING", caught.exception.code)
        self.assertEqual(save(), self.target.read_bytes())
        self.assertEqual("pending", self.server.purchases[self.purchase])
        self.assertEqual(["RELEASED"], self.states())
        # Closed emulator: the same purchase is delivered once.
        self.processes.clear()
        self.assertEqual("DELIVERED", self.flow.deliver(self.purchase, "sitrus_berry")["status"])
        self.assertEqual(1, self.counts()[0])

    def test_lost_completion_is_finished_by_settle_without_a_second_write(self):
        self.server.fail["complete"] = lost()
        result = self.flow.deliver(self.purchase, "leftovers")
        self.assertEqual("APPLIED", result["status"])
        self.assertEqual(1, self.counts()[1])
        self.assertEqual(["APPLIED"], self.states())
        self.assertEqual([], self.flow.settle())
        self.assertEqual(["DELIVERED"], self.states())
        self.assertEqual(1, self.counts()[1])
        self.assertEqual("used", self.server.purchases[self.purchase])

    def test_offline_completion_waits_and_then_completes(self):
        self.server.fail["complete"] = BackendError("BACKEND_UNAVAILABLE")
        self.assertEqual("APPLIED", self.flow.deliver(self.purchase, "fire_gem")["status"])
        self.assertEqual("pending", self.server.purchases[self.purchase])
        self.server.fail["complete"] = BackendError("BACKEND_UNAVAILABLE")
        waiting = self.flow.settle()
        self.assertEqual(1, len(waiting))
        self.assertEqual([], self.flow.settle())
        self.assertEqual("used", self.server.purchases[self.purchase])
        self.assertEqual(1, self.counts()[3])

    def test_lost_reservation_answer_is_released_by_settle(self):
        self.server.fail["reserve"] = BackendError("BACKEND_UNAVAILABLE")
        with self.assertRaises(BackendError):
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual(["RESERVING"], self.states())
        self.assertEqual([], self.flow.settle())  # never reached the server: 404
        self.assertEqual(["RELEASED"], self.states())
        self.assertEqual(save(), self.target.read_bytes())

    def test_crash_after_apply_before_journal_completes_on_settle(self):
        record = self._reserved_only()
        intent = WriteIntent.create(**record["intent"])
        self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.engine.confirm(
            intent.operation_id,
            closed_emulator_confirmed=True,
            paired_permit=PairedApplyPermit(intent.operation_id),
        )
        self.assertEqual([], self.flow.settle())
        self.assertEqual(["DELIVERED"], self.states())
        self.assertEqual("used", self.server.purchases[self.purchase])
        self.assertEqual(1, self.counts()[0])

    def test_crash_after_reserve_before_prepare_releases(self):
        self._reserved_only()
        self.assertEqual([], self.flow.settle())
        self.assertEqual(["RELEASED"], self.states())
        self.assertEqual("pending", self.server.purchases[self.purchase])
        self.assertEqual(save(), self.target.read_bytes())

    def test_prepared_but_unapplied_is_abandoned_and_released(self):
        record = self._reserved_only()
        intent = WriteIntent.create(**record["intent"])
        self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual([], self.flow.settle())
        self.assertEqual(["RELEASED"], self.states())
        self.assertEqual("REJECTED", self.engine.status(intent.operation_id).status)
        self.assertEqual(save(), self.target.read_bytes())

    def test_generic_confirmation_can_never_apply_a_delivery(self):
        record = self._reserved_only()
        intent = WriteIntent.create(**record["intent"])
        self.controller.offer(intent, closed_emulator_confirmed=True)
        state = self.controller.state()
        self.assertEqual("AWAITING_CONFIRMATION", state["status"])
        self.assertFalse(state["can_confirm"])
        with self.assertRaises(WriteSafetyError) as caught:
            self.engine.confirm(intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual("DELIVERY_COORDINATED_APPLICATION_REQUIRED", caught.exception.code)
        self.assertEqual(save(), self.target.read_bytes())

    def test_full_bag_and_absent_object_hold_nothing(self):
        self.target.write_bytes(save(counts=(255, 0, 0, 0)))
        with self.assertRaises(WriteSafetyError) as full:
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual("INVENTORY_FULL", full.exception.code)
        self.target.write_bytes(save(game="Y"))
        with self.assertRaises(WriteSafetyError) as absent:
            self.flow.deliver(self.purchase, "bottle_cap")
        self.assertEqual("ITEM_NOT_IN_GAME", absent.exception.code)
        self.assertEqual([], self.server.calls)
        self.assertEqual([], self.flow.bindings())

    def test_unsettled_attempt_blocks_a_new_one(self):
        record = self._reserved_only()
        intent = WriteIntent.create(**record["intent"])
        self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        # The journal cannot settle while the release call is offline.
        original = self.server.release

        def offline(op):
            raise BackendError("BACKEND_UNAVAILABLE")

        self.server.release = offline
        with self.assertRaises(WriteSafetyError) as caught:
            self.flow.deliver(self.purchase, "sitrus_berry")
        self.assertEqual("DELIVERY_PENDING", caught.exception.code)
        self.server.release = original
        self.assertEqual("DELIVERED", self.flow.deliver(self.purchase, "sitrus_berry")["status"])
        self.assertEqual(1, self.counts()[0])

    def test_confirmation_text_only_for_the_exact_shape(self):
        change = {
            "kind": "deliver_item",
            "item": "bottle_cap",
            "quantity": 1,
            "expected_count": 2,
            "purchase_id": self.purchase,
            "attempt": str(uuid4()),
        }
        self.assertIn("Chapa Plateada", describe(change))
        for bad in (
            dict(change, quantity=2),
            dict(change, item="rare_candy"),
            dict(change, kind="add_item"),
            {k: v for k, v in change.items() if k != "attempt"},
        ):
            with self.assertRaises(WriteSafetyError):
                describe(bad)

    def _reserved_only(self):
        """A reservation the Launcher recorded and the server accepted, then
        the process ended before anything else happened."""
        data = self.target.read_bytes()
        intent = WriteIntent.create(
            expected_sha256=sha256(data).hexdigest(),
            game="SN",
            trainer_key=TRAINER_KEY,
            mutation={
                "kind": "deliver_item",
                "item": "sitrus_berry",
                "quantity": 1,
                "expected_count": 0,
                "purchase_id": self.purchase,
                "attempt": str(uuid4()),
            },
        )
        record = {
            "operation_id": intent.operation_id,
            "season_id": SEASON,
            "trainer_id": TRAINER,
            "purchase_id": self.purchase,
            "item": "sitrus_berry",
            "game": "SN",
            "path": str(self.target.absolute()),
            "intent": intent.to_payload(),
            "state": "RESERVED",
            "error": None,
            "created_at": "2026-10-29T00:00:00+00:00",
        }
        self.flow._write(record, insert=True)
        self.server.reserve(intent.operation_id, self.purchase, "sitrus_berry", "SN")
        return record


if __name__ == "__main__":
    unittest.main()
