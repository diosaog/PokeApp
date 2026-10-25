"""25A Launcher seams without native or network; the native matrix is separate."""

import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from app.launcher.discovery import EmulatorProvider, emulator_saves
from app.launcher.quick_items import describe, quick_item_intent
from app.launcher.write_files import WriteSafetyError

DATA = b"\x01" * 415232
HASH = sha256(DATA).hexdigest()


class Native:
    def __init__(self, count=5, addable=994, source=HASH):
        self.count, self.addable, self.source = count, addable, source

    def inventory(self, data):
        return {
            "game": "X",
            "trainer_key": "b" * 64,
            "source_sha256": self.source,
            "items": {
                "rare_candy": {
                    "count": self.count,
                    "max": 999,
                    "addable": self.addable,
                },
                "heart_scale": {"count": 0, "max": 999, "addable": 999},
            },
        }


class QuickItemTests(unittest.TestCase):
    def test_intent_binds_snapshot_hash_count_and_quantity(self):
        intent = quick_item_intent(Native(), DATA, "rare_candy", 3)
        self.assertEqual(intent.expected_sha256, HASH)
        self.assertEqual(
            intent.mutation,
            {
                "kind": "add_item",
                "item": "rare_candy",
                "quantity": 3,
                "expected_count": 5,
            },
        )
        # Deterministic operation id: a lost reply re-offers the SAME operation.
        self.assertEqual(
            intent.operation_id,
            quick_item_intent(Native(), DATA, "rare_candy", 3).operation_id,
        )

    def test_limits_full_stale_and_unapproved_items(self):
        for item, quantity, native, code in (
            ("rare_candy", 995, Native(), "INVENTORY_LIMIT"),
            ("rare_candy", 1, Native(addable=0), "INVENTORY_FULL"),
            ("rare_candy", 1, Native(source="c" * 64), "STALE_SOURCE"),
            ("master_ball", 1, Native(), "INVALID_QUICK_ITEM"),
            ("rare_candy", 0, Native(), "INVALID_QUICK_ITEM"),
            ("rare_candy", True, Native(), "INVALID_QUICK_ITEM"),
        ):
            with self.assertRaises(WriteSafetyError) as error:
                quick_item_intent(native, DATA, item, quantity)
            self.assertEqual(str(error.exception), code)

    def test_confirmation_text_only_for_exact_shape(self):
        text = describe(
            {
                "kind": "add_item",
                "item": "heart_scale",
                "quantity": 2,
                "expected_count": 7,
            }
        )
        self.assertIn("Añadir 2 × Escama Corazón", text)
        for bad in (
            {
                "kind": "add_item",
                "item": "heart_scale",
                "quantity": 0,
                "expected_count": 7,
            },
            {"kind": "add_item", "item": "heart_scale", "quantity": 2},
            {"kind": "add_item", "item": "nugget", "quantity": 2, "expected_count": 0},
        ):
            with self.assertRaises(WriteSafetyError):
                describe(bad)


class DiscoveryTests(unittest.TestCase):
    def test_lime3ds_azahar_citra_bounded_title_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ids = "0" * 32
            expected = []
            for emulator, title in (
                ("Lime3DS", "00055e00"),
                ("Azahar", "00175e00"),
                ("Citra", "001b5100"),
            ):
                save = (
                    root
                    / emulator
                    / "sdmc"
                    / "Nintendo 3DS"
                    / ids
                    / ids
                    / "title"
                    / "00040000"
                    / title
                    / "data"
                    / "00000001"
                    / "main"
                )
                save.parent.mkdir(parents=True)
                save.write_bytes(b"save")
                expected.append(save)
            unknown = (
                root
                / "Lime3DS"
                / "sdmc"
                / "Nintendo 3DS"
                / ids
                / ids
                / "title"
                / "00040000"
                / "deadbeef"
                / "data"
                / "00000001"
                / "main"
            )
            unknown.parent.mkdir(parents=True)
            unknown.write_bytes(b"other")
            found = emulator_saves(root)
            self.assertEqual(
                sorted((s["emulator"], s["game"]) for s in found),
                [("Azahar", "MN"), ("Citra", "UM"), ("Lime3DS", "Y")],
            )
            self.assertEqual(len(EmulatorProvider(root).candidates()), 3)
            self.assertEqual(emulator_saves(root / "missing"), [])


class RuntimeCommandTests(unittest.TestCase):
    def runtime(self):
        from app.launcher.runtime import LauncherRuntime

        temp = tempfile.TemporaryDirectory(prefix="pokeapp-25a-")
        self.addCleanup(temp.cleanup)
        return LauncherRuntime(
            Path(temp.name),
            Mock(),
            client=Mock(origin="https://x.invalid"),
            token_store=Mock(),
            start=False,
        )

    def test_quick_item_arguments_are_strict(self):
        runtime = self.runtime()
        for args in (
            {"item": "rare_candy", "quantity": 1},
            {"item": "rare_candy", "quantity": 0, "closed_emulator_confirmed": True},
            {"item": "rare_candy", "quantity": 1.0, "closed_emulator_confirmed": True},
            {
                "item": "rare_candy",
                "quantity": 10000,
                "closed_emulator_confirmed": True,
            },
            {"item": "nugget", "quantity": 1, "closed_emulator_confirmed": True},
        ):
            with self.assertRaises(ValueError):
                runtime.command("quick_item_offer", args)
        with self.assertRaises(ValueError):
            runtime.command("quick_items_refresh", {"x": 1})

    def test_production_build_without_save_never_writes(self):
        runtime = self.runtime()
        runtime.command(
            "quick_item_offer",
            {"item": "rare_candy", "quantity": 1, "closed_emulator_confirmed": True},
        )
        runtime._write_step()
        self.assertEqual(
            runtime.state()["quick_item_error"], "Selecciona tu partida primero."
        )
        self.assertFalse(runtime.save_activity.recovery_required)

    def test_discovered_selection_accepts_only_listed_paths(self):
        runtime = self.runtime()
        with self.assertRaises(ValueError):
            runtime.command("select_discovered", {"path": "C:/elsewhere/main"})
        runtime.value["emulator_saves"] = [
            {"path": "C:/fixture/main", "emulator": "Lime3DS", "game": "Y"}
        ]
        self.assertEqual(
            runtime.command("select_discovered", {"path": "C:/fixture/main"}),
            {"status": "QUEUED"},
        )
        self.assertEqual(
            runtime.local_commands.get_nowait(), ("select", {"path": "C:/fixture/main"})
        )


if __name__ == "__main__":
    unittest.main()
