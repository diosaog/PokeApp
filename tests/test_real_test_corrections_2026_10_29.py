"""Second real test (2026-10-29): «Objetos ∞», live updates, dead box, sync speed.

Each class pins one cause found in the owner's Launcher 0.26.5 and production:
the packaged core lacked app.domain.unlimited_items, so every quick-item read
failed silently and marked the save unreadable; the API's shared HTTP/2
connection to Supabase failed every read at once after a confirmed change; a
sync spent ~29 s on sequential requests around two uploads.
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from test_launcher_stability import ORIGIN, SEASON, TRAINER, Harness

from app.launcher.runtime import PERSONAL, QUICK_READ_FAILED

REPO = Path(__file__).resolve().parents[1]


class QuickItemsAlwaysEndTests(Harness):
    def engine(self):
        engine = Mock()
        engine.native.inventory.return_value = {
            "game": "Y",
            "trainer_key": "b" * 64,
            "source_sha256": sha256(b"save").hexdigest(),
            "items": {
                "rare_candy": {"count": 0, "max": 999, "addable": 999},
                "heart_scale": {"count": 4, "max": 999, "addable": 995},
            },
        }
        engine.files.read_path.return_value = b"save"
        engine.allows.return_value = True
        return engine

    def test_counts_are_read_and_adding_is_enabled(self):
        runtime = self.runtime()
        runtime.writes.engine = self.engine()
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime._quick_step("quick_items_refresh", {})
        state = runtime.state()
        self.assertTrue(state["quick_items"]["application_enabled"])
        self.assertEqual(state["quick_items"]["items"]["heart_scale"]["count"], 4)
        self.assertIsNone(state["quick_item_error"])
        self.assertEqual(state["quick_item_seq"], 1)

    def test_an_unexpected_failure_ends_with_a_reason_not_reading_forever(self):
        runtime = self.runtime()
        runtime.writes.engine = self.engine()
        runtime.writes.engine.native.inventory.side_effect = ImportError("missing")
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime._quick_step("quick_items_refresh", {})
        state = runtime.state()
        self.assertIsNone(state["quick_items"])
        self.assertEqual(state["quick_item_error"], QUICK_READ_FAILED)
        self.assertEqual(state["quick_item_seq"], 1)
        self.assertEqual(state["local_status"], "READY")

    def test_a_native_read_failure_is_explained(self):
        from app.save_parser.writer import NativeWriteError

        runtime = self.runtime()
        runtime.writes.engine = self.engine()
        runtime.writes.engine.native.inventory.side_effect = NativeWriteError(
            "VERIFICATION_FAILED"
        )
        runtime.writes.selected = Mock(return_value=str(self.ready(runtime)))
        runtime._quick_step("quick_items_refresh", {})
        self.assertIn("leer la bolsa", runtime.state()["quick_item_error"])

    def test_a_failed_write_step_never_marks_the_save_unreadable(self):
        runtime = self.runtime()
        self.ready(runtime)
        runtime._write_step = Mock(side_effect=RuntimeError("boom"))
        runtime._local_step = Mock(side_effect=lambda: runtime.stop.set())
        runtime._local_loop()
        state = runtime.state()
        self.assertEqual(state["local_status"], "READY")
        self.assertTrue(state["write_error"])

    def test_the_idle_changes_panel_says_nothing_about_disabled_trades(self):
        runtime = self.runtime()
        write = runtime.state()["write"]
        self.assertTrue(write["idle"])
        self.assertEqual(write["message"], "No hay cambios pendientes.")


class WriteWaitsForSyncTests(unittest.TestCase):
    """A click on «Añadir a la bolsa» during a cloud round waits, then writes."""

    def test_a_write_waits_for_another_threads_read_and_blocks_new_ones(self):
        import threading

        from app.launcher.save_activity import SaveActivityGate, SaveBusy

        gate = SaveActivityGate()
        reading, release, done = threading.Event(), threading.Event(), threading.Event()

        def cloud_round():
            with gate.reading():
                reading.set()
                release.wait(5)
                with gate.reading():  # its own nested step still runs
                    pass
            done.set()

        thread = threading.Thread(target=cloud_round)
        thread.start()
        self.assertTrue(reading.wait(5))
        order = []

        def write():
            with gate.writing(wait=5):
                order.append("write")

        writer = threading.Thread(target=write)
        writer.start()
        time.sleep(0.2)
        # No new read starts while the write waits.
        with self.assertRaises(SaveBusy), gate.reading():
            pass
        order.append("read finishes")
        release.set()
        writer.join(5)
        thread.join(5)
        self.assertTrue(done.is_set())
        self.assertEqual(order, ["read finishes", "write"])
        with gate.reading():  # and reads resume afterwards
            pass

    def test_a_read_of_the_same_thread_or_a_timeout_still_refuses(self):
        import threading

        from app.launcher.save_activity import SaveActivityGate, SaveBusy

        gate = SaveActivityGate()
        with gate.reading(), self.assertRaises(SaveBusy), gate.writing(wait=5):
            pass
        held = gate.reading()
        held.__enter__()
        try:
            started = time.monotonic()
            result = []

            def write():
                try:
                    with gate.writing(wait=0.3):
                        result.append("write")
                except SaveBusy:
                    result.append("busy")

            writer = threading.Thread(target=write)
            writer.start()
            writer.join(5)
            self.assertEqual(result, ["busy"])
            self.assertLess(time.monotonic() - started, 3)
        finally:
            held.__exit__(None, None, None)


class PackagedCoreOverlayTests(unittest.TestCase):
    def test_every_desktop_domain_import_is_in_the_overlay(self):
        from tools.prepare_launcher_core import prepare, required_domain_modules

        sources = [
            p for g in ("launcher", "save_parser") for p in (REPO / "app" / g).glob("*.py")
        ]
        self.assertIn("app.domain.unlimited_items", required_domain_modules(sources))
        with tempfile.TemporaryDirectory() as temp:
            overlay = Path(temp) / "core"
            prepare(overlay)
            # Only the overlay on the path: what PyInstaller can bundle.
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    (
                        "import sys; sys.path.insert(0, sys.argv[1]);"
                        "import app.launcher.runtime, app.launcher.quick_items;"
                        "print(sorted(app.launcher.quick_items.QUICK_ITEMS))"
                    ),
                    str(overlay),
                ],
                cwd=temp,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
                timeout=60,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            self.assertIn("rare_candy", result.stdout)


class FastSyncTests(Harness):
    def logged_in(self, runtime, *, fresh=True):
        save = self.ready(runtime)
        runtime.session = Mock(
            _principal=Mock(trainer_id=TRAINER),
            _tokens=Mock(expires_at=time.time() + 3600),
        )
        runtime._patch(cloud={"data": {"season": {"id": SEASON}}})
        runtime.next_cloud_refresh = time.monotonic() + (60 if fresh else -1)
        return save

    def test_a_new_save_goes_up_without_the_season_refresh_first(self):
        runtime = self.runtime()
        self.logged_in(runtime)
        runtime.store.pending = Mock(return_value={"season": SEASON})
        runtime._deliver_pending = Mock()
        runtime._cloud_step()
        runtime._deliver_pending.assert_called_once_with(TRAINER)
        runtime.client.json.assert_not_called()  # no /health probe
        runtime.session.request.assert_not_called()  # no season reads first
        runtime.session.principal.assert_not_called()  # no /v1/me
        self.assertEqual(runtime.next_cloud_refresh, 0)  # full refresh next turn

    def test_a_stale_cache_or_short_token_takes_the_full_path(self):
        for fresh, expires in ((False, 3600), (True, 30)):
            with self.subTest(fresh=fresh, expires=expires):
                runtime = self.runtime()
                self.logged_in(runtime, fresh=fresh)
                runtime.session._tokens.expires_at = time.time() + expires
                runtime.store.pending = Mock(return_value={"season": SEASON})
                self.assertFalse(runtime._fast_delivery())

    def test_the_season_copy_is_queued_before_the_personal_record(self):
        runtime = self.runtime()
        self.logged_in(runtime)
        runtime._patch(
            cloud={"data": {"season": {"id": SEASON}, "season_link": {"status": "OPEN"}}}
        )
        runtime._enqueue_local()
        first = runtime.store.pending(ORIGIN, TRAINER)
        self.assertEqual(first["season"], SEASON)
        runtime.store.update(first, verified=1)
        self.assertEqual(runtime.store.pending(ORIGIN, TRAINER)["season"], PERSONAL)

    def test_a_save_is_seen_within_a_second_and_read_once_stable(self):
        runtime = self.runtime()
        save = self.ready(runtime)
        runtime.core.config = runtime.core.config.model_copy(
            update={"selected_save": str(save), "poll_seconds": 5.0, "debounce_seconds": 1.0}
        )
        runtime._load_local()
        self.assertEqual(
            (runtime.watch.poll_seconds, runtime.watch.debounce_seconds), (1.0, 0.75)
        )


class SupabaseTransportTests(unittest.TestCase):
    def test_postgrest_runs_on_one_shared_http11_pool_with_its_headers(self):
        import base64
        import json

        from app.repositories.supabase import http

        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json=[{"ok": 1}])

        def part(value):
            return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

        key = part({"alg": "HS256", "typ": "JWT"}) + "." + part({"role": "service_role"}) + ".s"
        with patch.object(http, "_session", httpx.Client(transport=httpx.MockTransport(handler))):
            first = http.create_client("https://example.supabase.co", key)
            second = http.create_client("https://example.supabase.co", key)
            self.assertIs(first.postgrest.session, second.postgrest.session)
            first.table("trainers").select("id").execute()
            first.rpc("league_general_read", {"p_season_id": "s"}).execute()
        self.assertEqual(
            [str(r.url) for r in seen],
            [
                "https://example.supabase.co/rest/v1/trainers?select=id",
                "https://example.supabase.co/rest/v1/rpc/league_general_read",
            ],
        )
        self.assertTrue(all(r.headers.get("apikey") == key for r in seen))
        self.assertTrue(all(r.headers["authorization"] == f"Bearer {key}" for r in seen))

    def test_the_real_pool_is_http11(self):
        from app.repositories.supabase import http

        with patch.object(http, "_session", None):
            session = http.postgrest_session()
            self.addCleanup(session.close)
            self.assertFalse(session._transport._pool._http2)
            self.assertIs(http.postgrest_session(), session)

    def test_a_dropped_connection_is_retried_once_on_reads(self):
        from app.repositories.supabase.frontend_reads import _execute_read

        query = Mock()
        query.execute.side_effect = [
            httpx.RemoteProtocolError("Server disconnected"),
            Mock(data=[1]),
        ]
        self.assertEqual(_execute_read(query, "rows"), [1])
        self.assertEqual(query.execute.call_count, 2)


class DeadBoxAdminRouteTests(unittest.TestCase):
    def test_route_validates_the_box_and_passes_the_participant(self):
        from app.api.config import APIConfig
        from app.api.dependencies import ApiContainer
        from app.api.main import create_app
        from app.api.models import AuthenticatedPrincipal
        from app.api.security import require_admin_principal

        sid, pid, admin = str(uuid4()), str(uuid4()), str(uuid4())
        repo = Mock()
        repo.execute.return_value = {
            "operation_id": str(uuid4()),
            "resource_id": pid,
            "season_id": sid,
            "event_id": str(uuid4()),
            "replayed": False,
            "state": "active",
            "setup_revision": 3,
            "roster_revision": 2,
            "config_revision": 1,
        }
        app = create_app(container=ApiContainer(season_admin_repository=repo), config=APIConfig())
        app.dependency_overrides[require_admin_principal] = lambda: AuthenticatedPrincipal(
            trainer_id=admin, display_name="Admin", is_admin=True, globally_enabled=True
        )
        client = TestClient(app)
        path = f"/v1/admin/seasons/{sid}/participants/{pid}/dead-box"
        ok = client.put(path, json={"dead_box_number": 7}, headers={"Idempotency-Key": "k1"})
        self.assertEqual(ok.status_code, 200, ok.text)
        operation, request = repo.execute.call_args.args
        self.assertEqual(operation, "dead_box")
        self.assertEqual(
            (request["season_id"], request["resource_id"], request["body"]),
            (sid, pid, {"dead_box_number": 7}),
        )
        for bad in (0, 33, "7", 7.5):
            with self.subTest(bad=bad):
                response = client.put(
                    path, json={"dead_box_number": bad}, headers={"Idempotency-Key": "k2"}
                )
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
