"""Real PostgREST transport with injected response loss; no remote requests."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import unittest

import httpx
from postgrest import SyncPostgrestClient

from app.repositories.errors import PersistenceError
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository


class FrontendReadRecoveryTests(unittest.TestCase):
    def client(self, handler):
        client = SyncPostgrestClient("https://example.invalid/rest/v1")
        client.session = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.session.close)
        return client

    def operations(self, repo):
        return (
            (
                lambda: repo.rows(
                    "save_files",
                    "id",
                    filters={
                        "trainer_id": "owner",
                        "season_id": "season",
                        "deleted_at": None,
                    },
                    offset=5,
                    limit=10,
                ),
                [],
            ),
            (lambda: repo.league_general("season"), {"rows": []}),
            (lambda: repo.initial_observations("season"), []),
            (lambda: repo.observed_progress("season", "owner"), []),
        )

    def test_lost_response_retries_same_scoped_read_once(self):
        for index in range(4):
            requests = []

            def respond(request):
                requests.append(
                    (
                        request.method,
                        str(request.url),
                        request.content,
                        dict(request.headers),
                    )
                )
                if len(requests) == 1:
                    raise httpx.ReadError("SECRET upstream payload", request=request)
                return httpx.Response(200, json=expected)

            repo = SupabaseFrontendReadRepository(self.client(respond))
            operation, expected = self.operations(repo)[index]
            with (
                self.subTest(index=index),
                self.assertLogs("app.repositories.supabase.frontend_reads") as logs,
            ):
                self.assertEqual(operation(), expected)
            self.assertEqual(len(requests), 2)
            self.assertEqual(requests[0], requests[1])
            self.assertIn("frontend_read_retry", str(logs.output))
            self.assertNotIn("SECRET", str(logs.output))

    def test_persistent_read_error_is_bounded_and_sanitized(self):
        for index in range(4):
            requests = []

            def respond(request):
                requests.append(request)
                raise httpx.ReadError("SECRET upstream payload", request=request)

            repo = SupabaseFrontendReadRepository(self.client(respond))
            with (
                self.subTest(index=index),
                self.assertLogs("app.repositories.supabase.frontend_reads") as logs,
                self.assertRaises(PersistenceError) as error,
            ):
                self.operations(repo)[index][0]()
            self.assertEqual(len(requests), 2)
            self.assertNotIn("SECRET", str(error.exception))
            self.assertNotIn("SECRET", str(logs.output))

    def test_http_denials_and_backend_status_failures_are_not_retried(self):
        for status in (401, 403, 409, 500, 503):
            for index in range(4):
                requests = []

                def respond(request):
                    requests.append(request)
                    return httpx.Response(
                        status,
                        json={
                            "code": "XX000",
                            "message": "SECRET",
                            "hint": None,
                            "details": None,
                        },
                    )

                repo = SupabaseFrontendReadRepository(self.client(respond))
                with (
                    self.subTest(status=status, index=index),
                    self.assertRaises(PersistenceError),
                ):
                    self.operations(repo)[index][0]()
                self.assertEqual(len(requests), 1)

    def test_other_transport_errors_are_not_retried(self):
        for error_type in (
            httpx.ReadTimeout,
            httpx.WriteError,
            httpx.ConnectError,
            httpx.LocalProtocolError,
            ValueError,
        ):
            requests = []

            def respond(request):
                requests.append(request)
                raise error_type("SECRET")

            repo = SupabaseFrontendReadRepository(self.client(respond))
            with (
                self.subTest(error=error_type.__name__),
                self.assertRaises(PersistenceError),
            ):
                repo.rows("seasons", "id")
            self.assertEqual(len(requests), 1)

    def test_concurrent_requests_have_independent_retry_budgets_and_scope(self):
        counts, lock, barrier = Counter(), Lock(), Barrier(4)

        def respond(request):
            owner = request.url.params["trainer_id"]
            with lock:
                counts[owner] += 1
                attempt = counts[owner]
            if attempt == 1:
                barrier.wait(timeout=10)
                raise httpx.ReadError("SECRET response loss", request=request)
            return httpx.Response(200, json=[{"id": owner}])

        repo = SupabaseFrontendReadRepository(self.client(respond))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda n: repo.rows(
                        "save_files", "id", filters={"trainer_id": str(n)}
                    ),
                    range(4),
                )
            )
        self.assertEqual(results, [[{"id": f"eq.{n}"}] for n in range(4)])
        self.assertEqual(counts, {f"eq.{n}": 2 for n in range(4)})

    def test_initial_finalization_never_inherits_read_retry(self):
        requests = []

        def respond(request):
            requests.append(request)
            raise httpx.ReadError("SECRET unknown outcome", request=request)

        repo = SupabaseSeasonAdminRepository(self.client(respond))
        with self.assertRaises(PersistenceError):
            repo.execute("initial_finalize", {"body": {}})
        self.assertEqual(len(requests), 1)
