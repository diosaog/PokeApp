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
    @patch.object(notifications, "recent_activity_events", return_value=[])
    def test_collect_notifications_limits_recent_activity_to_five(
        self,
        _mock_events,
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
        self.assertEqual(items[0]["body"], "Sergio ha subido ROM SERGIO.sav.")
        self.assertTrue(any(item["title"] == "Compra" for item in items))
        self.assertTrue(any(item["body"] == "Samu ha comprado Restos." for item in items))
        self.assertFalse(any("por" in item["body"] for item in items))
        self.assertFalse(any("Robar Pokemon" in item["body"] for item in items))

    @patch.object(notifications, "recent_activity_events", return_value=[])
    @patch.object(notifications, "list_saves", return_value=[])
    @patch.object(notifications, "list_purchases", return_value=[])
    @patch.object(notifications, "list_team_locks", return_value=[])
    def test_collect_notifications_empty_state(self, *_mocks) -> None:
        items = notifications.collect_notifications(jornada=3, limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Sin actividad reciente")
        self.assertEqual(notification_count(items), 0)

    @patch.object(notifications, "recent_activity_events")
    def test_collect_notifications_prefers_activity_events(self, mock_events) -> None:
        mock_events.return_value = [
            {
                "id": "evt-save",
                "type": "SAVE_UPLOADED",
                "created_at": 300,
                "actor": "Anto",
                "trainer": "Anto",
                "payload": {"original_name": "ROM ANTO.sav"},
                "context": {},
            },
            {
                "id": "evt-purchase",
                "type": "PURCHASE_COMPLETED",
                "created_at": 200,
                "actor": "Samu",
                "trainer": "Samu",
                "payload": {"item": "Restos", "price": 8},
                "context": {"jornada": 3},
            },
            {
                "id": "evt-lock",
                "type": "TEAM_LOCKED",
                "created_at": 100,
                "actor": "Victor",
                "trainer": "Victor",
                "payload": {"is_late": True},
                "context": {"jornada": 3},
            },
        ]

        items = notifications.collect_notifications(user="Anto", jornada=3, limit=5)

        self.assertEqual([item["title"] for item in items], ["Save subido", "Compra", "Equipo fijado"])
        self.assertEqual(items[0]["body"], "Anto ha subido ROM ANTO.sav.")
        self.assertEqual(items[1]["body"], "Samu ha comprado Restos.")
        self.assertEqual(items[2]["body"], "Victor ha fijado equipo tarde para J3.")


if __name__ == "__main__":
    unittest.main()
