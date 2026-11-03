"""A save synced as personal before the League started still reaches the League.

Iker's case (2026-11-02): his Y save went to his personal record at 02:25 UTC,
ChampionsLocke was activated at 17:51 and his Launcher was not opened again.
These synthetic runs pin what happens when it is: after a restart on the same
profile the unchanged bytes are registered in the League once, a lost answer is
reconciled by its receipt instead of a second registration, and later restarts
upload nothing again.
"""

import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from test_phase21_progress import facts, payload

from app.launcher.backend import BackendError, BackendPrincipal
from app.launcher.journal import LocalReceipt
from app.launcher.runtime import LauncherRuntime
from app.launcher.trusted_sync import PERSONAL
from app.save_parser.models import ObservedSave, SaveFingerprint

ORIGIN = "https://api.invalid"
TRAINER = "11111111-1111-4111-8111-111111111111"
SEASON = "22222222-2222-4222-8222-222222222222"
VERSION = "pokeapp-reader/3;pkhex/24.11.11"
PRINCIPAL = BackendPrincipal(
    trainer_id=TRAINER, display_name="Iker", globally_enabled=True, is_admin=False
)


class Server:
    """PokeApp API double: one registration per (scope, hash), like the SQL."""

    def __init__(self):
        self.active = False
        self.receipts = {}
        self.puts = []
        self.lose_next_answer = False

    def request(self, method, path, **kwargs):
        if "/receipt?" in path:
            return self.receipts.get(path)
        if path == "/v1/read/seasons":
            items = [{"id": SEASON, "status": "active"}] if self.active else []
            return {"items": items, "next_offset": None}
        if path.endswith(("/item-uses", "/transfers")):
            return None
        if path.endswith("/shop"):
            return {"balance": "0"}
        if path == f"/v1/seasons/{SEASON}/saves/context":
            current = next(
                (r["save_id"] for k, r in self.receipts.items() if k.startswith("/v1/seasons/")),
                None,
            )
            return {"current_save_id": current, "save_identity": None}
        if path == "/v1/me/save/context":
            return {"current_save_id": None, "save_identity": None}
        if path == "/v1/me/pc":
            return {"status": "ready", "save": {"id": TRAINER}}
        if path == f"/v1/read/seasons/{SEASON}/pc":
            return {"status": "ready", "save": {"id": SEASON}}
        raise AssertionError(path)

    def upload(self, path, data):
        route = urlsplit(path)
        params = parse_qs(route.query)
        personal = route.path.startswith("/v1/me/")
        key = route.path.removesuffix("/raw") + "/receipt?sha256=" + params["sha256"][0]
        if key in self.receipts:
            raise AssertionError("a registered hash was uploaded again")
        receipt = dict(
            status="registered", save_id=TRAINER if personal else SEASON,
            trainer_id=TRAINER, season_id=PERSONAL if personal else SEASON,
            sha256=params["sha256"][0], parser_version=VERSION,
            observation_digest=params["observation_digest"][0], is_current=True,
        )
        self.puts.append(receipt["season_id"])
        self.receipts[key] = receipt
        if self.lose_next_answer:
            # Registered server-side, but the answer never reached the Launcher.
            self.lose_next_answer = False
            raise BackendError("BACKEND_UNAVAILABLE", cause="ReadTimeout")
        return receipt


class LeagueRegistrationRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pokeapp-league-recovery-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.save = self.root / "main"
        self.data = b"synthetic Y snapshot: two badges, three in Box 7"
        self.save.write_bytes(self.data)
        self.server = Server()

    def launcher(self):
        """A Launcher start on the same profile: durable outbox, fresh memory."""
        runtime = LauncherRuntime(
            self.root / "profile", Mock(), client=Mock(origin=ORIGIN),
            token_store=Mock(), start=False,
        )
        runtime.session = Mock()
        runtime.session._principal = PRINCIPAL
        runtime.session._tokens = None
        runtime.session.principal.return_value = PRINCIPAL
        runtime.session.request.side_effect = self.server.request
        runtime.session.upload.side_effect = self.server.upload
        runtime.client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        value = payload("Y")
        value["native_progress"] = facts("Y", badge_flags=[i < 2 for i in range(8)])
        runtime.receipt = LocalReceipt(
            "fixture", 1,
            SaveFingerprint(sha256=sha256(self.data).hexdigest(), size=len(self.data)),
            VERSION, ObservedSave.model_validate_json(json.dumps(value)),
        )
        runtime._patch(
            principal=PRINCIPAL.model_dump(), cloud_sync=True,
            selected_save=str(self.save), local_status="READY",
        )
        return runtime

    def test_restart_after_activation_registers_the_unchanged_save_once(self):
        before = self.launcher()
        before._cloud_step()
        self.assertEqual(self.server.puts, [PERSONAL])
        self.assertIsNone(before.state()["season_receipt"])

        self.server.active = True  # the League starts while the Launcher is closed
        after = self.launcher()
        after._cloud_step()
        self.assertEqual(self.server.puts, [PERSONAL, SEASON])
        self.assertEqual(after.state()["season_receipt"]["season_id"], SEASON)

        for _ in range(2):  # later starts reconcile receipts, never upload again
            again = self.launcher()
            again._cloud_step()
            self.assertEqual(self.server.puts, [PERSONAL, SEASON])
            self.assertEqual(again.state()["season_receipt"]["season_id"], SEASON)

    def test_a_lost_answer_is_reconciled_by_its_receipt_not_a_second_registration(self):
        self.server.active = True
        self.server.lose_next_answer = True
        runtime = self.launcher()
        with self.assertRaisesRegex(BackendError, "BACKEND_UNAVAILABLE"):
            runtime._cloud_step()
        self.assertEqual(self.server.puts, [SEASON])
        self.assertIsNone(runtime.state()["season_receipt"])
        self.assertEqual(runtime.state()["outbox"]["paused"], 0)

        runtime._cloud_step()  # the next unattended turn, or the next start
        self.assertEqual(self.server.puts, [SEASON, PERSONAL])
        self.assertEqual(runtime.state()["season_receipt"]["season_id"], SEASON)
        self.assertIsNotNone(runtime.state()["cloud_receipt"])


if __name__ == "__main__":
    unittest.main()
