from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.admin.actions import discard_active_season
from app.liga.permissions import LeaguePermissionError
from app.liga.snapshots import build_matchday_snapshot
from app.season import archive
from app.season.config import default_season_document, default_season_version, season_version_to_dict


def _league_snapshot():
    version = replace(
        default_season_version(players=["Anto", "Victor"], effective_round=1),
        id="v1",
        name="Temporada Test",
        points_by_position={1: 9, 2: 8},
        coins_by_position={1: 15, 2: 14},
        division_sizes=[1, 1],
    )
    snapshot = build_matchday_snapshot(
        round_no=1,
        division_snapshot={"A": ["Anto"], "B": ["Victor"]},
        rank_a=["Anto"],
        rank_b=["Victor"],
        season_version=version,
        penalties_by_user={"Anto": {"dead_count": 0}, "Victor": {"dead_count": 1}},
        closed_at=1000,
    )
    league_state = {
        "tramo": 2,
        "active": False,
        "divisions": {"A": ["Anto"], "B": ["Victor"]},
        "matches": {},
        "results": {"Anto": {"1": 1}, "Victor": {"1": 2}},
        "movements": {"1": {"up": ["Victor"], "down": ["Anto"]}},
        "round_snapshots": {"1": snapshot},
    }
    document = {
        "schema_version": 1,
        "active_version_id": "v1",
        "versions": [season_version_to_dict(version)],
    }
    return league_state, document


class SeasonArchiveTests(unittest.TestCase):
    def _settings_store(self, initial: dict[str, object] | None = None):
        store = {
            key: (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
            for key, value in (initial or {}).items()
        }

        def fake_get(key: str):
            return store.get(key)

        def fake_set(key: str, value: str, **_kwargs):
            store[key] = value

        return store, fake_get, fake_set

    def test_build_archive_freezes_config_standings_status_and_public_team(self) -> None:
        league_state, document = _league_snapshot()
        locks = {
            1: [
                {
                    "jornada": 1,
                    "user": "Anto",
                    "team": [
                        {
                            "species": "Milotic",
                            "nickname": "Pau",
                            "level": 55,
                            "item": "Restos",
                            "ability": "Competitive",
                            "nature": "Bold",
                            "ivs": {"hp": 31},
                            "moves": [{"name": "Recover"}, {"name": "Scald"}],
                            "types": ["Agua"],
                        }
                    ],
                }
            ]
        }

        built = archive.build_season_archive(
            label="Temporada Test",
            archived_at=2000,
            league_state=league_state,
            season_document=document,
            lifecycle={"state": "finished", "finished_at": 1500},
            cup_states={},
            locks_by_round=locks,
        )

        self.assertEqual(built["state"], "archived")
        self.assertEqual(built["season_config"]["active_version_id"], "v1")
        self.assertEqual(built["league"]["champion"], "Anto")
        self.assertEqual(built["league"]["runner_up"], "Victor")
        self.assertEqual(built["league"]["points_final"], {"Anto": 9.0, "Victor": 7.8})
        self.assertEqual(built["league"]["coins_awarded"], {"Anto": 15, "Victor": 14})
        self.assertEqual(built["trainer_statuses"]["Anto"]["status"], "active")
        team = built["champion_team"]["team"]
        self.assertEqual(team[0]["species"], "Milotic")
        self.assertEqual(team[0]["moves"], ["Recover", "Scald"])
        self.assertNotIn("ivs", team[0])
        self.assertNotIn("nature", team[0])
        self.assertNotIn("ability", team[0])

    def test_finish_and_archive_are_admin_only_and_idempotent(self) -> None:
        league_state, document = _league_snapshot()
        store, fake_get, fake_set = self._settings_store(
            {
                "league_state": league_state,
                "season_lifecycle_v1": {"state": "active"},
                "season_archives_v1": [],
            }
        )

        with (
            patch.object(archive, "settings_get", side_effect=fake_get),
            patch.object(archive, "settings_set", side_effect=fake_set),
            patch.object(archive, "load_season_document", return_value=document),
            patch.object(archive, "all_trainer_flags", return_value={}),
            patch.object(archive, "_collect_team_locks", return_value={}),
            patch("app.interfaz.hall_of_fame.sync_hall_of_fame_from_sources", return_value=[]),
        ):
            with self.assertRaises(LeaguePermissionError):
                archive.finish_active_season(admin_user="Victor", finished_at=1500)

            lifecycle = archive.finish_active_season(admin_user="Anto", finished_at=1500)
            self.assertEqual(lifecycle["state"], "finished")

            first = archive.archive_current_season(admin_user="Anto", archived_at=2000)
            second = archive.archive_current_season(admin_user="Anto", archived_at=3000)

            self.assertEqual(first["id"], second["id"])
            self.assertEqual(len(json.loads(store["season_archives_v1"])), 1)
            self.assertEqual(json.loads(store["season_lifecycle_v1"])["state"], "archived")

    def test_hall_prefers_archived_entry_over_live_auto_entry(self) -> None:
        from app.interfaz import hall_of_fame

        archived = {
            "id": "auto:liga:v1:1",
            "competition": "Liga",
            "title": "Temporada Test - Liga",
            "season": "Temporada Test",
            "champion": "Anto",
            "runner_up": "Victor",
            "team": ["Milotic"],
            "team_snapshot": [{"species": "Milotic", "moves": ["Recover"]}],
            "archive_id": "season:abc",
            "created_at": 2000,
        }
        live = dict(archived)
        live["team"] = ["Garchomp"]
        live["team_snapshot"] = [{"species": "Garchomp"}]

        with (
            patch.object(hall_of_fame, "settings_get", return_value="[]"),
            patch.object(hall_of_fame, "settings_set", return_value=None),
            patch.object(hall_of_fame, "_automatic_entries", return_value=[live]),
            patch.object(hall_of_fame, "_archive_entries", return_value=[archived]),
        ):
            entries = hall_of_fame.sync_hall_of_fame_from_sources()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["team"], ["Milotic"])
        self.assertEqual(entries[0]["team_snapshot"][0]["species"], "Milotic")
        self.assertEqual(entries[0]["archive_id"], "season:abc")

    def test_discard_default_path_does_not_create_archive_or_hall(self) -> None:
        with patch("app.season.archive.mark_season_discarded", return_value={"ok": True, "errors": []}) as marked:
            report = discard_active_season(
                admin_user="Anto",
                decision="discard",
                confirmation="DESCARTAR",
            )

        self.assertEqual(report, {"ok": True, "errors": []})
        marked.assert_called_once_with(admin_user="Anto")

    def test_prepare_new_active_season_preserves_archives(self) -> None:
        existing_archive = {"id": "season:old", "label": "Old", "archived_at": 100}
        store, fake_get, fake_set = self._settings_store(
            {
                "season_lifecycle_v1": {"state": "archived", "archive_id": "season:old"},
                "season_archives_v1": [existing_archive],
            }
        )
        st_fake = SimpleNamespace(session_state={"league_tramo": 9, "user": "Anto"})

        with (
            patch.object(archive, "settings_get", side_effect=fake_get),
            patch.object(archive, "settings_set", side_effect=fake_set),
            patch.object(archive, "st", st_fake),
            patch("storage.clear_active_competition_rows", return_value={"ok": True, "errors": []}),
        ):
            report = archive.prepare_new_active_season(admin_user="Anto")

        self.assertTrue(report["ok"])
        self.assertEqual(json.loads(store["season_lifecycle_v1"])["state"], "active")
        self.assertEqual(json.loads(store["season_archives_v1"]), [existing_archive])
        self.assertNotIn("league_tramo", st_fake.session_state)


if __name__ == "__main__":
    unittest.main()
