from __future__ import annotations

import unittest

from app.interfaz.hall_of_fame import _clean_team, _coerce_entry


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


if __name__ == "__main__":
    unittest.main()
