"""Virtual consumables trust boundary. Synthetic bytes; native matrix is separate."""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_enabled_principal
from app.application.save_ingestion import parsed_payload, registration_request
from app.application.frontend_reads import FrontendReads
from app.application.training import EFFECTS, VirtualTraining
from app.domain.pokemon_identity import digest, trusted_native_identity
from app.domain.shop_item_uses import GAMES, deliverable, describe_use, purchase_refusal
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.models import ObservedSave
from test_phase21_identity import TRAINER, neutral
from test_phase21_progress import payload

SID, TID, OLD_SID, PID, OP = (str(uuid4()) for _ in range(5))
VERSION = "pokeapp-reader/3;pkhex/24.11.11"
SOURCE, OUTPUT = b"source virtual training fixture", b"output virtual training fixture"


def observation(ivs=(17, 2, 3, 4, 5, 6), nature=0, game="Y"):
    value = payload(game)
    value["trainer"] = dict(TRAINER)
    value["party"][0]["identity"] = asdict(neutral(ivs=ivs))
    value["party"][0].update(ivs=list(ivs), nature_id=nature)
    for box in value["boxes"]:
        box["slots"] = [None] * 30
    return ObservedSave.model_validate_json(json.dumps(value))


def context_fixture():
    observed = observation()
    source_hash = sha256(SOURCE).hexdigest()
    initial = registration_request(SID, TID, source_hash, None, observed, VERSION, {"head": None, "entities": []})
    binding = initial["identity_plan"]["bindings"][0]
    head = {"id": str(uuid4()), "capture_stream_id": str(uuid4()), "capture_sequence": 1}
    entity = {"id": binding["pokemon_entity_id"], "initial_evidence": binding["evidence"], "candidate_key": binding["candidate_key"], "identity_status": "unambiguous"}
    return {
        "save": {"id": initial["save_id"], "sha256": source_hash}, "revision": head,
        "payload": initial["payload"], "observations": [{"pokemon_entity_id": entity["id"], "source": "party", "box_number": 0, "slot_number": 1}],
        "purchases": [{"purchase_id": PID, "purchase_season_id": OLD_SID, "item_code": "chapa_plateada", "name": "Chapa Plateada"}],
        "operations": [], "registration": {"head": head, "entities": [entity]},
    }


def receipt(context, status="RESERVED"):
    return {"operation_id": OP, "season_id": SID, "trainer_id": TID, "purchase_id": PID, "purchase_season_id": OLD_SID,
        "pokemon_entity_id": context["observations"][0]["pokemon_entity_id"], "save_file_id": context["save"]["id"],
        "identity_revision_id": context["revision"]["id"], "status": status,
        "intent": {"game": "Y", "expected_sha256": context["save"]["sha256"], "trainer_key": "a" * 64,
            "mutation": {"kind": "virtual_training", "item_code": "chapa_plateada", "attempt": OP, "location": "party", "box_index": None,
            "slot_index": 0, "expected_pokemon_sha256": "b" * 64, "expected_nature": 0, "expected_ivs": [17, 2, 3, 4, 5, 6], "nature_id": None, "stat": "hp"}},
        "reserved_at": "2026-11-01T00:00:00+00:00", "finished_at": None, "result": None}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.context = context_fixture()
        self.repo = Mock()
        self.repo.read_source.return_value = SOURCE
        self.native = Mock()
        self.native.inspect_training.return_value = {"source_sha256": self.context["save"]["sha256"], "game": "Y", "trainer_key": "a" * 64,
            "pokemon_sha256": "b" * 64, "nature": 0, "ivs": [17, 2, 3, 4, 5, 6], "is_egg": False}
        self.parser = Mock(version=VERSION)
        self.parser.parse.return_value = observation(ivs=(31, 2, 3, 4, 5, 6))
        self.service = VirtualTraining(self.repo, self.parser, self.native)
        self.current = None

        def execute(op, sid, tid, **values):
            if op == "context": return deepcopy(self.context)
            if op == "load": return deepcopy(self.current)
            if op == "reserve":
                self.current = receipt(self.context)
                self.current["intent"] = values.get("intent", self.current["intent"])
                return deepcopy(self.current)
            if op == "complete": return receipt(self.context, "APPLIED")
            raise AssertionError(op)

        self.repo.execute.side_effect = execute
        self.body = {"purchase_id": PID, "pokemon_entity_id": self.context["observations"][0]["pokemon_entity_id"],
                     "source_sha256": self.context["save"]["sha256"], "change": {"kind": "iv", "nature_id": None, "stat": "hp"}}

    def test_all_three_virtual_purchases_are_supported_in_all_eight_games_not_bag(self):
        for code, effect in EFFECTS.items():
            for game in GAMES:
                self.assertIsNone(purchase_refusal(code, game))
                self.assertEqual((), deliverable(code, game))
                view = describe_use(code, game)
                self.assertEqual(("training", effect, True, []), (view["mode"], view["training_effect"], view["compatible"], view["options"]))

    def test_listing_is_read_only_and_surfaces_old_purchase_with_original_season(self):
        data = self.service.listing(SID, TID)
        self.assertEqual(OLD_SID, data["items"][0]["purchase_season_id"])
        self.assertEqual({"hp": 17, "atk": 2, "defense": 3, "spa": 4, "spd": 5, "spe": 6}, data["targets"][0]["pokemon"]["ivs"])
        self.repo.read_source.assert_not_called()
        self.native.prepare.assert_not_called()
        self.assertEqual(["context"], [c.args[0] for c in self.repo.execute.call_args_list])

    def test_reservation_derives_slot_identity_and_values_from_server_bytes(self):
        result = self.service.reserve(SID, TID, OP, self.body)
        m = result["intent"]["mutation"]
        self.assertEqual(("party", None, 0, "b" * 64, [17, 2, 3, 4, 5, 6]),
                         (m["location"], m["box_index"], m["slot_index"], m["expected_pokemon_sha256"], m["expected_ivs"]))
        self.assertEqual("chapa_plateada", m["item_code"])
        self.assertEqual(OP, m["attempt"])
        self.native.prepare.assert_called_once()
        self.repo.store_raw.assert_not_called()

    def test_a_fresh_confirmation_on_unchanged_source_gets_a_new_local_operation_uuid(self):
        from app.save_parser.write_models import WriteIntent
        first = self.service.reserve(SID, TID, OP, self.body)
        # The previous reservation was safely released without any write. A
        # fresh confirmation must not replay its rejected local engine journal.
        self.current = None
        second_id = str(uuid4())
        second = self.service.reserve(SID, TID, second_id, self.body)
        self.assertNotEqual(WriteIntent.create(**first["intent"]).operation_id,
                            WriteIntent.create(**second["intent"]).operation_id)
        self.assertEqual(second_id, second["intent"]["mutation"]["attempt"])

    def test_stale_unauthorized_and_noop_never_reserve_or_consume(self):
        cases = [(dict(self.body, source_sha256="c" * 64), "TRAINING_SOURCE_CHANGED"),
                 (dict(self.body, pokemon_entity_id=str(uuid4())), "TRAINING_TARGET_UNAVAILABLE"),
                 (dict(self.body, purchase_id=str(uuid4())), "TRAINING_PURCHASE_UNAVAILABLE"),
                 (dict(self.body, change={"kind": "nature", "nature_id": 1, "stat": None}), "TRAINING_CHANGE_NOT_OFFERED")]
        for body, code in cases:
            with self.subTest(code=code), self.assertRaises(SeasonAdminRejected) as caught:
                self.service.reserve(SID, TID, OP, body)
            self.assertEqual(code, caught.exception.code)
        self.native.inspect_training.return_value["ivs"][0] = 31
        with self.assertRaises(SeasonAdminRejected) as caught:
            self.service.reserve(SID, TID, OP, self.body)
        self.assertEqual("TRAINING_NO_CHANGE", caught.exception.code)
        self.assertNotIn("reserve", [c.args[0] for c in self.repo.execute.call_args_list])

    def test_native_failed_output_never_registers_or_spends(self):
        self.current = receipt(self.context)
        self.native.verify.side_effect = ValueError("invalid output")
        with patch("app.save_parser.write_models.WriteIntent.create", return_value=SimpleNamespace(mutation=self.current["intent"]["mutation"])):
            with self.assertRaises(ValueError): self.service.complete(SID, TID, OP, OUTPUT)
        self.repo.store_raw.assert_not_called()
        self.assertNotIn("complete", [c.args[0] for c in self.repo.execute.call_args_list])

    def test_verified_result_preserves_entity_uuid_and_rekeys_only_authorized_ivs(self):
        self.current = receipt(self.context)
        self.native.prepare.return_value = SimpleNamespace(semantic_diff={"preserved_unrelated": True})
        with patch("app.save_parser.write_models.WriteIntent.create", return_value=SimpleNamespace(mutation=self.current["intent"]["mutation"])):
            result = self.service.complete(SID, TID, OP, OUTPUT)
        self.assertEqual("APPLIED", result["status"])
        self.native.verify.assert_called_once()
        args = self.repo.execute.call_args_list[-1].kwargs
        self.assertEqual([31, 2, 3, 4, 5, 6], list(args["after_evidence"]["ivs"]))
        b = args["registration"]["identity_plan"]["bindings"][0]
        self.assertEqual((self.current["pokemon_entity_id"], "MATCHED"), (b["pokemon_entity_id"], b["outcome"]))
        self.assertNotEqual(args["before_evidence"]["ivs"], args["after_evidence"]["ivs"])
        self.repo.store_raw.assert_called_once()

    def test_applied_retry_does_not_reparse_or_depend_on_old_current_source(self):
        self.current = receipt(self.context, "APPLIED")
        self.service.complete(SID, TID, OP, OUTPUT)
        self.repo.read_source.assert_not_called()
        self.native.prepare.assert_not_called()
        self.parser.parse.assert_not_called()
        self.assertEqual(["load", "complete"], [c.args[0] for c in self.repo.execute.call_args_list])

    def test_foreign_ot_proven_entity_retains_canonical_origin_through_two_trainings_and_sync(self):
        from app.save_parser.models import ParsedTrainer
        self.context["registration"]["proven_entity_ids"] = [self.context["observations"][0]["pokemon_entity_id"]]
        original = deepcopy(self.context["registration"]["entities"][0]["initial_evidence"])
        foreign_trainer = ParsedTrainer(name="Recipient", tid=99, sid=100, gender=1, language=2)
        self.native.prepare.return_value = SimpleNamespace(semantic_diff={"preserved_unrelated": True})
        for ivs in ((31, 2, 3, 4, 5, 6), (31, 31, 3, 4, 5, 6)):
            self.current = receipt(self.context)
            self.parser.parse.return_value = observation(ivs=ivs).model_copy(update={"trainer": foreign_trainer})
            with patch("app.save_parser.write_models.WriteIntent.create", return_value=SimpleNamespace(mutation=self.current["intent"]["mutation"])):
                self.service.complete(SID, TID, OP, OUTPUT)
            proof = self.repo.execute.call_args_list[-1].kwargs
            self.assertTrue(proof["after_evidence"]["source_trainer_match"])
            self.assertFalse(proof["observed_evidence"]["source_trainer_match"])
            self.assertEqual(original | {"ivs": tuple(ivs)}, proof["after_evidence"])
            self.assertEqual("MATCHED", proof["registration"]["identity_plan"]["bindings"][0]["outcome"])
            self.context["registration"]["entities"][0]["initial_evidence"] = proof["after_evidence"]
        future = registration_request(SID, TID, "f" * 64, self.current["save_file_id"],
            self.parser.parse.return_value, VERSION, self.context["registration"])
        self.assertEqual((self.current["pokemon_entity_id"], "MATCHED"),
            (future["identity_plan"]["bindings"][0]["pokemon_entity_id"], future["identity_plan"]["bindings"][0]["outcome"]))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.service = Mock()
        self.app = create_app(container=ApiContainer(training_service=self.service), config=APIConfig())
        self.app.dependency_overrides[require_enabled_principal] = lambda: AuthenticatedPrincipal(
            trainer_id=TID, display_name="Fixture", is_admin=False, globally_enabled=True)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.base = f"/v1/launcher/seasons/{SID}/training"
        self.service.reserve.return_value = receipt(context_fixture())

    def test_reserve_auth_scope_and_strict_change_contract(self):
        c = context_fixture()
        body = {"purchase_id": PID, "pokemon_entity_id": c["observations"][0]["pokemon_entity_id"],
                "source_sha256": c["save"]["sha256"], "change": {"kind": "iv", "stat": "hp"}}
        self.assertEqual(200, self.client.put(f"{self.base}/{OP}", json=body).status_code)
        self.assertEqual((SID, TID, OP), self.service.reserve.call_args.args[:3])
        for change in ({"kind": "nature", "nature_id": 25}, {"kind": "iv", "stat": "speed"},
                       {"kind": "ivs", "stat": "hp"}, {"kind": "nature"}, {"kind": "iv", "stat": "hp", "slot_index": 0}):
            self.assertEqual(422, self.client.put(f"{self.base}/{OP}", json=body | {"change": change}).status_code)
        self.assertEqual(422, self.client.put(f"{self.base}/{OP}", json=body | {"trainer_id": str(uuid4())}).status_code)

    def test_complete_requires_actual_bytes_not_client_hash_or_claim(self):
        path = f"{self.base}/{OP}/complete"
        self.service.complete.return_value = receipt(context_fixture(), "APPLIED")
        self.assertEqual(415, self.client.put(path, json={"output_sha256": "b" * 64}).status_code)
        self.assertEqual(422, self.client.put(path, content=b"", headers={"Content-Type": "application/octet-stream"}).status_code)
        self.assertEqual(200, self.client.put(path, content=OUTPUT, headers={"Content-Type": "application/octet-stream"}).status_code)
        self.assertEqual((SID, TID, OP, OUTPUT), self.service.complete.call_args.args)

    def test_all_routes_require_the_existing_authenticated_enabled_principal(self):
        self.app.dependency_overrides.clear()
        self.assertEqual(401, self.client.get(self.base).status_code)
        self.assertEqual(401, self.client.put(f"{self.base}/{OP}/release", json={}).status_code)
        self.service.release.assert_not_called()


class HistoricalInventoryTests(unittest.TestCase):
    def test_only_owned_pending_paid_virtual_purchases_cross_season_in_inventory(self):
        catalog = [{"id": str(uuid4()), "code": code, "name": code}
                   for code in (*EFFECTS, "restos")]
        purchases = []
        for item in catalog:
            purchases.append({"id": str(uuid4()), "shop_item_id": item["id"], "trainer_id": TID,
                "season_id": OLD_SID, "status": "pending", "acquisition_type": "paid",
                "total_price": 6, "purchased_at": "2026-10-29T12:00:00+00:00"})
        purchases.extend([dict(purchases[0], id=str(uuid4()), trainer_id=str(uuid4())),
                          dict(purchases[0], id=str(uuid4()), status="used"),
                          dict(purchases[0], id=str(uuid4()), acquisition_type="reward")])
        reserved = purchases[1]["id"]

        class Reads:
            def shield_targets(self, *args): return []
            def rows(self, table, columns, *, filters=None, **kwargs):
                rows = {"purchases": purchases, "shop_items": catalog,
                        "training_operations": [{"purchase_id": reserved, "trainer_id": TID, "status": "RESERVED"}]}.get(table, [])
                return [deepcopy(row) for row in rows if all(row.get(k) == v for k, v in (filters or {}).items())]

        read = FrontendReads(Reads())
        read.season = lambda sid: {"current_matchday_id": None}
        read._pc = lambda sid, tid: SimpleNamespace(pokemon=[])
        read.league_game = lambda sid, tid: "Y"
        result = read.inventory(SID, TID)
        self.assertEqual(set(EFFECTS), {p.item_code for p in result.purchases})
        self.assertEqual({OLD_SID}, {str(p.purchase_season_id) for p in result.purchases})
        self.assertEqual({"training"}, {p.use.mode for p in result.purchases})
        self.assertEqual("RESERVED", next(p for p in result.purchases if str(p.id) == reserved).training_status)


if __name__ == "__main__": unittest.main()
