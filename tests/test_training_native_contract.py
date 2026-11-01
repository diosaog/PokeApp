"""Malformed native receipts must not become authority for an edit.

Synthetic protocol envelopes only; the separate native matrix proves saves.
"""
from copy import deepcopy
from hashlib import sha256
import unittest
from unittest.mock import Mock

from app.save_parser.native_sizes import NATIVE_SIZES
from app.save_parser.writer import NativeWriteError, PkhexProcessWriter


class TrainingNativeContractTests(unittest.TestCase):
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
