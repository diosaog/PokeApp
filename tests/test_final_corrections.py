"""Focused regressions for unattended sync and webhook delivery ambiguity."""

import logging
from datetime import UTC, datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from app.application.discord_webhook import DiscordWebhook, _classify
from app.launcher.backend import BackendClient, BackendError
from app.launcher.runtime import LauncherRuntime
from test_personal_saves import PersonalDeliveryTests, ORIGIN, TRAINER_ID, HASH
from app.application.announcements import Dispatcher, render, gather, Skip, embed
from app.application.discord_webhook import Outcome


class PersonalTransportTests(PersonalDeliveryTests):
    def test_real_http_boundary_accepts_only_exact_personal_upload(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=self.receipt)

        client = BackendClient(ORIGIN, transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        self.assertEqual(
            client.upload(
                "/v1/me/save/raw?sha256=" + HASH, b"bytes", "fictional-token"
            ),
            self.receipt,
        )
        self.assertEqual(calls[0].headers["authorization"], "Bearer fictional-token")
        self.assertEqual(calls[0].content, b"bytes")
        for path in [
            "/v1/me/save/raw/extra",
            "//evil.invalid/v1/me/save/raw",
            "/v1/me/save/rawx",
        ]:
            with self.assertRaises(ValueError):
                client.upload(path, b"bytes", "fictional-token")
        self.assertEqual(len(calls), 1)

    def test_retry_survives_five_technical_failures_but_not_semantic_block(self):
        with self.store.journal.connection() as db:
            db.execute("UPDATE trusted_save_outbox SET attempts=5")
        self.assertIsNotNone(self.store.pending(ORIGIN, TRAINER_ID))
        with self.store.journal.connection() as db:
            db.execute("UPDATE trusted_save_outbox SET blocked=1")
        self.assertIsNone(self.store.pending(ORIGIN, TRAINER_ID))


class UnattendedLoopTests(unittest.TestCase):
    def test_network_recovers_without_manual_retry_after_six_failures(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = LauncherRuntime(
                Path(root),
                Mock(),
                client=Mock(origin=ORIGIN),
                token_store=Mock(),
                start=False,
            )
            runtime.session = Mock()
            runtime.stop = Mock()
            runtime.stop.wait.side_effect = [False] * 8 + [True]
            runtime._cloud_step = Mock(
                side_effect=[BackendError("BACKEND_UNAVAILABLE")] * 6 + [None, None]
            )
            with patch(
                "app.launcher.runtime.time.monotonic",
                side_effect=iter(range(0, 50000, 1000)),
            ):
                runtime._cloud_loop()
            self.assertEqual(runtime._cloud_step.call_count, 8)


class WebhookSafetyTests(unittest.TestCase):
    URL = "https://discord.com/api/webhooks/123456789/" + "fictional_token_" * 3

    def webhook(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return DiscordWebhook(self.URL, client=client, sleep=lambda _: None)

    def test_transport_never_retries_ambiguous_post(self):
        for error in [
            httpx.WriteError,
            httpx.WriteTimeout,
            httpx.ReadError,
            httpx.ReadTimeout,
        ]:
            with self.subTest(error=error):

                def handler(request):
                    raise error("fictional transport failure")

                self.assertEqual(
                    self.webhook(handler).post({"content": "test"}).result, "uncertain"
                )
        for status in [500, 502, 503, 521, 522, 523]:
            self.assertEqual(_classify(httpx.Response(status)).result, "uncertain")
        self.assertEqual(_classify(httpx.Response(200, json={})).result, "uncertain")

    def test_connection_and_rate_limit_are_safe_bounded_retries(self):
        def handler(request):
            raise httpx.ConnectError("offline")

        self.assertEqual(self.webhook(handler).post({}).result, "retry")
        result = _classify(httpx.Response(429, json={"retry_after": 12}))
        self.assertEqual((result.result, result.retry_after), ("retry", 12))

    def test_receipt_mentions_and_secret_logging(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"id": "987654321"})

        with self.assertLogs("httpx", level=logging.INFO) as log:
            result = self.webhook(handler).post(
                {"content": "@everyone", "allowed_mentions": {"parse": ["everyone"]}}
            )
        self.assertEqual(result.message_id, "987654321")
        self.assertIn(b'"parse":[]', requests[0].content)
        self.assertNotIn("fictional_token_", "\n".join(log.output))


class AnnouncementTests(unittest.TestCase):
    def test_unknown_post_is_not_retried_but_edit_can_reconcile_by_id(self):
        outbox, webhook = Mock(), Mock()
        dispatcher = Dispatcher(outbox, Mock(), webhook)
        row = dict(
            id="row",
            status="pending",
            revision=1,
            kind="season_started",
            subject={},
            attempts=1,
            discord_message_id=None,
            claimed_at=datetime.now(UTC).isoformat(),
        )
        outbox.claim.return_value = row
        webhook.post.return_value = Outcome("uncertain", "response_lost")
        webhook.edit.return_value = Outcome("uncertain", "response_lost")
        with (
            patch("app.application.announcements.gather", return_value={}),
            patch("app.application.announcements.render", return_value={}),
        ):
            dispatcher._deliver(row)
            self.assertEqual(outbox.update.call_args.args[1]["status"], "uncertain")
            row.update(status="sent", discord_message_id="123")
            dispatcher._deliver(row)
            self.assertEqual(outbox.update.call_args.args[1]["status"], "sent")
            self.assertIn("next_attempt_at", outbox.update.call_args.args[1])
        self.assertEqual(webhook.post.call_count, 1)
        self.assertEqual(webhook.edit.call_count, 1)

    def test_lost_claim_never_contacts_discord_and_retry_budget_is_finite(self):
        outbox, webhook = Mock(), Mock()
        dispatcher = Dispatcher(outbox, Mock(), webhook)
        outbox.claim.return_value = None
        dispatcher._deliver({"status": "pending"})
        webhook.post.assert_not_called()
        row = dict(id="row", attempts=8, revision=1, claimed_at="original-claim")
        dispatcher._retry(row, False, "connect_failed", 0)
        self.assertEqual(
            outbox.update.call_args.args,
            (row, {"status": "failed", "last_error": "connect_failed"}),
        )

    def test_private_fields_cannot_escape_team_renderer(self):
        facts = dict(
            kind="team_locked",
            season="Prueba",
            trainer="@everyone",
            matchday=1,
            late=False,
            revision=1,
            team=[
                dict(
                    species="Pikachu",
                    nickname="Partner",
                    level=20,
                    ivs="SECRET_IVS",
                    nature="SECRET_NATURE",
                    ability="SECRET_ABILITY",
                )
            ],
            fixed=1,
            participants=2,
            at=None,
        )
        text = str(render(facts))
        for secret in ["SECRET_IVS", "SECRET_NATURE", "SECRET_ABILITY", "@everyone"]:
            self.assertNotIn(secret, text)
        self.assertIn("Pikachu", text)

    def test_private_trial_and_missing_confirmed_source_fail_closed(self):
        def read(table, columns, **filters):
            return (
                [{"is_public": "false", "status": "resolved"}]
                if table == "trial_cases"
                else []
            )

        with self.assertRaises(Skip):
            gather("trial_resolved", {"case_id": "case"}, read)
        with self.assertRaises(Skip):
            gather("season_finished", {"finalization_id": "absent"}, read)

    def test_large_embed_remains_under_discord_limits(self):
        result = embed(
            title="T" * 256,
            description="D" * 4096,
            color=1,
            footer="footer",
            fields=[{"name": "Name", "value": "v" * 1000} for _ in range(50)],
        )["embeds"][0]
        fields = result.get("fields", [])
        self.assertLessEqual(len(fields), 25)
        self.assertLessEqual(
            len(result["title"])
            + len(result["description"])
            + len(result["footer"]["text"])
            + sum(len(f["name"]) + len(f["value"]) for f in fields),
            6000,
        )


if __name__ == "__main__":
    unittest.main()
