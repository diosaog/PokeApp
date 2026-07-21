from __future__ import annotations

import unittest
from unittest.mock import patch

from app.interfaz import notifications
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
                "time": "21/07/2026 20:00",
            }
        )

        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Equipo &lt;pendiente&gt;", html)
        self.assertIn("21/07/2026 20:00", html)
        self.assertNotIn("<script>", html)

    @patch.object(notifications, "list_saves")
    @patch.object(notifications, "list_purchases")
    @patch.object(notifications, "list_team_locks")
    def test_collect_notifications_limits_recent_activity_to_five(
        self,
        mock_locks,
        mock_purchases,
        mock_saves,
    ) -> None:
        mock_locks.return_value = [
            {"user": "Anto", "team": [{"species": "Milotic"}] * 6, "locked_at": 50},
            {"user": "Victor", "team": [{"species": "Gallade"}] * 6, "locked_at": 90},
        ]
        mock_purchases.return_value = [
            (1, "Samu", "Restos", 8, 100, "pending", None),
            (2, "Iker", "Robar Pokemon", 0, 110, "pending", None),
        ]
        mock_saves.return_value = [
            (3, "save3.sav", "ROM SERGIO.sav", "sha", "Sergio", 120),
            (4, "save4.sav", "ROM ROBER.sav", "sha", "Rober", 80),
            (5, "save5.sav", "ROM MIGUEL.sav", "sha", "Miguel", 70),
            (6, "save6.sav", "ROM DAVIRY.sav", "sha", "Daviry", 60),
        ]

        items = notifications.collect_notifications(jornada=3, limit=5)

        self.assertEqual(len(items), 5)
        self.assertEqual(items[0]["title"], "Save subido")
        self.assertIn("Sergio", items[0]["body"])
        self.assertTrue(any(item["title"] == "Compra" for item in items))
        self.assertFalse(any("Robar Pokemon" in item["body"] for item in items))

    @patch.object(notifications, "list_saves", return_value=[])
    @patch.object(notifications, "list_purchases", return_value=[])
    @patch.object(notifications, "list_team_locks", return_value=[])
    def test_collect_notifications_empty_state(self, *_mocks) -> None:
        items = notifications.collect_notifications(jornada=3, limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Sin actividad reciente")
        self.assertEqual(notification_count(items), 0)


if __name__ == "__main__":
    unittest.main()
