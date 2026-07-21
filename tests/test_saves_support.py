from __future__ import annotations

import unittest

from app.saves_support import current_save_meta_html, save_card_html, saves_summary_html


class SavesSupportTests(unittest.TestCase):
    def test_save_card_escapes_file_content_and_marks_current(self) -> None:
        row = (12, "stored.sav", "ROM <Anto>.sav", "abcdef123456", "Anto", 0)

        html = save_card_html(row, current_id=12)

        self.assertIn("saves-history-card is-current", html)
        self.assertIn("ROM &lt;Anto&gt;.sav", html)
        self.assertNotIn("ROM <Anto>.sav", html)
        self.assertIn("abcdef12", html)

    def test_current_save_meta_uses_compact_fields(self) -> None:
        row = (7, "remote.sav", "", "0011223344", "Victor", 0)

        html = current_save_meta_html(row)

        self.assertIn("remote.sav", html)
        self.assertIn("Victor", html)
        self.assertIn("00112233", html)
        self.assertIn("Actual", html)

    def test_summary_reflects_retired_mode_without_save(self) -> None:
        html = saves_summary_html("Sergio", None, [], retired=True)

        self.assertIn("Sergio", html)
        self.assertIn("Solo consulta", html)
        self.assertIn("Sin save", html)


if __name__ == "__main__":
    unittest.main()
