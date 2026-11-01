"""Malformed native receipts must not become authority for an edit.

Synthetic protocol envelopes only; the separate native matrix proves saves.
"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import Mock

from app.save_parser.native_sizes import NATIVE_SIZES
from app.save_parser.writer import NativeWriteError, PkhexProcessWriter
from app.save_parser.write_models import PreparedNative, WriteIntent


class TrainingNativeContractTests(unittest.TestCase):
    def proof_case(self):
        source = bytes(NATIVE_SIZES["Y"])
        output = b"x" + source[1:]
        mutation = dict(kind="virtual_training", item_code="menta_naturaleza",
                        attempt="a4740000-0000-4000-8000-000000000001", location="party",
                        box_index=None, slot_index=0, expected_nature=0, nature_id=1, stat=None,
                        expected_ivs=[1, 2, 3, 4, 5, 6], expected_pokemon_sha256="a" * 64)
        intent = WriteIntent.create(expected_sha256=sha256(source).hexdigest(), game="Y",
                                    trainer_key="b" * 64, mutation=mutation)
        diff = mutation | dict(preserved_unrelated=True, checksums_valid=True, signature_valid=True,
                               before_nature=0, after_nature=1, before_ivs=[1, 2, 3, 4, 5, 6],
                               after_ivs=[1, 2, 3, 4, 5, 6], target_pid=123, target_ec=456,
                               before_pokemon_sha256="a" * 64, after_pokemon_sha256="c" * 64,
                               legality_warnings_before=[], legality_warnings_after=[],
                               hidden_power_before=0, hidden_power_after=0)
        writer = object.__new__(PkhexProcessWriter)
        writer._run = Mock(return_value=dict(status="verified", game="Y", trainer_key="b" * 64,
            source_sha256=intent.expected_sha256, output_sha256=sha256(output).hexdigest(),
            output_base64=None, semantic_diff=deepcopy(diff)))
        # Historical recovery receipts intentionally omit candidate bytes.
        prepared = PreparedNative(output=b"", game="Y", trainer_key=intent.trainer_key,
            source_hash=intent.expected_sha256, output_hash=sha256(output).hexdigest(),
            semantic_diff=diff, contract={"schema_version": 1, "writer_version": writer.version})
        return writer, source, output, intent, prepared

    def test_legacy_vanilla_warnings_do_not_block_identical_verified_training(self):
        writer, source, output, intent, prepared = self.proof_case()
        prepared.semantic_diff["legality_warnings_before"] = ["Encounter|Invalid|Randomizer origin"]
        prepared.semantic_diff["legality_warnings_after"] = ["move:0|Invalid|Private modified move"]
        writer.verify(source, output, intent, prepared)
        writer._run.assert_called_once()

    def test_legacy_warning_compatibility_preserves_authoritative_proof_validation(self):
        writer, source, output, intent, prepared = self.proof_case()
        for key, value in (("target_pid", 124), ("target_ec", 457), ("after_nature", 2),
                           ("after_ivs", [31] * 6), ("after_pokemon_sha256", "d" * 64),
                           ("checksums_valid", False), ("signature_valid", 1),
                           ("preserved_unrelated", False),
                           ("expected_ivs", [True, 2, 3, 4, 5, 6])):
            with self.subTest(key=key):
                bad = deepcopy(prepared.semantic_diff) | {key: value}
                with self.assertRaises(NativeWriteError):
                    writer.verify(source, output, intent, replace(prepared, semantic_diff=bad))

    def test_legacy_warning_lists_remain_bounded_wire_data(self):
        writer, source, output, intent, prepared = self.proof_case()
        for value in ("not a list", ["x" * 2049], [False]):
            with self.subTest(value=value):
                bad = deepcopy(prepared.semantic_diff) | {"legality_warnings_after": value}
                with self.assertRaises(NativeWriteError):
                    writer.verify(source, output, intent, replace(prepared, semantic_diff=bad))

    def test_hash_and_contract_checks_still_fail_before_invoking_native(self):
        writer, source, output, intent, prepared = self.proof_case()
        for values in ({"source_hash": "f" * 64}, {"output_hash": "f" * 64},
                       {"contract": {"schema_version": 2, "writer_version": writer.version}}):
            with self.subTest(values=values), self.assertRaises(NativeWriteError):
                writer.verify(source, output, intent, replace(prepared, **values))
        writer._run.assert_not_called()

    def test_inspection_rejects_wrong_identity_value_types_and_unbounded_warnings(self):
        source = bytes(NATIVE_SIZES["Y"])
        info = dict(location="box", box_index=0, slot_index=0,
                    pokemon_sha256="a" * 64, nature=0, ivs=[1, 2, 3, 4, 5, 6],
                    target_pid=123, target_ec=456, is_egg=False,
                    legality_warnings=[], hidden_power_type=0)
        writer = object.__new__(PkhexProcessWriter)
        response = dict(status="inspected", source_sha256=sha256(source).hexdigest(),
                        game="Y", trainer_key="b" * 64, output_base64=None,
                        output_sha256=None, semantic_diff=info)
        writer._run = Mock(return_value=response)
        self.assertEqual(writer.inspect_training(source, "box", 0, 0)["target_pid"], 123)
        for key, value in (("box_index", False), ("slot_index", False),
                           ("target_pid", True), ("target_ec", -1),
                           ("hidden_power_type", True), ("hidden_power_type", 16),
                           ("legality_warnings", ["x" * 2049])):
            with self.subTest(key=key, value=value):
                bad = deepcopy(response)
                bad["semantic_diff"][key] = value
                writer._run.return_value = bad
                with self.assertRaises(NativeWriteError):
                    writer.inspect_training(source, "box", 0, 0)

    def test_training_receipt_rejects_boolean_nature_and_ivs(self):
        mutation = dict(item_code="menta_naturaleza", expected_nature=0, nature_id=1,
                        expected_ivs=[0, 2, 3, 4, 5, 6], expected_pokemon_sha256="a" * 64)
        diff = mutation | dict(preserved_unrelated=True, checksums_valid=True, signature_valid=True,
                               before_nature=0, after_nature=1,
                               before_ivs=[0, 2, 3, 4, 5, 6], after_ivs=[0, 2, 3, 4, 5, 6],
                               target_pid=123, target_ec=456, before_pokemon_sha256="a" * 64,
                               after_pokemon_sha256="b" * 64, legality_warnings_before=[],
                               legality_warnings_after=[], hidden_power_before=0, hidden_power_after=0)
        PkhexProcessWriter._training_diff(mutation, diff)
        for key, value in (("before_nature", False), ("after_nature", True),
                           ("before_ivs", [False, 2, 3, 4, 5, 6]),
                           ("after_ivs", [False, 2, 3, 4, 5, 6])):
            with self.subTest(key=key):
                bad = diff | {key: value}
                with self.assertRaises(NativeWriteError):
                    PkhexProcessWriter._training_diff(mutation, bad)
