"""Personal progress is not League acceptance; the original selected bytes are.

Synthetic snapshots only. These tests exercise the durable runtime/outbox
boundary when a League starts after personal sync, without promoting a cached
personal projection, inventing a Team Lock or awarding any coins.
"""

import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from test_phase21_progress import facts, payload

from app.launcher.backend import BackendError, BackendPrincipal
from app.launcher.journal import LocalReceipt
from app.launcher.runtime import LauncherRuntime, save_identity
from app.launcher.trusted_sync import PERSONAL
from app.save_parser.models import ObservedSave, SaveFingerprint


ORIGIN = "https://api.invalid"
TRAINER = "11111111-1111-4111-8111-111111111111"
OTHER = "33333333-3333-4333-8333-333333333333"
SEASON = "22222222-2222-4222-8222-222222222222"
DISCARDED = "44444444-4444-4444-8444-444444444444"
VERSION = "pokeapp-reader/3;pkhex/24.11.11"


class PersonalToLeagueSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pokeapp-077-sync-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.runtime = LauncherRuntime(
            self.root / "profile", Mock(), client=Mock(origin=ORIGIN),
            token_store=Mock(), start=False,
        )
        self.source = self.root / "main"
        self.runtime.session = Mock()
        self.runtime._patch(
            principal={"trainer_id": TRAINER}, cloud_sync=True,
            cloud={"data": {"season": None}},
        )
        self.select(b"synthetic Y snapshot: badge one", badges=1)
        self.uploads = []
        self.receipts = {}
        self.runtime.session.request.side_effect = self.request
        self.runtime.session.upload.side_effect = self.upload

    def select(self, data, *, badges):
        self.source.write_bytes(data)
        value = payload("Y")
        value["native_progress"] = facts("Y", badge_flags=[i < badges for i in range(8)])
        self.runtime.receipt = LocalReceipt(
            "fixture-" + str(badges), badges,
            SaveFingerprint(sha256=sha256(data).hexdigest(), size=len(data)),
            VERSION, ObservedSave.model_validate_json(json.dumps(value)),
        )
        self.runtime._patch(selected_save=str(self.source), local_status="READY")

    def request(self, method, path, **kwargs):
        if "/receipt?" in path:
            return self.receipts.get(path)
        if path == "/v1/read/seasons":
            return {"items": [{"id": SEASON, "status": "active"}]}
        if path.endswith(("/item-uses", "/transfers")):
            return None
        if path.endswith("/shop"):
            return {"balance": "0"}
        if path.endswith("/context"):
            return {"current_save_id": None, "save_identity": None}
        if path == "/v1/me/pc":
            return {"status": "ready", "save": {"id": TRAINER}}
        if path == f"/v1/read/seasons/{SEASON}/pc":
            return {"status": "ready", "save": {"id": SEASON}}
        raise AssertionError(path)

    def upload(self, path, data):
        from urllib.parse import parse_qs, urlsplit

        route = urlsplit(path)
        params = parse_qs(route.query)
        personal = route.path.startswith("/v1/me/")
        receipt = dict(
            status="registered", save_id=TRAINER if personal else SEASON,
            trainer_id=TRAINER, season_id=PERSONAL if personal else SEASON,
            sha256=params["sha256"][0], parser_version=VERSION,
            observation_digest=params["observation_digest"][0], is_current=True,
        )
        self.uploads.append((receipt["season_id"], data))
        self.receipts[route.path.removesuffix("/raw") + "/receipt?sha256=" + receipt["sha256"]] = receipt
        return receipt

    def queued(self):
        with self.runtime.store.journal.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM trusted_save_outbox ORDER BY rowid")]

    def link(self, status="OPEN", identity=None):
        self.runtime._patch(cloud={"data": {
            "season": {"id": SEASON},
            "season_link": {"status": status, "identity": identity},
        }})

    def stale_discarded_row(self):
        """An upload the server accepted for a season discarded before its readback."""
        self.select(b"synthetic Y snapshot: old discarded season", badges=1)
        old = self.runtime.receipt
        data = self.source.read_bytes()
        self.runtime.store.enqueue_raw(ORIGIN, TRAINER, DISCARDED, old, data)
        digest = self.queued()[0]["digest"]
        self.select(b"synthetic Y snapshot: the League save", badges=2)
        self.link("OPEN")
        return dict(
            status="registered", save_id=DISCARDED, trainer_id=TRAINER, season_id=DISCARDED,
            sha256=old.fingerprint.sha256, parser_version=VERSION,
            observation_digest=digest, is_current=True,
        )

    def test_discarded_season_row_held_back_every_newer_save(self):
        # Reproduces production: the receipt still answered 200 and the readback
        # 404, classified as a lost connection, so the oldest row never finished.
        accepted = self.stale_discarded_row()
        self.receipts[
            f"/v1/seasons/{DISCARDED}/saves/receipt?sha256={accepted['sha256']}"
        ] = accepted

        def request(method, path, **kwargs):
            if path == f"/v1/read/seasons/{DISCARDED}/pc":
                raise BackendError("BACKEND_UNAVAILABLE", status=404, detail="NOT_FOUND")
            return self.request(method, path, **kwargs)

        self.runtime.session.request.side_effect = request
        self.runtime._enqueue_local()
        for _ in range(3):
            with self.assertRaises(BackendError):
                self.runtime._deliver_pending(TRAINER)
        self.assertEqual(self.uploads, [])
        self.assertEqual(self.queued()[0]["season"], DISCARDED)
        self.assertEqual(self.queued()[0]["attempts"], 3)

    def test_discarded_season_row_is_closed_and_the_league_save_goes_up(self):
        # The API now answers 404 for that receipt: installed Launchers close
        # the row themselves, and the selected save reaches the League.
        self.stale_discarded_row()
        self.runtime._enqueue_local()
        self.runtime._deliver_pending(TRAINER)
        self.assertEqual({scope for scope, _ in self.uploads}, {SEASON, PERSONAL})
        self.assertEqual(self.uploads[0][1], self.source.read_bytes())
        self.assertEqual(self.runtime.state()["season_receipt"]["season_id"], SEASON)
        stale = next(r for r in self.queued() if r["season"] == DISCARDED)
        self.assertEqual((stale["blocked"], stale["raw"]), (1, None))
        self.assertIsNone(self.runtime.store.pending(ORIGIN, TRAINER))

    def test_same_selected_bytes_sync_to_newly_active_league_once_then_new_progress(self):
        self.runtime._enqueue_local()
        self.runtime._deliver_pending(TRAINER)
        self.assertEqual([scope for scope, _ in self.uploads], [PERSONAL])
        self.assertIsNone(self.runtime.state()["season_receipt"])

        # A fresh authorized OPEN context is what makes the League eligible;
        # no file change or manual Team Lock is required.
        principal = BackendPrincipal(
            trainer_id=TRAINER, display_name="Fixture", globally_enabled=True,
            is_admin=False,
        )
        self.runtime.session._principal = principal
        self.runtime.session.principal.return_value = principal
        self.runtime.client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        self.runtime._cloud_step()
        self.assertEqual([scope for scope, _ in self.uploads], [PERSONAL, SEASON])
        self.assertEqual(self.uploads[0][1], self.uploads[1][1])
        self.assertEqual(self.runtime.state()["season_receipt"]["season_id"], SEASON)
        self.runtime._enqueue_local()
        self.runtime._deliver_pending(TRAINER)
        self.assertEqual(len(self.uploads), 2)

        self.link("BOUND", save_identity(self.runtime.receipt))
        self.select(b"synthetic Y snapshot: badge two", badges=2)
        self.runtime._enqueue_local()
        self.runtime._deliver_pending(TRAINER)
        self.assertEqual([scope for scope, _ in self.uploads], [PERSONAL, SEASON, SEASON, PERSONAL])
        self.assertEqual(sum(self.runtime.receipt.observation.native_progress.badge_flags), 2)
        self.assertEqual(len(self.queued()), 4)
        self.assertTrue(all(r["verified"] and r["raw"] is None for r in self.queued()))

    def test_other_game_or_trainer_and_ineligible_membership_keep_personal_only(self):
        own = save_identity(self.runtime.receipt)
        wrong_game = own | {"game": "X"}
        wrong_trainer = own | {"trainer": own["trainer"] | {"tid": own["trainer"]["tid"] + 1}}
        for status, identity in (
            ("BOUND", wrong_game), ("BOUND", wrong_trainer),
            ("NOT_PARTICIPANT", None), ("CLOSED", None), ("OTHER_SAVE", None),
        ):
            with self.subTest(status=status, identity=identity):
                self.link(status, identity)
                self.runtime._enqueue_local()
                self.assertEqual({r["season"] for r in self.queued()}, {PERSONAL})

    def test_wrong_account_cannot_deliver_another_accounts_pending_bytes(self):
        self.link()
        self.runtime._enqueue_local()
        # The login transition clears the old account's cached cloud context.
        self.runtime._patch(principal={"trainer_id": OTHER}, cloud=None)
        self.runtime._deliver_pending(OTHER)
        self.runtime.session.upload.assert_not_called()
        self.assertIsNotNone(self.runtime.store.pending(ORIGIN, TRAINER))
        self.assertIsNone(self.runtime.store.pending(ORIGIN, OTHER))

    def test_wrong_scope_receipt_is_never_presented_as_league_acceptance(self):
        self.link()
        self.runtime._enqueue_local()
        original = self.upload
        self.runtime.session.upload.side_effect = lambda path, data: original(path, data) | {"trainer_id": OTHER}
        with self.assertRaisesRegex(BackendError, "SAVE_RECEIPT_MISMATCH"):
            self.runtime._deliver_pending(TRAINER)
        self.assertIsNone(self.runtime.state()["season_receipt"])
        self.assertFalse(any(r["verified"] for r in self.queued()))


if __name__ == "__main__":
    unittest.main()
