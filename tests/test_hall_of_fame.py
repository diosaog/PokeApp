from __future__ import annotations

import unittest

from app.interfaz.hall_of_fame import (
    _auto_entry,
    _clean_team,
    _coerce_entry,
    _merge_entries,
    _valid_bo3,
)


class HallOfFameTests(unittest.TestCase):
    def test_clean_team_accepts_text_and_limits_to_six(self) -> None:
        raw = "Garchomp\nRotom-Wash, Scizor; Latios\nHeatran\nAmoonguss\nTyranitar\nMew"

        self.assertEqual(
            _clean_team(raw),
            [
                "Garchomp",
                "Rotom-Wash",
                "Scizor",
                "Latios",
                "Heatran",
                "Amoonguss",
            ],
        )

    def test_coerce_entry_requires_champion_and_defaults_metadata(self) -> None:
        self.assertIsNone(_coerce_entry({"title": "Sin campeon"}))

        entry = _coerce_entry({"champion": "Anto", "team": ["Milotic"]})

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["competition"], "Liga")
        self.assertEqual(entry["title"], "Temporada archivada")
        self.assertEqual(entry["team"], ["Milotic"])

    def test_coerce_entry_tolerates_legacy_text_id(self) -> None:
        entry = _coerce_entry({"id": "old-entry", "champion": "Victor"})

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertGreater(entry["created_at"], 0)

    def test_merge_entries_upserts_automatic_entries_by_id(self) -> None:
        saved = [
            {
                "id": "auto:liga:default:4",
                "competition": "Liga",
                "title": "Liga antigua",
                "season": "Temporada",
                "champion": "Miguel",
                "runner_up": "",
                "team": ["Dragonite"],
                "notes": "",
                "created_at": 123,
            }
        ]
        auto = _auto_entry(
            source_id="liga:default:4",
            competition="Liga",
            title="Liga nueva",
            season="Temporada",
            champion="Anto",
            team=["Milotic"],
            notes="Final corregida.",
        )

        merged = _merge_entries(saved, [auto] if auto else [])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["champion"], "Anto")
        self.assertEqual(merged[0]["team"], ["Milotic"])
        self.assertEqual(merged[0]["created_at"], 123)

    def test_valid_bo3_accepts_only_finished_series(self) -> None:
        self.assertTrue(_valid_bo3(2, 0))
        self.assertTrue(_valid_bo3("1", "2"))
        self.assertFalse(_valid_bo3(None, None))
        self.assertFalse(_valid_bo3(1, 1))


if __name__ == "__main__":
    unittest.main()
