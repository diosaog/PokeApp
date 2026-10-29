"""072 server side: the use contract, the Launcher delivery routes, the
purchase guard and the reads. Fakes only (refunds: 062 incident center)."""

import re
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_enabled_principal
from app.domain.shop_item_uses import (
    BAG_ITEMS,
    GAMES,
    GEN7,
    SHOP_USES,
    deliverable,
    describe_use,
    purchase_refusal,
    use_of,
)
from app.repositories.errors import ItemDeliveryRejectedError, PersistenceError
from app.repositories.supabase.item_delivery import SupabaseItemDeliveryRepository

ROOT = Path(__file__).resolve().parents[1]
TRAINER = str(uuid4())
SAVE_TRAINER = {"name": "Samu", "tid": 123, "sid": 456, "gender": 0, "language": 7}


def native_key(game="US"):
    return sha256("\0".join((game, "Samu", "123", "456", "0", "7")).encode()).hexdigest()


class ContractTests(unittest.TestCase):
    def test_every_object_use_names_a_writable_object(self):
        for code, use in SHOP_USES.items():
            for item in use.get("items", ()):
                self.assertIn(item, BAG_ITEMS, code)

    def test_native_whitelist_equals_the_contract(self):
        source = (ROOT / "companion/parser/PokeApp.Parser/NativeItems.cs").read_text("utf-8")
        block = source.split("ShopItems = new Dictionary<string, ushort>", 1)[1].split("};", 1)[0]
        native = {name: int(value) for name, value in re.findall(r'\["([a-z0-9_]+)"\] = (\d+)', block)}
        self.assertEqual({code: item[0] for code, item in BAG_ITEMS.items()}, native)

    def test_bottle_cap_is_gen7_only_and_refused_for_pokemon_y(self):
        self.assertEqual(GEN7, use_of("chapa_plateada")["games"])
        self.assertEqual("ITEM_INCOMPATIBLE_WITH_GAME", purchase_refusal("chapa_plateada", "Y"))
        self.assertIsNone(purchase_refusal("chapa_plateada", "US"))
        # No accepted save yet: the delivery checks the real save later.
        self.assertIsNone(purchase_refusal("chapa_plateada", None))
        view = describe_use("chapa_plateada", "Y")
        self.assertEqual((False, "ITEM_INCOMPATIBLE_WITH_GAME"), (view["compatible"], view["reason"]))
        self.assertEqual([{"code": "bottle_cap", "name": "Chapa Plateada", "item_id": 795, "games": list(GEN7)}], view["options"])

    def test_modes_keep_comodines_and_permissions_apart(self):
        for code in ("blindar_pokemon", "robar_pokemon", "revivir_pokemon", "robbery_shield_voucher"):
            self.assertEqual("pokemon", use_of(code)["mode"])
            self.assertEqual((), deliverable(code, "Y"))
        self.assertEqual("permission", use_of("captura_extra")["mode"])
        self.assertEqual("unavailable", use_of("menta_naturaleza")["mode"])
        self.assertEqual("ITEM_NOT_USABLE", purchase_refusal("menta_naturaleza", None))
        self.assertEqual("unknown", use_of("added_later_by_an_admin")["mode"])

    def test_choice_families_offer_only_what_the_game_holds(self):
        evolution = deliverable("objeto_evolutivo", "Y")
        self.assertNotIn("ice_stone", evolution)
        self.assertIn("ice_stone", deliverable("objeto_evolutivo", "UM"))
        self.assertEqual(18, len(deliverable("gemas_elementales", "X")))
        self.assertEqual(set(GAMES), set(use_of("fosil")["games"]))


class Repo:
    """In-memory stand-in for the 072 service-role transport."""

    def __init__(self):
        self.calls = []
        self.codes = {}
        self.listing = []
        self.live = []
        self.reject = None

    def purchase_code(self, sid, tid, pid):
        return self.codes.get(pid)

    def purchases(self, sid, tid):
        return self.listing

    def deliveries(self, sid, tid):
        return self.live

    def _receipt(self, name, *args):
        self.calls.append((name, args))
        if self.reject:
            raise self.reject
        return {
            "delivery_id": str(uuid4()),
            "purchase_id": str(uuid4()),
            "season_id": str(uuid4()),
            "trainer_id": TRAINER,
            "operation_id": str(uuid4()),
            "kind": "bag",
            "item_code": "bottle_cap",
            "game_item_id": 795,
            "game": "US",
            "status": "RESERVED",
            "reserved_at": "2026-10-29T12:00:00+00:00",
            "finished_at": None,
            "purchase_status": "pending",
        }

    def reserve(self, *args):
        return self._receipt("reserve", *args)

    def complete(self, *args):
        return self._receipt("complete", *args)

    def release(self, *args):
        return self._receipt("release", *args)

    def use_permission(self, *args):
        return self._receipt("use_permission", *args)

    def item_code(self, item_id):
        return self.codes.get(item_id)

    def promotion_item_code(self, sid, promotion_id):
        return self.codes.get(promotion_id)


class Reads:
    """league_game: season_players.current_save_file_id -> save identity."""

    def __init__(self, game):
        self.game = game
        self.trainer = dict(SAVE_TRAINER)
        self.error = None
        self.filters = []

    def rows(self, table, columns, filters=None, limit=None, offset=None, order=None):
        if self.error:
            raise self.error
        self.filters.append((table, filters))
        if table == "season_players":
            return [{"current_save_file_id": "save-1" if self.game else None}]
        if table == "save_files":
            return [{"metadata": {"save_identity": {"game": self.game, "trainer": self.trainer}}}]
        return []


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.purchases = Mock()
        self.reads = Reads("US")
        self.container = ApiContainer(
            item_delivery_repository=self.repo,
            frontend_read_repository=self.reads,
            purchase_repository=self.purchases,
        )
        self.app = create_app(container=self.container, config=APIConfig())
        self.app.dependency_overrides[require_enabled_principal] = lambda: AuthenticatedPrincipal(
            trainer_id=TRAINER, display_name="Samu", is_admin=False, globally_enabled=True
        )
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.sid, self.pid, self.op = str(uuid4()), str(uuid4()), str(uuid4())
        self.base = f"/v1/launcher/seasons/{self.sid}/deliveries"

    def reserve(self, item="bottle_cap", game="US", code="chapa_plateada"):
        self.repo.codes[self.pid] = code
        return self.client.put(
            f"{self.base}/{self.op}", json={"purchase_id": self.pid, "item": item, "game": game}
        )

    def test_reserve_uses_the_server_contract_not_the_client(self):
        response = self.reserve()
        self.assertEqual(200, response.status_code, response.text)
        name, args = self.repo.calls[-1]
        self.assertEqual("reserve", name)
        self.assertEqual((self.sid, TRAINER, self.pid, self.op, "bottle_cap", 795, "US"), args)
        self.assertEqual(native_key(), response.json()["authorized_trainer_key"])
        self.assertIn(("save_files", {"id": "save-1", "season_id": self.sid, "trainer_id": TRAINER}), self.reads.filters)

    def test_reservation_requires_a_complete_server_accepted_save_identity(self):
        self.reads.game = None
        response = self.reserve()
        self.assertEqual((409, "DELIVERY_SAVE_NOT_BOUND"), (response.status_code, response.json()["detail"]["code"]))
        self.reads.game = "US"
        self.reads.trainer.pop("tid")
        response = self.reserve()
        self.assertEqual((503, "ITEM_DELIVERY_UNAVAILABLE"), (response.status_code, response.json()["detail"]["code"]))
        self.assertEqual([], self.repo.calls)

    def test_unavailable_save_read_never_skips_purchase_compatibility(self):
        self.reads.error = PersistenceError("offline")
        item = str(uuid4())
        self.repo.codes[item] = "chapa_plateada"
        response = self.client.post(
            f"/v1/seasons/{self.sid}/shop/purchases", json={"item_id": item}, headers={"Idempotency-Key": "k"}
        )
        self.assertEqual((503, "ITEM_DELIVERY_UNAVAILABLE"), (response.status_code, response.json()["detail"]["code"]))
        self.purchases.assert_not_called()

    def test_reserve_refusals(self):
        cases = (
            ({"item": "leftovers"}, 409, "DELIVERY_ITEM_NOT_OFFERED"),
            ({"game": "Y"}, 409, "ITEM_INCOMPATIBLE_WITH_GAME"),
            ({"code": "blindar_pokemon", "item": "bottle_cap"}, 409, "DELIVERY_NOT_SUPPORTED"),
            ({"code": "captura_extra"}, 409, "DELIVERY_NOT_SUPPORTED"),
        )
        for kwargs, status, code in cases:
            with self.subTest(kwargs=kwargs):
                response = self.reserve(**kwargs)
                self.assertEqual(status, response.status_code, response.text)
                self.assertEqual(code, response.json()["detail"]["code"])
        self.assertEqual([], self.repo.calls)
        unknown = self.client.put(
            f"{self.base}/{self.op}", json={"purchase_id": str(uuid4()), "item": "bottle_cap", "game": "US"}
        )
        self.assertEqual(404, unknown.status_code)

    def test_the_object_goes_to_the_league_save_only(self):
        self.reads.game = "SN"
        response = self.reserve(item="sitrus_berry", game="US", code="baya_zidra")
        self.assertEqual(409, response.status_code)
        self.assertEqual("DELIVERY_OTHER_GAME", response.json()["detail"]["code"])

    def test_body_is_strict(self):
        self.repo.codes[self.pid] = "chapa_plateada"
        for body in (
            {"purchase_id": self.pid, "item": "bottle_cap", "game": "US", "game_item_id": 1},
            {"purchase_id": self.pid, "item": "BAD", "game": "US"},
            {"purchase_id": self.pid, "item": "bottle_cap", "game": "SW"},
        ):
            self.assertEqual(422, self.client.put(f"{self.base}/{self.op}", json=body).status_code)
        self.assertEqual(
            422,
            self.client.put(
                f"{self.base}/{self.op}/complete", json={"source_sha256": "a" * 64, "output_sha256": "B" * 64}
            ).status_code,
        )
        self.assertEqual(422, self.client.put(f"{self.base}/{self.op}/release", json={"x": 1}).status_code)

    def test_complete_release_and_rejections_map(self):
        ok = self.client.put(
            f"{self.base}/{self.op}/complete", json={"source_sha256": "a" * 64, "output_sha256": "b" * 64}
        )
        self.assertEqual(200, ok.status_code, ok.text)
        self.assertEqual(("complete", (self.sid, TRAINER, self.op, "a" * 64, "b" * 64)), self.repo.calls[-1])
        self.assertEqual(200, self.client.put(f"{self.base}/{self.op}/release", json={}).status_code)
        self.repo.reject = ItemDeliveryRejectedError("DELIVERY_NOT_FOUND", 404)
        missing = self.client.put(f"{self.base}/{self.op}/release", json={})
        self.assertEqual((404, "DELIVERY_NOT_FOUND"), (missing.status_code, missing.json()["detail"]["code"]))
        self.repo.reject = PersistenceError("down")
        self.assertEqual(503, self.client.put(f"{self.base}/{self.op}/release", json={}).status_code)

    def test_listing_offers_pending_objects_with_their_options(self):
        paid = str(uuid4())
        self.repo.listing = [
            {"id": paid, "status": "pending", "code": "objeto_evolutivo", "name": "Objeto Evolutivo"},
            {"id": str(uuid4()), "status": "used", "code": "baya_zidra", "name": "Baya Zidra"},
            {"id": str(uuid4()), "status": "pending", "code": "blindar_pokemon", "name": "Blindar"},
            {"id": str(uuid4()), "status": "pending", "code": "captura_extra", "name": "Captura Extra"},
        ]
        self.repo.live = [{"purchase_id": paid, "operation_id": self.op, "item_code": "ice_stone", "game": "US", "status": "RESERVED"}]
        body = self.client.get(self.base).json()
        self.assertEqual("US", body["league_game"])
        self.assertEqual([paid], [i["purchase_id"] for i in body["items"]])
        item = body["items"][0]
        self.assertEqual("choice", item["mode"])
        self.assertEqual(27, len(item["options"]))
        self.assertEqual({"operation_id": self.op, "item_code": "ice_stone", "game": "US"}, item["reserved"])

    def test_captura_extra_use_is_one_operation_per_key(self):
        path = f"/v1/seasons/{self.sid}/shop/purchases/{self.pid}/use"
        self.assertEqual(200, self.client.post(path, headers={"Idempotency-Key": "k1"}).status_code)
        self.assertEqual(200, self.client.post(path, headers={"Idempotency-Key": "k1"}).status_code)
        first, second = (call[1][3] for call in self.repo.calls[-2:])
        self.assertEqual(first, second)
        self.assertEqual(str(uuid5(NAMESPACE_URL, f"pokeapp:item-use:{TRAINER}:{self.pid}:k1")), first)
        self.assertEqual(422, self.client.post(path).status_code)

    def test_purchase_guard_refuses_what_cannot_be_used(self):
        item = str(uuid4())
        path = f"/v1/seasons/{self.sid}/shop/purchases"
        self.reads.game = "Y"
        for code, reason in (("chapa_plateada", "ITEM_INCOMPATIBLE_WITH_GAME"), ("menta_naturaleza", "ITEM_NOT_USABLE")):
            with self.subTest(code=code):
                self.repo.codes[item] = code
                response = self.client.post(path, json={"item_id": item}, headers={"Idempotency-Key": "k"})
                self.assertEqual(409, response.status_code)
                self.assertEqual(reason, response.json()["detail"]["code"])
        self.purchases.assert_not_called()


class TransportTests(unittest.TestCase):
    def test_rpc_rejections_are_whitelisted(self):
        class Failure(Exception):
            def __init__(self, message, code):
                self.message, self.code = message, code

        client = Mock()
        repo = SupabaseItemDeliveryRepository(client)
        client.rpc.return_value.execute.side_effect = Failure("delivery_in_progress", "PT409")
        with self.assertRaises(ItemDeliveryRejectedError) as caught:
            repo.reserve("s", "t", "p", "o", "bottle_cap", 795, "US")
        self.assertEqual(("DELIVERY_IN_PROGRESS", 409), (caught.exception.code, caught.exception.status))
        client.rpc.return_value.execute.side_effect = Failure("delivery_in_progress", "PT500")
        with self.assertRaises(PersistenceError):
            repo.release("s", "t", "o")
        client.rpc.return_value.execute.side_effect = Failure("something else", "PT409")
        with self.assertRaises(PersistenceError):
            repo.complete("s", "t", "o", "a" * 64, "b" * 64)


if __name__ == "__main__":
    unittest.main()
