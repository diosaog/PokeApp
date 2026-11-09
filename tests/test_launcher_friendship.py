"""«Felicidad máxima»: the real native writer through the real journaled engine.

The Pokémon Y source is derived in memory from the retained public contributor
fixture (never a player's save) by the C# --friendship-checks gate, then copied
into a disposable folder. Writes only happen under the in-process engineering
capability scoped to that folder; production mode must refuse them.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from test_launcher_stability import Harness

from app.launcher.friendship import friendship_intent, party_view
from app.launcher.runtime import FRIENDSHIP_ERRORS
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.save_parser.writer import PkhexProcessWriter

REPO = Path(__file__).resolve().parents[1]
PARSER = REPO / "companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe"
CHECKS = REPO / "companion/parser/PokeApp.Parser.Checks/bin/Release/net8.0/PokeApp.Parser.Checks.dll"
PUBLIC = Path(os.environ.get("POKEAPP_PUBLIC_FIXTURES", Path(os.environ.get("LOCALAPPDATA", "")) /
                             "PokeApp-migration-evidence/phase22/20261020/native-writes"))
DOTNET = os.environ.get("POKEAPP_DOTNET8") or shutil.which("dotnet") or r"C:\Program Files\dotnet\dotnet.exe"


@unittest.skipUnless(os.name == "nt" and PARSER.exists() and CHECKS.exists() and (PUBLIC / "Y/prepared").exists(),
                     "build the parser and its checks (Release) and keep the public fixtures")
class FriendshipEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="pokeapp-friendship-fixture-")
        subprocess.run([DOTNET, str(CHECKS), "--friendship-checks", str(PUBLIC), cls.fixtures.name],
                       check=True, capture_output=True, timeout=600)
        cls.source = (Path(cls.fixtures.name) / "Y-source.sav").read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-friendship-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(self.source)
        self.native = PkhexProcessWriter(PARSER)
        self.engine = self.engine_at()

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.tmp.cleanup()

    def engine_at(self, *, enabled=True, fault_hook=None):
        return LocalWriteEngine(
            self.root / "profile", self.native, files=WindowsWriteFiles(process_names=list),
            engineering_capability=EngineeringCapability.for_fixture_root(self.root) if enabled else None,
            fault_hook=fault_hook,
        )

    def intent(self, slot=0, data=None):
        data = self.target.read_bytes() if data is None else data
        member = party_view(self.native, data)["party"][slot]
        return friendship_intent(self.native, data, slot, member["pokemon_sha256"])

    def test_party_view_shows_real_friendship_and_eggs_are_not_eligible(self):
        view = party_view(self.native, self.source)
        self.assertEqual(view["game"], "Y")
        self.assertEqual([m["friendship"] for m in view["party"]][::2], [70, 255])
        self.assertEqual([m["eligible"] for m in view["party"]], [True, True, True, False])
        self.assertEqual((view["party"][0]["species"], view["party"][0]["form"], view["party"][0]["nickname"]),
                         (711, 2, "Jalowin"))

    def test_applies_255_with_verified_backup_readback_and_exact_restore(self):
        before = party_view(self.native, self.source)["party"]
        intent = self.intent()
        receipt = self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual(receipt.status, "AWAITING_CONFIRMATION")
        self.assertEqual(self.target.read_bytes(), self.source)  # nothing written before confirmation
        result = self.engine.confirm(intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual(result.status, "APPLIED_VERIFIED", result.error)
        after = party_view(self.native, self.target.read_bytes())["party"]
        self.assertEqual(after[0]["friendship"], 255)
        self.assertEqual({k: after[0][k] for k in ("species", "form", "nickname", "level")},
                         {k: before[0][k] for k in ("species", "form", "nickname", "level")})
        self.assertEqual(after[1:], before[1:])  # every other party member byte-identical
        backup = self.root / "profile/write-backups" / (intent.operation_id + ".original")
        self.assertEqual(backup.read_bytes(), self.source)
        restored = self.engine.restore(intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual(restored.status, "RESTORED_VERIFIED", restored.error)
        self.assertEqual(self.target.read_bytes(), self.source)

    def test_a_traded_pokemon_uses_its_handlers_friendship(self):
        intent = self.intent(slot=1)
        self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual(self.engine.confirm(intent.operation_id, closed_emulator_confirmed=True).status,
                         "APPLIED_VERIFIED")
        self.assertEqual(party_view(self.native, self.target.read_bytes())["party"][1]["friendship"], 255)

    def test_an_interrupted_write_is_recovered_from_the_journal(self):
        intent = self.intent()
        interrupted = self.engine_at(fault_hook=lambda at: (_ for _ in ()).throw(OSError("power cut"))
                                     if at == "after_publish" else None)
        interrupted.prepare(interrupted.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual(interrupted.confirm(intent.operation_id, closed_emulator_confirmed=True).status,
                         "RECOVERY_REQUIRED")
        self.assertEqual(self.engine_at().reconcile(intent.operation_id).status, "APPLIED_VERIFIED")
        self.assertEqual(party_view(self.native, self.target.read_bytes())["party"][0]["friendship"], 255)

    def test_repeating_on_255_is_refused_before_any_journal_entry(self):
        intent = self.intent()
        self.engine.prepare(self.engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.engine.confirm(intent.operation_id, closed_emulator_confirmed=True)
        written = self.target.read_bytes()
        with self.assertRaises(WriteSafetyError) as caught:
            self.intent()
        self.assertEqual(caught.exception.code, "FRIENDSHIP_ALREADY_MAX")
        self.assertEqual((self.target.read_bytes(), self.engine.pending()), (written, ()))

    def test_a_party_that_changed_since_it_was_shown_is_refused(self):
        with self.assertRaises(WriteSafetyError) as caught:
            friendship_intent(self.native, self.source, 0, "0" * 64)
        self.assertEqual(caught.exception.code, "STALE_MUTATION")
        with self.assertRaises(WriteSafetyError) as caught:
            self.intent(slot=3)
        self.assertEqual(caught.exception.code, "FRIENDSHIP_NOT_ELIGIBLE")

    def test_production_mode_enables_only_friendship_among_new_kinds(self):
        # Launcher 0.26.12: the production engine (no engineering capability)
        # applies «Felicidad máxima» with the same backup and readback; the
        # fixture-only kinds stay refused.
        production = self.engine_at(enabled=False)
        self.assertTrue(production.allows("max_friendship"))
        # Revive: owner decision 2026-11-09, only through its coordinated flow.
        self.assertFalse(production.allows("test_marking"))
        intent = self.intent()
        production.prepare(production.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual(production.confirm(intent.operation_id, closed_emulator_confirmed=True).status,
                         "APPLIED_VERIFIED")
        self.assertEqual(party_view(self.native, self.target.read_bytes())["party"][0]["friendship"], 255)
        backup = self.root / "profile/write-backups" / (intent.operation_id + ".original")
        self.assertEqual(backup.read_bytes(), self.source)


class FriendshipRuntimeTests(Harness):
    PARTY = {"game": "Y", "trainer_key": "b" * 64, "source_sha256": sha256(b"save").hexdigest(),
             "party": [dict(slot_index=0, species=711, form=2, nickname="Jalowin", level=31,
                            friendship=70, eligible=True, pokemon_sha256="c" * 64)]}

    def runtime_with(self, *, enabled):
        runtime = self.runtime()
        engine = Mock()
        engine.native.inspect_friendship.return_value = self.PARTY
        engine.files.read_path.return_value = b"save"
        engine.allows.side_effect = lambda kind: enabled and kind == "max_friendship"
        runtime.writes.engine = engine
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        return runtime

    def test_the_party_is_shown_and_production_says_it_is_not_enabled_yet(self):
        runtime = self.runtime_with(enabled=False)
        runtime._friendship_step("friendship_refresh", {})
        state = runtime.state()
        self.assertEqual(state["friendship"]["party"][0]["friendship"], 70)
        self.assertFalse(state["friendship"]["application_enabled"])
        runtime._friendship_step("friendship_apply", {"slot_index": 0, "pokemon_sha256": "c" * 64})
        state = runtime.state()
        self.assertEqual(state["friendship_error"], FRIENDSHIP_ERRORS["FRIENDSHIP_DISABLED"])
        self.assertIsNone(state["friendship_result"])
        self.assertEqual(state["friendship_seq"], 2)
        runtime.writes.engine.files.write_path.assert_not_called()

    def test_commands_are_validated_before_queueing(self):
        runtime = self.runtime_with(enabled=True)
        for args in ({"slot_index": 6, "pokemon_sha256": "c" * 64}, {"slot_index": 0, "pokemon_sha256": "X" * 64},
                     {"slot_index": 0}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                runtime.command("friendship_apply", args)
        self.assertEqual(runtime.command("friendship_refresh", {})["status"], "QUEUED")


if __name__ == "__main__":
    unittest.main()
