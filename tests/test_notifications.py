from __future__ import annotations

import unittest

from app.interfaz.notifications import notification_count, notice_html


class NotificationTests(unittest.TestCase):
    def test_notification_count_ignores_ok_items(self) -> None:
        items = [
            {"kind": "ok", "title": "Todo bien", "body": ""},
            {"kind": "info", "title": "Rebajas", "body": ""},
            {"kind": "danger", "title": "Save", "body": ""},
        ]

        self.assertEqual(notification_count(items), 2)

    def test_notice_html_escapes_user_content(self) -> None:
        html = notice_html(
            {
                "kind": "danger",
                "title": "<script>",
                "body": "Equipo <pendiente>",
            }
        )

        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Equipo &lt;pendiente&gt;", html)
        self.assertNotIn("<script>", html)


if __name__ == "__main__":
    unittest.main()
