from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from app.admin.actions import discard_active_season
from app.entrenadores import trainer_flags
from app.liga.permissions import LeaguePermissionError
from app.liga.snapshots import build_matchday_snapshot
from app.season.config import default_season_version


class TrainerStatusTests(unittest.TestCase):
    def _settings_store(self, initial: dict | None = None):
        store = {"trainer_flags": json.dumps(initial or {})}

        def fake_get(key: str):
            return store.get(key)

        def fake_set(key: str, value: str):
            store[key] = value

        return store, fake_get, fake_set

    def test_active_to_retired_requires_admin_and_preserves_reason(self) -> None:
        store, fake_get, fake_set = self._settings_store()

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            trainer_flags.set_trainer_retired("Victor", by_user="Anto")
            saved = json.loads(store["trainer_flags"])

            self.assertEqual(saved["Victor"]["status"], "retired")
            self.assertEqual(saved["Victor"]["inactive_reason"], "retired")
            self.assertTrue(saved["Victor"]["retired"])
            self.assertEqual(trainer_flags.trainer_status("Victor"), "retired")
            self.assertEqual(trainer_flags.status_labels_for("Victor"), ["Retirado"])

    def test_active_to_abandoned_is_historically_distinct(self) -> None:
        store, fake_get, fake_set = self._settings_store()

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            trainer_flags.set_trainer_abandoned("Sergio", by_user="Anto")
            saved = json.loads(store["trainer_flags"])

            self.assertEqual(saved["Sergio"]["status"], "abandoned")
            self.assertTrue(saved["Sergio"]["abandoned"])
            self.assertTrue(trainer_flags.is_trainer_retired("Sergio"))
            self.assertEqual(trainer_flags.status_labels_for("Sergio"), ["Abandono"])

    def test_disqualified_is_admin_status_without_reactivation(self) -> None:
        store, fake_get, fake_set = self._settings_store()

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            trainer_flags.set_trainer_disqualified("Rober", by_user="Anto")
            self.assertEqual(trainer_flags.trainer_status("Rober"), "disqualified")
            with self.assertRaises(ValueError):
                trainer_flags.set_trainer_status("Rober", "active", by_user="Anto")

    def test_non_admin_cannot_mutate_trainer_status(self) -> None:
        store, fake_get, fake_set = self._settings_store()

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            with self.assertRaises(LeaguePermissionError):
                trainer_flags.set_trainer_abandoned("Victor", by_user="Samu")

    def test_robbed_remains_a_flag_and_is_cleared_when_inactive(self) -> None:
        initial = {"Aaron": {"robbed": True, "robbed_by": "Sergio"}}
        store, fake_get, fake_set = self._settings_store(initial)

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            self.assertEqual(trainer_flags.trainer_status("Aaron"), "active")
            self.assertTrue(trainer_flags.is_trainer_robbed("Aaron"))
            self.assertEqual(trainer_flags.status_labels_for("Aaron"), ["Robado"])

            trainer_flags.set_trainer_abandoned("Aaron", by_user="Anto")
            self.assertFalse(trainer_flags.is_trainer_robbed("Aaron"))
            self.assertEqual(trainer_flags.status_labels_for("Aaron"), ["Abandono"])

    def test_inactive_trainer_cannot_be_marked_robbed(self) -> None:
        initial = {"Aaron": {"status": "abandoned", "abandoned": True, "retired": True}}
        store, fake_get, fake_set = self._settings_store(initial)

        with (
            patch.object(trainer_flags, "settings_get", side_effect=fake_get),
            patch.object(trainer_flags, "settings_set", side_effect=fake_set),
        ):
            result = trainer_flags.mark_trainer_robbed("Aaron", by_user="Sergio")

        self.assertEqual(
            result,
            {"marked": False, "already_robbed": False, "cycle_reset": False},
        )

    def test_closed_snapshot_keeps_trainer_status_metadata(self) -> None:
        snapshot = build_matchday_snapshot(
            round_no=1,
            division_snapshot={"A": ["Anto"], "B": ["Victor"]},
            rank_a=["Anto"],
            rank_b=["Victor"],
            season_version=default_season_version(players=["Anto", "Victor"]),
            penalties_by_user={
                "Victor": {
                    "trainer_status": "abandoned",
                    "trainer_status_labels": ["Abandono"],
                }
            },
            closed_at=1000,
        )

        penalties = snapshot["penalties"]["Victor"]
        self.assertEqual(penalties["trainer_status"], "abandoned")
        self.assertEqual(penalties["trainer_status_labels"], ["Abandono"])


class AdminActionTests(unittest.TestCase):
    def test_discard_requires_admin_user(self) -> None:
        with self.assertRaises(LeaguePermissionError):
            discard_active_season(
                admin_user="Victor",
                decision="discard",
                confirmation="DESCARTAR",
                wipe_fn=Mock(return_value={"ok": True}),
            )

    def test_discard_requires_explicit_decision(self) -> None:
        with self.assertRaises(ValueError):
            discard_active_season(
                admin_user="Anto",
                decision="archive",
                confirmation="DESCARTAR",
                wipe_fn=Mock(return_value={"ok": True}),
            )

    def test_discard_requires_text_confirmation(self) -> None:
        wipe = Mock(return_value={"ok": True})

        with self.assertRaises(ValueError):
            discard_active_season(
                admin_user="Anto",
                decision="discard",
                confirmation="WIPE",
                wipe_fn=wipe,
            )

        wipe.assert_not_called()

    def test_discard_runs_injected_wipe_only_when_confirmed(self) -> None:
        wipe = Mock(return_value={"ok": True, "errors": []})

        report = discard_active_season(
            admin_user="Anto",
            decision="discard",
            confirmation="DESCARTAR",
            wipe_fn=wipe,
        )

        self.assertEqual(report, {"ok": True, "errors": []})
        wipe.assert_called_once_with()

    def test_entrenadores_page_no_longer_contains_official_retirement_admin(self) -> None:
        source = Path("app/entrenadores/page.py").read_text(encoding="utf-8")

        self.assertNotIn("_render_retirement_admin", source)
        self.assertNotIn("Marcar abandono", source)

    def test_shop_page_no_longer_renders_global_flags_reset(self) -> None:
        source = Path("app/tienda/ui.py").read_text(encoding="utf-8")

        self.assertNotIn("render_flags_reset", source)


if __name__ == "__main__":
    unittest.main()
