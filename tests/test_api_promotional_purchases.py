from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.domain.promotional_purchases import PromotionalPurchaseReceipt, PromotionalPurchaseRequest
from app.repositories.supabase.normal_purchases import REJECTIONS
import test_api_purchases as normal


class PromotionalPurchaseTests(unittest.TestCase):
    def setUp(self):
        normal.NormalPurchaseTests.setUp(self)
        self.promotion = str(uuid4())
        self.receipt = PromotionalPurchaseReceipt(**asdict(self.receipt), promotion_id=self.promotion,
                                                 base_price=12, promotion_kind="normal", remaining_stock=1)
        self.rpc_body = asdict(self.receipt)
        self.container = replace(self.container, promotional_purchase_repository=self.repo)
        self.client = TestClient(create_app(container=self.container))
        self.addCleanup(self.client.close)
        self.path = f"/v1/seasons/{self.season}/shop/promotions/{self.promotion}/purchases"

    def post(self, body=None, headers=None):
        return self.client.post(self.path, json={} if body is None else body,
            headers=headers if headers is not None else {"Authorization": "Bearer dummy", "Idempotency-Key": "promo-key"})

    def test_e01_missing_bearer(self):
        self.assertEqual(self.post(headers={"Idempotency-Key": "x"}).status_code, 401)
        self.assertEqual(self.requests, [])

    def test_e02_invalid_bearer(self):
        self.verifier.fail = InvalidSessionError()
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.requests, [])

    def test_e03_disabled_admin(self):
        self.principals.trainer = replace(self.principals.trainer, globally_enabled=False)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.requests, [])

    def test_e14_to_e21_receipt_and_authoritative_request(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        expected = asdict(self.receipt)
        expected["purchased_at"] = "2026-09-22T12:00:00Z"
        self.assertEqual(response.json(), expected)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.url.path, "/rest/v1/rpc/api_create_promotional_purchase")
        self.assertEqual(json.loads(request.content), {
            "p_season_id": self.season, "p_trainer_id": self.receipt.trainer_id,
            "p_promotion_id": self.promotion, "p_idempotency_key": "promo-key",
        })

    def test_e04_to_e13_e35_to_e38_whitelisted_errors(self):
        for code, status in REJECTIONS.items():
            with self.subTest(code=code):
                self.rpc_status = status
                self.rpc_body = {"code": f"PT{status}", "message": code, "details": "SECRET SQL", "hint": "SECRET"}
                response = self.post()
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["code"], code.upper())
                self.assertNotIn("SECRET", response.text)

    def test_e15_e16_e28_body_cannot_choose_item_or_economy(self):
        for field in ("item_id", "promotion_id", "price", "discount", "quantity", "trainer_id", "stock",
                      "balance", "status", "season_player_id", "jornada", "promotion_price", "event_payload", "confirm_base_price"):
            with self.subTest(field=field):
                self.assertEqual(self.post({field: "forbidden"}).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_empty_object_required(self):
        for body in ([], "", 1, True):
            self.assertEqual(self.post(body).status_code, 422)
        self.assertEqual(self.client.post(self.path, headers={"Authorization": "Bearer dummy", "Idempotency-Key": "key"}).status_code, 422)

    def test_shared_key_validation(self):
        for key in (None, "", "has space", "x" * 129):
            headers = {"Authorization": "Bearer dummy"}
            if key is not None:
                headers["Idempotency-Key"] = key
            self.assertEqual(self.post(headers=headers).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_invalid_promotion_path(self):
        self.path = self.path.replace(self.promotion, "not-a-uuid")
        self.assertEqual(self.post().status_code, 422)
        self.assertEqual(self.requests, [])

    def test_e22_receipt_reused_without_extra_reads(self):
        self.assertEqual(self.post().json(), self.post().json())
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all("/rpc/" in str(r.url) for r in self.requests))

    def test_malformed_or_wrong_scope_receipt_fails_closed(self):
        original = asdict(self.receipt)
        for body in (None, [], {}, dict(original, promotion_id=str(uuid4())), dict(original, season_id=str(uuid4())),
                     dict(original, base_price=1), dict(original, remaining_stock=-1), dict(original, remaining_stock=True),
                     dict(original, promotion_kind="invented"), dict(original, quantity=2)):
            with self.subTest(body=body):
                self.rpc_body = body
                self.assertEqual(self.post().status_code, 503)

    def test_e49_unknown_errors_and_secrets_are_not_exposed(self):
        for code, message in (("23505", "SECRET SQL"), ("PT409", "SECRET"), ("XX000", "promotion_pending")):
            self.rpc_status, self.rpc_body = 500, {"code": code, "message": message, "details": "SECRET", "hint": None}
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("SECRET", response.text)

    def test_missing_backend(self):
        with TestClient(create_app(container=replace(self.container, promotional_purchase_repository=None))) as client:
            response = client.post(self.path, json={}, headers={"Authorization": "Bearer dummy", "Idempotency-Key": "key"})
            self.assertEqual(response.status_code, 503)

    def test_domain_shared_idempotency_validation(self):
        for key in ("", "bad\nkey", "x" * 129):
            with self.assertRaises(ValueError):
                PromotionalPurchaseRequest(self.season, self.receipt.trainer_id, self.promotion, key)

    def test_e50_e51_no_legacy_side_effect_imports(self):
        for name in ("app/application/promotional_purchases.py", "app/domain/promotional_purchases.py"):
            source = Path(name).read_text(encoding="utf-8")
            for forbidden in ("streamlit", "storage_shop", "conex_pkhex", "discord", "redemption"):
                self.assertNotIn(forbidden, source)

    def test_sql_security_wallet_first_and_unique_claim(self):
        sql = Path("supabase/v2/migrations/022_promotional_purchase_api.sql").read_text(encoding="utf-8").lower()
        body = sql.split("create or replace function public.api_create_promotional_purchase", 1)[1]
        self.assertIn("on public.purchases (promotion_id, trainer_id) where promotion_id is not null", sql)
        self.assertIn("security invoker set search_path = ''", body)
        self.assertLess(body.index("from public.season_players"), body.index("from public.shop_promotions"))
        self.assertIn("for update", body)
        self.assertNotIn("exception when", body)
        self.assertNotIn("create policy", sql)
        self.assertNotIn("insert into public.redemptions", sql)
