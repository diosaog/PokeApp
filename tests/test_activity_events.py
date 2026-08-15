from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from app.activity import events


class ActivityEventTests(unittest.TestCase):
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

    def test_save_uploaded_is_deduped_by_trainer_and_hash(self) -> None:
        store, fake_get, fake_set = self._settings_store()
        with (
            patch.object(events, "settings_get", side_effect=fake_get),
            patch.object(events, "settings_set", side_effect=fake_set),
        ):
            first = events.emit_save_uploaded(
                trainer="Anto",
                save_id=1,
                filename="a.sav",
                original_name="ROM.sav",
                sha256="abc",
                created_at=100,
            )
            second = events.emit_save_uploaded(
                trainer="Anto",
                save_id=2,
                filename="b.sav",
                original_name="ROM retry.sav",
                sha256="abc",
                created_at=200,
            )

        saved = json.loads(store[events.ACTIVITY_EVENTS_KEY])
        self.assertEqual(len(saved), 1)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(saved[0]["payload"]["save_id"], 1)

    def test_purchase_payload_and_recent_ordering(self) -> None:
        store, fake_get, fake_set = self._settings_store()
        with (
            patch.object(events, "settings_get", side_effect=fake_get),
            patch.object(events, "settings_set", side_effect=fake_set),
        ):
            events.emit_purchase_completed(
                trainer="Samu",
                item="Restos",
                price=8,
                purchase_id=10,
                created_at=100,
                jornada=3,
            )
            events.emit_team_locked(
                trainer="Anto",
                jornada=3,
                lock_id=20,
                locked_at=200,
            )
            recent = events.recent_activity_events(limit=5, viewer="Victor", ui_only=True)

        self.assertEqual([event["type"] for event in recent], [events.EVENT_TEAM_LOCKED, events.EVENT_PURCHASE_COMPLETED])
        purchase = recent[1]
        self.assertEqual(purchase["payload"]["item"], "Restos")
        self.assertEqual(purchase["payload"]["price"], 8)
        self.assertEqual(purchase["payload"]["purchase_id"], 10)
        self.assertEqual(purchase["context"]["jornada"], 3)

    def test_team_lock_is_deduped_per_trainer_and_round(self) -> None:
        store, fake_get, fake_set = self._settings_store()
        with (
            patch.object(events, "settings_get", side_effect=fake_get),
            patch.object(events, "settings_set", side_effect=fake_set),
        ):
            events.emit_team_locked(trainer="Anto", jornada=4, lock_id=1, locked_at=100)
            events.emit_team_locked(trainer="Anto", jornada=4, lock_id=2, locked_at=200)

        saved = json.loads(store[events.ACTIVITY_EVENTS_KEY])
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["payload"]["lock_id"], 1)

    def test_visibility_filters_admin_and_trainer_only_events(self) -> None:
        store, fake_get, fake_set = self._settings_store()
        with (
            patch.object(events, "settings_get", side_effect=fake_get),
            patch.object(events, "settings_set", side_effect=fake_set),
        ):
            events.record_activity_event(
                "TRAINER_STATUS_CHANGED",
                trainer="Victor",
                actor="Anto",
                visibility=events.VISIBILITY_ADMIN,
                dedupe_key="admin:1",
                created_at=100,
            )
            events.record_activity_event(
                "PRIVATE_SAVE_CHECK",
                trainer="Victor",
                actor="Victor",
                visibility=events.VISIBILITY_TRAINER,
                dedupe_key="trainer:1",
                created_at=200,
            )
            self.assertEqual(len(events.list_activity_events(viewer="Samu")), 0)
            self.assertEqual(len(events.list_activity_events(viewer="Anto")), 1)
            self.assertEqual(len(events.list_activity_events(viewer="Victor")), 1)


class ActivityStorageHookTests(unittest.TestCase):
    def _conn_context(self, conn: sqlite3.Connection):
        @contextmanager
        def _ctx():
            yield conn

        return _ctx

    def test_save_upload_emits_event_after_successful_persist(self) -> None:
        import storage

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                original_name TEXT,
                sha256 TEXT,
                uploader TEXT,
                created_at INTEGER
            )
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            emit = Mock()
            with (
                patch.object(storage, "_supabase_enabled", return_value=False),
                patch.object(storage, "_conn", self._conn_context(conn)),
                patch.object(storage, "SAVES_DIR", Path(tmp)),
                patch("app.activity.events.emit_save_uploaded", emit),
                patch.object(storage.time, "time", return_value=1000),
            ):
                rec = storage.save_upload(b"abc", "ROM ANTO.sav", "Anto")

        self.assertEqual(rec["id"], 1)
        emit.assert_called_once()
        self.assertEqual(emit.call_args.kwargs["trainer"], "Anto")
        self.assertEqual(emit.call_args.kwargs["save_id"], 1)
        conn.close()

    def test_add_purchase_emits_event_after_insert(self) -> None:
        from app import storage_shop

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                item TEXT,
                price INTEGER,
                created_at INTEGER,
                status TEXT,
                redeemed_at INTEGER,
                discount_id INTEGER,
                base_price INTEGER,
                jornada INTEGER
            )
            """
        )
        emit = Mock()
        with (
            patch.object(storage_shop, "_supabase_enabled", return_value=False),
            patch.object(storage_shop, "_conn", self._conn_context(conn)),
            patch("app.activity.events.emit_purchase_completed", emit),
            patch.object(storage_shop.time, "time", return_value=1100),
        ):
            purchase_id = storage_shop.add_purchase(
                "Samu",
                "Restos",
                8,
                jornada=3,
                notify=False,
            )

        self.assertEqual(purchase_id, 1)
        emit.assert_called_once()
        self.assertEqual(emit.call_args.kwargs["trainer"], "Samu")
        self.assertEqual(emit.call_args.kwargs["purchase_id"], 1)
        conn.close()

    def test_failed_discount_purchase_emits_no_event(self) -> None:
        from app import storage_shop

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE shop_discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT,
                category TEXT,
                base_price INTEGER,
                discount_price INTEGER,
                stock_total INTEGER,
                stock_used INTEGER,
                discount_kind TEXT,
                jornada INTEGER,
                active INTEGER,
                created_at INTEGER,
                announced_at INTEGER,
                activates_at INTEGER,
                exhausted_at INTEGER
            )
            """
        )
        emit = Mock()
        with (
            patch.object(storage_shop, "_supabase_enabled", return_value=False),
            patch.object(storage_shop, "_conn", self._conn_context(conn)),
            patch("app.activity.events.emit_purchase_completed", emit),
        ):
            result = storage_shop.purchase_shop_discount(user="Samu", discount_id=99, jornada=4)

        self.assertFalse(result["purchased"])
        emit.assert_not_called()
        conn.close()

    def test_team_lock_emits_event_after_upsert(self) -> None:
        from app import storage_shop

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE team_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jornada INTEGER,
                user TEXT,
                team_json TEXT,
                save_id INTEGER,
                save_sha256 TEXT,
                locked_at INTEGER,
                deadline_at INTEGER,
                is_late INTEGER,
                UNIQUE(jornada, user)
            )
            """
        )
        emit = Mock()
        with (
            patch.object(storage_shop, "_supabase_enabled", return_value=False),
            patch.object(storage_shop, "_conn", self._conn_context(conn)),
            patch("app.activity.events.emit_team_locked", emit),
            patch.object(storage_shop.time, "time", return_value=1200),
        ):
            lock = storage_shop.upsert_team_lock(
                jornada=4,
                user="Anto",
                team=[{"species": "Milotic"}],
                save_id=7,
                save_sha256="abc",
            )

        self.assertIsNotNone(lock)
        emit.assert_called_once()
        self.assertEqual(emit.call_args.kwargs["trainer"], "Anto")
        self.assertEqual(emit.call_args.kwargs["jornada"], 4)
        conn.close()


if __name__ == "__main__":
    unittest.main()
