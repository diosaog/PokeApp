"""Trust-boundary unit checks; native byte and SQL evidence lives in the local gate."""

import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.application.item_use_verification import (
    TrustedItemUseVerification,
    VerificationRejected,
)
from app.domain.pokemon_identity import trusted_native_identity
from app.launcher.item_use import EngineeringItemUse
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import PRODUCTION_MUTATIONS
from app.save_parser.models import ParsedTrainer
from app.save_parser.writer import NATIVE_SIZES
from app.save_parser.xy_identity import ObservedXYIdentity


class ReviveVerificationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(UTC)
        self.source = bytes(NATIVE_SIZES["X"])
        self.result = b"\x01" + self.source[1:]
        self.t = ParsedTrainer(name="Fixture", tid=1, sid=2, gender=0, language=2)
        identity = ObservedXYIdentity(
            1,
            6,
            123,
            1,
            2,
            24,
            2,
            "Fixture",
            0,
            met_location=1,
            met_level=5,
            egg_location=0,
            met_date="2020-01-01",
            encryption_constant=456,
            ivs=(1,) * 6,
        )
        self.p = SimpleNamespace(identity=identity, is_egg=False)
        self.obs = SimpleNamespace(
            game="X",
            trainer=self.t,
            boxes=[SimpleNamespace(number=b, slots=[None] * 30) for b in range(1, 9)],
            occupied=lambda: [(None, self.p)],
        )
        self.obs.boxes[7].slots[0] = self.p
        e = trusted_native_identity(identity, trainer=self.t, is_egg=False)
        a = {
            key: str(uuid4())
            for key in (
                "id",
                "season_id",
                "trainer_id",
                "purchase_id",
                "claim_id",
                "operation_id",
                "save_file_id",
                "identity_revision_id",
                "target_pokemon_entity_id",
            )
        }
        a.update(
            effect_code="revive",
            status="PENDING_APPLICATION",
            save_sha256=sha256(self.source).hexdigest(),
            expires_at=(self.now + timedelta(minutes=10)).isoformat(),
        )
        self.a = a
        self.context = {
            "authorization": a,
            "entity": {
                "id": a["target_pokemon_entity_id"],
                "owner_trainer_id": a["trainer_id"],
                "season_id": a["season_id"],
                "identity_status": "unambiguous",
                "candidate_key": e.candidate_key,
            },
            "observation": {
                "pokemon_entity_id": a["target_pokemon_entity_id"],
                "revision_id": a["identity_revision_id"],
                "source": "box",
                "box_number": 8,
                "slot_number": 1,
                "outcome": "MATCHED",
                "evidence": asdict(e),
            },
            "save": {
                "id": a["save_file_id"],
                "trainer_id": a["trainer_id"],
                "season_id": a["season_id"],
                "sha256": a["save_sha256"],
                "metadata": {
                    "save_identity": {
                        "game": "X",
                        "trainer": self.t.model_dump(mode="json"),
                    }
                },
            },
            "trainer_enabled": True,
            "participant_active": True,
            "purchase_pending": True,
            "purchase_effect": "revive",
            "current_save_id": a["save_file_id"],
            "head_id": a["identity_revision_id"],
        }
        self.repo = Mock()
        self.repo.load.return_value = self.context
        self.repo.read_source.return_value = self.source
        self.parser = Mock()
        self.parser.parse.return_value = self.obs
        self.native = Mock()
        self.native.version = "fixture-native"
        self.service = TrustedItemUseVerification(
            self.repo, self.parser, self.native, now=lambda: self.now
        )

    def verify(self):
        a = self.a
        return self.service.verify(
            a["id"], a["season_id"], a["trainer_id"], a["claim_id"], self.result
        )

    def denied(self):
        with self.assertRaises(VerificationRejected):
            self.verify()
        self.repo.record_verified.assert_not_called()

    def test_server_derives_exact_plan_and_binds_entitlement_and_bytes(self):
        proof = self.verify()
        args = self.native.prepare.call_args.args
        self.assertEqual(args[0], self.source)
        self.assertEqual(
            args[1].mutation,
            {
                "kind": "revive",
                "location": "box",
                "box_index": 7,
                "slot_index": 0,
                "target_pid": 123,
                "target_ec": 456,
                "destination_box_index": 0,
                "destination_slot_index": 0,
            },
        )
        self.native.verify.assert_called_once_with(
            self.source, self.result, args[1], self.native.prepare.return_value
        )
        self.assertEqual(proof["result_sha256"], sha256(self.result).hexdigest())
        self.assertEqual(proof["claim_id"], self.a["claim_id"])
        before = proof["plan_sha256"]
        self.a["purchase_id"] = str(uuid4())
        self.assertNotEqual(self.verify()["plan_sha256"], before)

    def test_all_authority_mismatches_fail_before_record(self):
        mutations = [
            ("authorization", "effect_code", "steal"),
            ("authorization", "status", "PREPARED"),
            ("authorization", "expires_at", self.now.isoformat()),
            ("entity", "id", str(uuid4())),
            ("entity", "owner_trainer_id", str(uuid4())),
            ("entity", "identity_status", "ambiguous"),
            ("entity", "candidate_key", "0" * 64),
            ("observation", "outcome", "AMBIGUOUS"),
            ("observation", "box_number", 1),
            ("observation", "revision_id", str(uuid4())),
            ("save", "trainer_id", str(uuid4())),
            ("save", "sha256", "f" * 64),
            ("save", "metadata", {}),
        ]
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                previous = self.context[section][key]
                self.context[section][key] = value
                self.denied()
                self.context[section][key] = previous
        for key, value in (
            ("trainer_enabled", False),
            ("participant_active", False),
            ("purchase_pending", False),
            ("current_save_id", str(uuid4())),
            ("head_id", str(uuid4())),
        ):
            with self.subTest(key=key):
                before = self.context[key]
                self.context[key] = value
                self.denied()
                self.context[key] = before

    def test_native_denial_cannot_record_proof(self):
        self.native.verify.side_effect = ValueError("synthetic invalid native output")
        with self.assertRaises(ValueError):
            self.verify()
        self.repo.record_verified.assert_not_called()

    def test_parser_denial_cannot_record_proof(self):
        self.parser.parse.side_effect = [self.obs, ValueError("bad result")]
        with self.assertRaises(ValueError):
            self.verify()
        self.repo.record_verified.assert_not_called()

    def test_hash_must_match_retained_server_source(self):
        self.repo.read_source.return_value = self.result
        self.denied()

    def test_incomplete_or_changed_identity_is_not_reconstructed(self):
        self.p.identity = replace(self.p.identity, met_date=None)
        self.denied()

    def test_clone_identifier_rejected(self):
        self.obs.occupied = lambda: [(None, self.p), (None, self.p)]
        self.denied()

    def test_egg_rejected(self):
        self.p.is_egg = True
        self.denied()

    def test_no_empty_slot_rejected(self):
        for box in self.obs.boxes[:7]:
            box.slots = [self.p] * 30
        self.denied()

    def test_destination_is_first_available_not_client_chosen(self):
        self.obs.boxes[0].slots = [self.p] * 30
        self.obs.boxes[1].slots[0] = self.p
        intent = self.service.plan(
            self.a["id"], self.a["season_id"], self.a["trainer_id"]
        )
        self.assertEqual(
            (
                intent.mutation["destination_box_index"],
                intent.mutation["destination_slot_index"],
            ),
            (1, 1),
        )
        self.assertIn("Caja 2, posición 2", LocalWriteController._describe(intent))
        # Revive is not a production mutation; only the owner's enabled kinds
        # are (072 adds the coordinated Shop delivery, deliver_item).
        self.assertEqual(
            PRODUCTION_MUTATIONS,
            {"add_item", "deliver_item", "transfer_remove", "transfer_insert"},
        )

    def test_wrong_claim_and_bare_client_receipt_denied(self):
        a = self.a
        with self.assertRaises(VerificationRejected):
            self.service.verify(
                a["id"], a["season_id"], a["trainer_id"], str(uuid4()), self.result
            )
        with self.assertRaises(VerificationRejected):
            self.service.verify(
                a["id"],
                a["season_id"],
                a["trainer_id"],
                a["claim_id"],
                {
                    "status": "APPLIED_VERIFIED",
                    "sha256": sha256(self.result).hexdigest(),
                },
            )
        self.repo.record_verified.assert_not_called()

    def test_cas_conflict_propagates_without_success(self):
        self.repo.record_verified.side_effect = VerificationRejected("CONTEXT_CHANGED")
        with self.assertRaises(VerificationRejected):
            self.verify()

    def test_055_only_disambiguates_variable_preserving_policy(self):
        root = Path(__file__).resolve().parents[1] / "supabase/v2/migrations"
        old = (root / "048_trusted_gen67_identity.sql").read_text(encoding="utf-8")
        start = old.index(
            "create or replace function public.commit_pokemon_identity_v038"
        )
        old = old[start : old.index("end $$;", start) + len("end $$;")]
        new = (root / "055_native_identity_evidence_scope.sql").read_text(
            encoding="utf-8"
        )
        start = new.index(
            "create or replace function public.commit_pokemon_identity_v038"
        )
        new = new[start : new.index("end $$;", start) + len("end $$;")]
        self.assertEqual(new.replace("v_evidence", "evidence"), old)


class ReviveBindingTests(unittest.TestCase):
    def test_multiple_pending_bindings_cannot_release_sync_early(self):
        from test_phase22_write_engine import engine_at, intent

        with tempfile.TemporaryDirectory(prefix="pokeapp-23c-bindings-") as temp:
            root = Path(temp)
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(root / "main"), engine_at(root)
            )
            service = EngineeringItemUse(
                controller,
                Mock(),
                season_id="fixture-season",
                trainer_id="fixture-trainer",
            )
            a = {
                k: str(uuid4())
                for k in (
                    "id",
                    "operation_id",
                    "purchase_id",
                    "target_pokemon_entity_id",
                    "save_file_id",
                    "identity_revision_id",
                )
            }
            a.update(
                season_id="fixture-season",
                trainer_id="fixture-trainer",
                effect_code="revive",
                status="PREPARED",
                save_sha256=intent().expected_sha256,
                expires_at=(datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            )
            service.bind_fixture(
                a, intent(), pokemon_entity_id=a["target_pokemon_entity_id"]
            )
            b = a | {
                "id": str(uuid4()),
                "operation_id": str(uuid4()),
                "purchase_id": str(uuid4()),
            }
            second_intent = replace(
                intent(), mutation=intent().mutation | {"new_value": 2}
            )
            service.bind_fixture(
                b, second_intent, pokemon_entity_id=b["target_pokemon_entity_id"]
            )
            _, r = service._load(a["id"])
            service._state(a["id"], r, "APPLIED_VERIFIED")
            self.assertTrue(controller.gate.recovery_required)
            _, r = service._load(b["id"])
            service._state(b["id"], r, "APPLIED_VERIFIED")
            self.assertFalse(controller.gate.recovery_required)

    def test_revive_requires_exact_effect_and_scope_and_production_remains_disabled(
        self,
    ):
        from test_phase22_write_engine import SOURCE, engine_at, intent

        from app.launcher.write_files import WriteSafetyError

        with tempfile.TemporaryDirectory(prefix="pokeapp-23c-disabled-") as temp:
            root = Path(temp)
            target = root / "main"
            target.write_bytes(SOURCE)
            native_intent = replace(intent(), mutation={"kind": "revive"})
            prod = engine_at(root, enabled=False)
            with self.assertRaises(WriteSafetyError):
                prod.prepare(
                    prod.enroll(target), native_intent, closed_emulator_confirmed=True
                )
            self.assertEqual(target.read_bytes(), SOURCE)
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine_at(root)
            )
            bridge = EngineeringItemUse(
                controller, Mock(), season_id="a", trainer_id="b"
            )
            with self.assertRaises(WriteSafetyError):
                bridge.bind_revive(
                    {"effect_code": "steal"}, native_intent, pokemon_entity_id="x"
                )
