"""«Felicidad máxima»: the real native writer through the real journaled engine.

The Pokémon Y source is derived in memory from the retained public contributor
fixture (never a player's save) by the C# --friendship-checks gate, then copied
into a disposable folder. Writes only happen under the in-process engineering
capability scoped to that folder; production mode must refuse them.

Since 2026-11-12 the PC too: that source keeps a Pokémon in Box 1 slot 1
(friendship 50), an empty Box 1 slot 2, an egg in Box 2 slot 6 and a traded
Pokémon (handler friendship 33) in the last slot of the last box.
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

from app.launcher.friendship import describe, friendship_intent, party_view
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
LAST_BOX = 30  # Pokémon Y has 31 boxes


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

    def boxed(self, view, box, slot):
        return next((m for m in view["boxes"] if (m["box_index"], m["slot_index"]) == (box, slot)), None)

    def box_intent(self, box, slot, data=None):
        data = self.target.read_bytes() if data is None else data
        member = self.boxed(party_view(self.native, data), box, slot)
        return friendship_intent(self.native, data, slot, member["pokemon_sha256"], box_index=box)

    def apply(self, intent, engine=None):
        engine = engine or self.engine
        receipt = engine.prepare(engine.enroll(self.target), intent, closed_emulator_confirmed=True)
        self.assertEqual(receipt.status, "AWAITING_CONFIRMATION")
        self.assertEqual(self.target.read_bytes(), self.source)  # nothing written before confirmation
        result = engine.confirm(intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual(result.status, "APPLIED_VERIFIED", result.error)

    def test_party_view_shows_real_friendship_and_eggs_are_not_eligible(self):
        view = party_view(self.native, self.source)
        self.assertEqual(view["game"], "Y")
        self.assertEqual([m["friendship"] for m in view["party"]][::2], [70, 255])
        self.assertEqual([m["eligible"] for m in view["party"]], [True, True, True, False])
        self.assertEqual((view["party"][0]["species"], view["party"][0]["form"], view["party"][0]["nickname"]),
                         (711, 2, "Jalowin"))

    def test_every_box_is_listed_with_its_place_and_empty_slots_are_not(self):
        boxes = party_view(self.native, self.source)["boxes"]
        places = [(m["box_index"], m["slot_index"]) for m in boxes]
        self.assertEqual(places, sorted(set(places)))
        first, last, egg = self.boxed({"boxes": boxes}, 0, 0), self.boxed({"boxes": boxes}, LAST_BOX, 29), \
            self.boxed({"boxes": boxes}, 1, 5)
        self.assertEqual((first["species"], first["nickname"], first["friendship"], first["eligible"]),
                         (448, "Caja", 50, True))
        self.assertEqual((last["species"], last["nickname"], last["friendship"], last["eligible"]),
                         (149, "Lejos", 33, True))
        self.assertFalse(egg["eligible"])
        self.assertIsNone(self.boxed({"boxes": boxes}, 0, 1))

    def test_applies_255_with_verified_backup_readback_and_exact_restore(self):
        before = party_view(self.native, self.source)["party"]
        intent = self.intent()
        self.assertNotIn("box_index", intent.mutation)  # the party shape earlier journals used
        self.apply(intent)
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

    def test_a_boxed_pokemon_gets_255_where_it_is(self):
        view = party_view(self.native, self.source)
        intent = self.box_intent(0, 0)
        self.assertEqual((intent.mutation["location"], intent.mutation["box_index"], intent.mutation["slot_index"]),
                         ("box", 0, 0))
        self.assertIn("Caja 1, posición 1", describe(intent.mutation))
        self.apply(intent)
        after = party_view(self.native, self.target.read_bytes())
        changed = self.boxed(after, 0, 0)
        self.assertEqual(changed["friendship"], 255)
        before = self.boxed(view, 0, 0)
        self.assertEqual({k: changed[k] for k in ("species", "form", "nickname", "level")},
                         {k: before[k] for k in ("species", "form", "nickname", "level")})
        # Not moved: the party and every other box slot are identical.
        self.assertEqual(after["party"], view["party"])
        self.assertEqual([m for m in after["boxes"] if (m["box_index"], m["slot_index"]) != (0, 0)],
                         [m for m in view["boxes"] if (m["box_index"], m["slot_index"]) != (0, 0)])
        backup = self.root / "profile/write-backups" / (intent.operation_id + ".original")
        self.assertEqual(backup.read_bytes(), self.source)
        restored = self.engine.restore(intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual(restored.status, "RESTORED_VERIFIED", restored.error)
        self.assertEqual(self.target.read_bytes(), self.source)

    def test_the_last_slot_of_the_last_box_uses_its_handlers_friendship(self):
        self.apply(self.box_intent(LAST_BOX, 29))
        self.assertEqual(self.boxed(party_view(self.native, self.target.read_bytes()), LAST_BOX, 29)["friendship"], 255)

    def test_a_traded_pokemon_uses_its_handlers_friendship(self):
        self.apply(self.intent(slot=1))
        self.assertEqual(party_view(self.native, self.target.read_bytes())["party"][1]["friendship"], 255)

    def test_an_interrupted_write_is_recovered_from_the_journal(self):
        for intent in (self.intent(), self.box_intent(0, 0)):
            with self.subTest(location=intent.mutation["location"]):
                self.target.write_bytes(self.source)
                interrupted = self.engine_at(fault_hook=lambda at: (_ for _ in ()).throw(OSError("power cut"))
                                             if at == "after_publish" else None)
                interrupted.prepare(interrupted.enroll(self.target), intent, closed_emulator_confirmed=True)
                self.assertEqual(interrupted.confirm(intent.operation_id, closed_emulator_confirmed=True).status,
                                 "RECOVERY_REQUIRED")
                self.assertEqual(self.engine_at().reconcile(intent.operation_id).status, "APPLIED_VERIFIED")
                view = party_view(self.native, self.target.read_bytes())
                member = view["party"][0] if intent.mutation["location"] == "party" else self.boxed(view, 0, 0)
                self.assertEqual(member["friendship"], 255)

    def test_repeating_on_255_is_refused_before_any_journal_entry(self):
        self.apply(self.intent())
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

    def test_never_a_wrong_box_pokemon(self):
        view = party_view(self.native, self.source)
        cases = (
            (0, 1, self.boxed(view, 0, 0)["pokemon_sha256"], "FRIENDSHIP_NOT_ELIGIBLE"),  # empty slot
            (1, 5, self.boxed(view, 1, 5)["pokemon_sha256"], "FRIENDSHIP_NOT_ELIGIBLE"),  # egg
            # The Pokémon seen in Box 1 is not the one in the last box.
            (LAST_BOX, 29, self.boxed(view, 0, 0)["pokemon_sha256"], "STALE_MUTATION"),
            (0, 0, view["party"][0]["pokemon_sha256"], "STALE_MUTATION"),  # the party Pokémon's identity
            (32, 0, "0" * 64, "INVALID_WRITE_INTENT"),
            (0, 30, "0" * 64, "INVALID_WRITE_INTENT"),
        )
        for box, slot, digest, code in cases:
            with self.subTest(box=box, slot=slot), self.assertRaises(WriteSafetyError) as caught:
                friendship_intent(self.native, self.source, slot, digest, box_index=box)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.engine.pending(), ())

    def test_production_mode_enables_only_friendship_among_new_kinds(self):
        # Launcher 0.26.12: the production engine (no engineering capability)
        # applies «Felicidad máxima» with the same backup and readback; the
        # fixture-only kinds stay refused. 0.26.15: the same kind reaches the PC.
        production = self.engine_at(enabled=False)
        self.assertTrue(production.allows("max_friendship"))
        # Revive: owner decision 2026-11-09, only through its coordinated flow.
        self.assertFalse(production.allows("test_marking"))
        intent = self.intent()
        self.apply(intent, production)
        self.assertEqual(party_view(self.native, self.target.read_bytes())["party"][0]["friendship"], 255)
        backup = self.root / "profile/write-backups" / (intent.operation_id + ".original")
        self.assertEqual(backup.read_bytes(), self.source)

    def test_production_mode_applies_to_a_boxed_pokemon(self):
        production = self.engine_at(enabled=False)
        intent = self.box_intent(0, 0)
        self.apply(intent, production)
        self.assertEqual(self.boxed(party_view(self.native, self.target.read_bytes()), 0, 0)["friendship"], 255)


class FriendshipRuntimeTests(Harness):
    PARTY = {"game": "Y", "trainer_key": "b" * 64, "source_sha256": sha256(b"save").hexdigest(),
             "party": [dict(slot_index=0, species=711, form=2, nickname="Jalowin", level=31,
                            friendship=70, eligible=True, pokemon_sha256="c" * 64)],
             "boxes": [dict(box_index=4, slot_index=17, species=448, form=0, nickname="Caja", level=40,
                            friendship=50, eligible=True, pokemon_sha256="d" * 64)]}

    def runtime_with(self, *, enabled):
        runtime = self.runtime()
        engine = Mock()
        engine.native.inspect_friendship.return_value = self.PARTY
        engine.files.read_path.return_value = b"save"
        engine.allows.side_effect = lambda kind: enabled and kind == "max_friendship"
        runtime.writes.engine = engine
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        return runtime

    def test_party_and_boxes_are_shown_and_production_says_it_is_not_enabled_yet(self):
        runtime = self.runtime_with(enabled=False)
        runtime._friendship_step("friendship_refresh", {})
        state = runtime.state()
        self.assertEqual(state["friendship"]["party"][0]["friendship"], 70)
        self.assertEqual(state["friendship"]["boxes"][0]["box_index"], 4)
        self.assertFalse(state["friendship"]["application_enabled"])
        runtime._friendship_step("friendship_apply", {"location": "box", "box_index": 4, "slot_index": 17,
                                                      "pokemon_sha256": "d" * 64})
        state = runtime.state()
        self.assertEqual(state["friendship_error"], FRIENDSHIP_ERRORS["FRIENDSHIP_DISABLED"])
        self.assertIsNone(state["friendship_result"])
        self.assertEqual(state["friendship_seq"], 2)
        runtime.writes.engine.files.write_path.assert_not_called()

    def test_a_boxed_pokemon_is_re_read_in_its_box_after_the_write(self):
        runtime = self.runtime_with(enabled=True)
        raised = {**self.PARTY, "boxes": [{**self.PARTY["boxes"][0], "friendship": 255, "pokemon_sha256": "e" * 64}]}
        runtime.writes.engine.native.inspect_friendship.side_effect = [self.PARTY, raised]
        runtime.writes.offer = Mock()
        runtime.writes.state = Mock(return_value={"status": "AWAITING_CONFIRMATION", "operation_id": "op"})
        runtime.writes.confirm = Mock(return_value={"status": "APPLIED_VERIFIED"})
        runtime._load_local = Mock()
        runtime._friendship_step("friendship_apply", {"location": "box", "box_index": 4, "slot_index": 17,
                                                      "pokemon_sha256": "d" * 64})
        state = runtime.state()
        intent = runtime.writes.offer.call_args.args[0]
        self.assertEqual(intent.mutation, {"kind": "max_friendship", "location": "box", "box_index": 4,
                                           "slot_index": 17, "expected_pokemon_sha256": "d" * 64,
                                           "expected_friendship": 50})
        self.assertIsNone(state["friendship_error"])
        result = state["friendship_result"]
        self.assertEqual((result["location"], result["box_index"], result["slot_index"], result["friendship"],
                          result["readback_verified"]), ("box", 4, 17, 255, True))

    def test_commands_are_validated_before_queueing(self):
        runtime = self.runtime_with(enabled=True)
        h = "c" * 64
        for args in ({"location": "party", "box_index": None, "slot_index": 6, "pokemon_sha256": h},
                     {"location": "party", "box_index": 0, "slot_index": 0, "pokemon_sha256": h},
                     {"location": "box", "box_index": None, "slot_index": 0, "pokemon_sha256": h},
                     {"location": "box", "box_index": 32, "slot_index": 0, "pokemon_sha256": h},
                     {"location": "box", "box_index": 0, "slot_index": 30, "pokemon_sha256": h},
                     {"location": "pc", "box_index": 0, "slot_index": 0, "pokemon_sha256": h},
                     {"location": "party", "box_index": None, "slot_index": 0, "pokemon_sha256": "X" * 64},
                     {"slot_index": 0, "pokemon_sha256": h}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                runtime.command("friendship_apply", args)
        self.assertEqual(runtime.command("friendship_refresh", {})["status"], "QUEUED")
        fresh = self.runtime_with(enabled=True)  # one queued command at a time
        self.assertEqual(fresh.command("friendship_apply", {"location": "box", "box_index": 31, "slot_index": 29,
                                                            "pokemon_sha256": h})["status"], "QUEUED")


if __name__ == "__main__":
    unittest.main()
