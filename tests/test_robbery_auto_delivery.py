"""Owner rule 2026-11-17: a decided robbery needs no request and no button.

Each Launcher fulfils its own side by itself, through the same safe path as
the manual button. These tests pin when it does and when it waits.
"""

import os
import stat
import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from test_launcher_stability import SEASON, TRAINER, Harness

from app.launcher.runtime import AUTO_TRANSFER_HOLD_SECONDS, save_identity
from app.launcher.save_activity import SaveActivityGate
from app.launcher.transfer import EngineeringTransfer
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WriteSafetyError
from tests.test_phase22_write_engine import SOURCE, engine_at
from tests.test_phase22_write_engine import TRAINER as SAVE_TRAINER
from tests.test_phase24_transfer import Repository

AID = "f" * 8 + "-ffff-4fff-8fff-" + "f" * 12


class AutoDeliveryTests(Harness):
    def setup(self, obligation="DONOR_PHYSICAL_PENDING", *, link=None, running=False):
        runtime = self.runtime()
        self.ready(runtime)
        engine = Mock()
        engine.allows.return_value = True

        class Files:
            @staticmethod
            def assert_closed(confirmed):
                if running:
                    raise WriteSafetyError("EMULATOR_RUNNING")

        engine.files = Files()
        runtime.writes = Mock(engine=engine, state=Mock(return_value={}))
        runtime.session = Mock(
            _principal=Mock(trainer_id=TRAINER),
            _tokens=Mock(expires_at=time.time() + 3600),
        )
        identity = save_identity(runtime.receipt)
        runtime._patch(
            cloud={
                "data": {
                    "season": {"id": SEASON},
                    "season_link": link or {"status": "BOUND", "identity": identity},
                    "transfers": [
                        {
                            "authorization_id": AID,
                            "side": "source" if obligation.startswith("DONOR") else "destination",
                            "status": "COMPETITIVELY_ADJUDICATED",
                            "obligation": obligation,
                            "mandatory": obligation.startswith("DONOR"),
                        }
                    ],
                }
            }
        )
        return runtime

    def run_step(self, runtime, result=None, error=None, bound=()):
        def fake(name, args):
            calls.append((name, dict(args)))
            runtime._patch(transfer_result=result or {"status": "DONOR_VERIFIED"}, write_error=error)

        calls = []
        runtime.writes.open_transfers = Mock(return_value=list(bound))
        with patch.object(runtime, "_transfer_step", side_effect=fake):
            runtime._auto_transfer_step()
        return calls

    def test_a_side_applied_here_only_asks_for_its_proof(self):
        # 2026-11-18: a verified robbery left four trainers paused for good.
        runtime = self.setup()
        calls = self.run_step(
            runtime, bound=[{"authorization_id": AID, "applied": True}]
        )
        self.assertEqual(calls, [("transfer_refresh", {"authorization_id": AID})])
        self.assertIsNone(runtime.state()["write_error"])

    def test_a_bound_side_not_applied_yet_is_fulfilled(self):
        runtime = self.setup()
        calls = self.run_step(
            runtime, bound=[{"authorization_id": AID, "applied": False}]
        )
        self.assertEqual([name for name, _ in calls], ["transfer_fulfil"])

    def test_asking_for_a_proof_that_cannot_match_is_not_repeated_in_a_loop(self):
        runtime = self.setup()
        bound = [{"authorization_id": AID, "applied": True}]
        self.run_step(runtime, {"status": "RECOVERY_REQUIRED"}, bound=bound)
        runtime._next_auto_transfer = 0
        self.assertEqual(self.run_step(runtime, bound=bound), [])

    def test_victim_removal_runs_by_itself_with_the_emulator_closed(self):
        runtime = self.setup()
        calls = self.run_step(runtime)
        self.assertEqual(
            calls,
            [("transfer_fulfil", {"authorization_id": AID, "closed_emulator_confirmed": True})],
        )
        self.assertIsNone(runtime.state()["transfer_auto"])

    def test_robber_receives_by_itself(self):
        runtime = self.setup("RECIPIENT_PHYSICAL_PENDING")
        self.assertEqual(len(self.run_step(runtime, {"status": "RECIPIENT_VERIFIED"})), 1)

    def test_an_open_emulator_only_postpones_and_says_so(self):
        runtime = self.setup(running=True)
        self.assertEqual(self.run_step(runtime), [])
        self.assertEqual(runtime.state()["transfer_auto"], "EMULATOR_OPEN")
        self.assertIsNone(runtime.state()["write_error"])

    def test_another_selected_game_never_receives_the_robbery(self):
        runtime = self.setup(link={"status": "BOUND", "identity": {"game": "SN", "trainer": {}}})
        self.assertEqual(self.run_step(runtime), [])
        self.assertEqual(runtime.state()["transfer_auto"], "WRONG_SAVE")

    def test_settled_or_assisted_sides_are_never_applied(self):
        for obligation in ("DONOR_VERIFIED", "RECIPIENT_VERIFIED", "DONOR_BLOCKED_UNCERTAIN",
                           "DONOR_RECOVERY_REQUIRED", "RECIPIENT_RECOVERY_REQUIRED"):
            with self.subTest(obligation=obligation):
                self.assertEqual(self.run_step(self.setup(obligation)), [])

    def test_a_side_needing_assistance_is_not_retried_in_a_loop(self):
        runtime = self.setup()
        self.assertEqual(len(self.run_step(runtime, {"status": "RECOVERY_REQUIRED"})), 1)
        self.assertGreater(runtime._auto_transfer_hold[AID], time.monotonic() + AUTO_TRANSFER_HOLD_SECONDS - 5)
        runtime._next_auto_transfer = 0
        self.assertEqual(self.run_step(runtime), [])

    def test_a_busy_read_is_retried_soon_without_an_error(self):
        runtime = self.setup()
        busy = "Hay una lectura o sincronización en curso. Espera y vuelve a intentarlo."
        self.assertEqual(len(self.run_step(runtime, {}, busy)), 1)
        self.assertNotIn(AID, runtime._auto_transfer_hold)
        self.assertIsNone(runtime.state()["write_error"])

    def test_it_waits_for_its_turn_and_for_queued_writes(self):
        runtime = self.setup()
        self.assertEqual(len(self.run_step(runtime)), 1)
        self.assertEqual(self.run_step(runtime), [])  # 30 s cadence
        runtime._next_auto_transfer = 0
        runtime.write_commands.put_nowait(("quick_inventory", {}))
        self.assertEqual(self.run_step(runtime), [])

    def test_an_expired_session_waits_for_the_cloud_loop_to_renew_it(self):
        runtime = self.setup()
        runtime.session._tokens.expires_at = time.time() - 10
        bound = [{"authorization_id": AID, "applied": True}]
        self.assertEqual(self.run_step(runtime, bound=bound), [])
        runtime.session._tokens.expires_at = time.time() + 3600
        runtime._next_auto_transfer = 0
        self.assertEqual(len(self.run_step(runtime, bound=bound)), 1)

    def test_a_paused_save_still_renews_the_session(self):
        runtime = self.setup()
        runtime.session._tokens.expires_at = time.time() + 10
        runtime.tokens = Mock()
        runtime._keep_session()
        runtime.session.principal.assert_called_once_with(min_validity=600)
        runtime.tokens.save.assert_called_once()
        runtime._keep_session()  # at most one attempt every 30 s
        runtime.session.principal.assert_called_once()
        runtime.session._tokens.expires_at = time.time() + 3600
        runtime._next_session_keep = 0
        runtime._keep_session()  # a valid token is left alone
        runtime.session.principal.assert_called_once()

    def test_a_launcher_without_transfer_writes_does_nothing(self):
        runtime = self.setup()
        runtime.writes.engine.allows.return_value = False
        self.assertEqual(self.run_step(runtime), [])


@unittest.skipUnless(os.name == "nt", "requires Windows filesystem")
class ProvenSideReleasesThePauseTests(unittest.TestCase):
    """Real disposable files and journal: once PokeApp proves a side, the
    pause ends, also after the trainer played on (2026-11-18 incident)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-proven-side-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.aid, self.tid, self.sid = (str(uuid4()) for _ in range(3))
        self.intent = WriteIntent.create(
            game="X",
            trainer_key=SAVE_TRAINER,
            expected_sha256=sha256(SOURCE).hexdigest(),
            mutation={"kind": "transfer_remove", "pair_id": self.aid},
        )
        self.repo = Repository(self.aid)
        self.bridge = self.restart()
        self.bridge.bind(self.aid, "source", self.intent)
        self.bridge.prepare(self.aid, closed_emulator_confirmed=True)
        self.bridge.apply(self.aid, closed_emulator_confirmed=True)
        self.output = self.target.read_bytes()
        self.assertNotEqual(SOURCE, self.output)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                p.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.tmp.cleanup()

    def restart(self):
        controller = LocalWriteController(
            SaveActivityGate(), lambda: str(self.target), engine_at(self.root)
        )
        return EngineeringTransfer(
            controller, self.repo, season_id=self.sid, trainer_id=self.tid
        )

    def prove(self, result):
        self.repo.state.update(
            status="COMPETITIVELY_ADJUDICATED",
            obligation="DONOR_VERIFIED",
            result_sha256=sha256(result).hexdigest(),
            verified=True,
            accepted_save_id=str(uuid4()),
        )

    def test_waiting_for_the_proof_keeps_the_pause_and_is_listed_as_applied(self):
        self.assertTrue(self.bridge.controller.gate.recovery_required)
        self.assertEqual(
            [{"authorization_id": self.aid, "applied": True}],
            self.bridge.controller.open_transfers(),
        )

    def test_a_proven_side_ends_the_pause_even_after_playing_on(self):
        self.target.write_bytes(b"PLAYED" + self.output[6:])  # saved again later
        self.prove(self.output)
        self.assertEqual("DONOR_VERIFIED", self.bridge.state(self.aid)["status"])
        self.assertFalse(self.bridge.controller.gate.recovery_required)
        self.assertEqual([], self.bridge.controller.open_transfers())
        # A restarted Launcher stays free: the settled binding is history.
        fresh = self.restart()
        self.assertFalse(fresh.controller.gate.recovery_required)
        self.assertIsNone(fresh.controller._transfer_notice())
        self.assertEqual(b"PLAYED", self.target.read_bytes()[:6])  # nothing rewritten

    def test_a_proof_of_another_result_keeps_the_pause(self):
        self.prove(b"another result")
        self.assertEqual("RECOVERY_REQUIRED", self.bridge.state(self.aid)["status"])
        self.assertTrue(self.bridge.controller.gate.recovery_required)
        self.assertTrue(self.restart().controller.gate.recovery_required)


if __name__ == "__main__":
    unittest.main()
