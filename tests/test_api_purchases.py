from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
from postgrest import SyncPostgrestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.domain.normal_purchases import NormalPurchaseRequest, NormalPurchaseReceipt
from app.repositories.errors import PersistenceError
from app.repositories.supabase.normal_purchases import REJECTIONS, SupabaseNormalPurchaseRepository
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier


class NormalPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.season, self.item = str(uuid4()), str(uuid4())
        self.receipt = NormalPurchaseReceipt(
            id=str(uuid4()), season_id=self.season, trainer_id=TRAINER_ID,
            season_player_id=str(uuid4()), item_id=self.item, quantity=1, unit_price=10,
            total_price=10, status="pending", purchased_at="2026-09-22T12:00:00+00:00",
            balance_after=90, ledger_id=str(uuid4()), event_id=str(uuid4()),
            matchday_id=str(uuid4()), matchday_number=2,
        )
        self.rpc_status, self.rpc_body = 200, asdict(self.receipt)
        self.requests = []

        def respond(request):
            self.requests.append(request)
            return httpx.Response(self.rpc_status, json=self.rpc_body)

        pg = SyncPostgrestClient("https://example.invalid/rest/v1")
        pg.session = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(pg.session.close)
        self.repo = SupabaseNormalPurchaseRepository(pg)
        self.principals, self.verifier = FakePrincipalRepository(), FakeTokenVerifier()
        self.container = ApiContainer(token_verifier=self.verifier, principal_repository=self.principals,
                                      purchase_repository=self.repo)
        self.client = TestClient(create_app(container=self.container))
        self.addCleanup(self.client.close)
        self.path = f"/v1/seasons/{self.season}/shop/purchases"

    def post(self, *, body=None, headers=None):
        return self.client.post(self.path, json=body or {"item_id": self.item}, headers=headers if headers is not None else {
            "Authorization": "Bearer dummy", "Idempotency-Key": "request-1",
        })

    def test_p01_missing_bearer(self):
        self.assertEqual(self.post(headers={"Idempotency-Key": "one"}).status_code, 401)
        self.assertEqual(self.requests, [])

    def test_p02_invalid_bearer(self):
        self.verifier.fail = InvalidSessionError()
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.requests, [])

    def test_p03_disabled_even_admin(self):
        self.principals.trainer = replace(self.principals.trainer, globally_enabled=False)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.requests, [])

    def test_p18_forbidden_client_authority(self):
        for field in ("price", "trainer_id", "season_player_id", "quantity", "balance", "status",
                      "promotion_id", "event_payload", "jornada", "matchday_id"):
            with self.subTest(field=field):
                self.assertEqual(self.post(body={"item_id": self.item, field: "forbidden"}).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_p19_p20_p23_p48_success_authority_receipt(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        expected = asdict(self.receipt)
        expected["purchased_at"] = "2026-09-22T12:00:00Z"
        self.assertEqual(response.json(), expected)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.url.path, "/rest/v1/rpc/api_create_normal_purchase")
        self.assertEqual(json.loads(request.content), {
            "p_season_id": self.season, "p_trainer_id": TRAINER_ID, "p_item_id": self.item,
            "p_idempotency_key": "request-1", "p_confirm_base_price": False,
        })
        for private in ("service_role", "auth_user_id", "pepper", "metadata"):
            self.assertNotIn(private, response.text)

    def test_p04_to_p17_p39_to_p44_typed_business_errors(self):
        for code, status in REJECTIONS.items():
            with self.subTest(code=code):
                self.rpc_status = status
                self.rpc_body = {"code": f"PT{status}", "message": code, "hint": "SECRET", "details": "private SQL"}
                response = self.post()
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["code"], code.upper())
                self.assertNotIn("SECRET", response.text)
                self.assertNotIn("private SQL", response.text)

    def test_p50_unknown_backend_error_is_sanitized(self):
        for code, message in (("23503", "SECRET SQL"), ("PT409", "unknown SECRET"), ("XX000", "insufficient_funds")):
            self.rpc_status, self.rpc_body = 500, {"code": code, "message": message, "hint": "SECRET", "details": "SECRET"}
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("SECRET", response.text)

    def test_key_required_and_bounded(self):
        for key in (None, "", " ", "has space", "x" * 129):
            headers = {"Authorization": "Bearer dummy"}
            if key is not None:
                headers["Idempotency-Key"] = key
            self.assertEqual(self.post(headers=headers).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_strict_confirmation_and_uuid(self):
        for value in (None, 0, 1, "true", "false"):
            self.assertEqual(self.post(body={"item_id": self.item, "confirm_base_price": value}).status_code, 422)
        self.assertEqual(self.post(body={"item_id": "bad"}).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_confirmation_forwarded(self):
        self.assertEqual(self.post(body={"item_id": self.item, "confirm_base_price": True}).status_code, 200)
        self.assertTrue(json.loads(self.requests[0].content)["p_confirm_base_price"])

    def test_p31_p49_receipt_returned_not_recomputed(self):
        self.assertEqual(self.post().json(), self.post().json())
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all("/rpc/" in str(r.url) for r in self.requests))

    def test_malformed_receipts_fail_closed(self):
        valid = asdict(self.receipt)
        for body in (None, [], {}, [valid], dict(valid, trainer_id=str(uuid4())), dict(valid, item_id=str(uuid4())),
                     dict(valid, balance_after=-1), dict(valid, quantity=2), dict(valid, total_price=11),
                     dict(valid, status="used"), dict(valid, unit_price=True), dict(valid, event_id="bad"),
                     dict(valid, purchased_at="2026-09-22")):
            with self.subTest(body=body):
                self.rpc_body = body
                self.assertEqual(self.post().status_code, 503)

    def test_port_validates_non_http_caller(self):
        for key in ("", "bad\nkey", "x" * 129):
            with self.assertRaises(ValueError):
                NormalPurchaseRequest(self.season, TRAINER_ID, self.item, key)

    def test_backend_absent(self):
        with TestClient(create_app(container=replace(self.container, purchase_repository=None))) as client:
            response = client.post(self.path, json={"item_id": self.item}, headers={"Authorization": "Bearer dummy", "Idempotency-Key": "x"})
            self.assertEqual(response.status_code, 503)

    def test_p36_p37_p38_boundary_no_legacy_imports(self):
        for file in ("app/application/normal_purchases.py", "app/repositories/supabase/normal_purchases.py",
                     "app/domain/normal_purchases.py", "app/api/routes/purchases.py"):
            source = Path(file).read_text(encoding="utf-8")
            for forbidden in ("streamlit", "storage_shop", "conex_pkhex", "discord_notify", "money_breakdown"):
                self.assertNotIn(forbidden, source)
        sql = Path("supabase/v2/migrations/021_normal_purchase_api.sql").read_text(encoding="utf-8").lower()
        for forbidden in ("security definer", "create policy", "update public.trainers", "insert into public.redemptions", "update public.save_files"):
            self.assertNotIn(forbidden, sql)
        self.assertIn("coalesce(sum(amount), 0)", sql)
        self.assertIn("for update", sql)
        self.assertIn("set search_path = ''", sql)
