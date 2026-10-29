import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from phase9_fixtures import FakeParser
from test_api_item_use import SEASON_ID, TRAINER_ID, receipt

from app.launcher.backend import BackendError, BackendPrincipal
from app.launcher.runtime import LauncherRuntime
from app.save_parser.adapter import SaveInspector


class ItemStatusRuntimeTests(unittest.TestCase):
    def runtime(self, payload):
        temp = tempfile.TemporaryDirectory(prefix="pokeapp-phase23-runtime-")
        self.addCleanup(temp.cleanup)
        client = Mock(origin="https://fixture.example")
        client.json.return_value = {"status": "ok", "service": "pokeapp-api"}
        runtime = LauncherRuntime(
            Path(temp.name),
            SaveInspector(FakeParser()),
            client=client,
            token_store=Mock(),
            start=False,
        )
        self.addCleanup(runtime.close)
        principal = BackendPrincipal(
            trainer_id=TRAINER_ID,
            display_name="Fixture",
            globally_enabled=True,
            is_admin=False,
        )
        runtime.session = Mock(_principal=principal)
        runtime.session.principal.return_value = principal

        def get(method, path, **kwargs):
            self.assertEqual(method, "GET")
            if path == "/v1/read/seasons":
                return {"items": [{"id": SEASON_ID, "status": "active"}]}
            if path.endswith("/saves/context"):
                return {"current_save_id": None, "save_identity": None}
            if path.endswith("/shop"):
                return {"balance": "25"}
            if path.endswith("/item-uses"):
                self.assertTrue(kwargs["missing"])
                return payload
            if path.endswith("/transfers"):
                self.assertTrue(kwargs["missing"])
                return None
            self.fail("unexpected request")

        runtime.session.request.side_effect = get
        return runtime

    def test_scoped_status_only_cache_no_write_capability(self):
        runtime = self.runtime({"items": [receipt(status="RECOVERY_REQUIRED")]})
        runtime._cloud_step()
        data = runtime.state()["cloud"]["data"]
        self.assertEqual(data["item_uses"], [{"status": "RECOVERY_REQUIRED"}])
        self.assertEqual(data["wallet"], "25")
        self.assertFalse(runtime.writes.state()["production_operations_enabled"])

    def test_old_backend_without_endpoint_stays_read_sync_compatible(self):
        runtime = self.runtime(None)
        runtime._cloud_step()
        self.assertIsNone(runtime.state()["cloud"]["data"]["item_uses"])
        self.assertEqual(runtime.state()["cloud_status"], "ONLINE")

    def test_foreign_or_capability_grant_dto_rejected(self):
        for payload in (
            {"items": [receipt(trainer_id=str(uuid4()))]},
            {"items": [], "physical_application_enabled": True},
            {"items": [{"status": "APPLIED_VERIFIED"}]},
        ):
            with self.subTest(payload=payload):
                runtime = self.runtime(payload)
                with self.assertRaises(BackendError):
                    runtime._cloud_step()
                self.assertIsNone(runtime.state()["cloud"])


if __name__ == "__main__":
    unittest.main()
