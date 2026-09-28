from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError

from app.domain.pokemon_identity import PokemonEntity, reconcile_pokemon
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.files import SaveSource, SnapshotReader, file_error
from app.save_parser.models import (
    ErrorCode,
    ObservedSave,
    ParserResponse,
    SaveError,
    compare_observations,
)
from phase9_fixtures import FakeParser, observed, pokemon


class Phase9ParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "Pokémon espacio.sav"
        self.path.write_bytes(b"synthetic snapshot")
        self.source = SaveSource.enroll(self.path)

    def test_neutral_roundtrip_including_empty_slots_and_identity(self):
        value = observed()
        encoded = value.model_dump_json()
        self.assertEqual(value, ObservedSave.model_validate_json(encoded))
        self.assertEqual(value.party[1:], (None,) * 5)
        self.assertEqual(len(value.boxes[0].slots), 30)
        self.assertEqual(value.identity_observations()[0].evidence.pid, 123)
        self.assertNotIn("entity_id", encoded)
        self.assertNotIn("PKHeX", encoded)

    def test_malformed_layout_fields_and_unknown_authority_rejected(self):
        for change in (
            {"party": []},
            {"trainer_id": str(uuid4())},
            {"generation": 6},
            {"boxes": [{"number": 2, "slots": [None] * 30}]},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ObservedSave.model_validate_json(
                    json.dumps(observed().model_dump(mode="json") | change)
                )

    def test_move_evolution_and_clone_observations_follow_023(self):
        first = observed()
        moved = observed(
            party=[None] * 6, boxes=[dict(number=1, slots=[pokemon()] + [None] * 29)]
        )
        self.assertEqual(compare_observations(first, moved)[0].status, "MOVED")
        entity = PokemonEntity(str(uuid4()), first.party[0].identity)
        plan = reconcile_pokemon(
            (entity,), moved.identity_observations(), save_file_id=str(uuid4())
        )
        self.assertEqual(plan.bindings[0].pokemon_entity_id, entity.id)
        clone = observed(party=[pokemon(), pokemon()] + [None] * 4)
        self.assertEqual(compare_observations(first, clone)[0].status, "AMBIGUOUS")
        plan = reconcile_pokemon(
            (entity,), clone.identity_observations(), save_file_id=str(uuid4())
        )
        self.assertTrue(
            all(
                b.outcome == "AMBIGUOUS" and b.pokemon_entity_id is None
                for b in plan.bindings
            )
        )
        changed = pokemon()
        changed["species_id"] = 26
        self.assertEqual(
            compare_observations(first, observed(party=[changed] + [None] * 5))[
                0
            ].status,
            "CHANGED",
        )
        self.assertEqual(
            compare_observations(first, observed(party=[None] * 6))[0].status, "MISSING"
        )
        self.assertEqual(compare_observations(None, first)[0].status, "NEW")

    def test_fingerprint_content_stable_and_change_detected_without_mtime(self):
        reader = SnapshotReader()
        first = reader.read(self.source)
        self.assertEqual(first.fingerprint, reader.read(self.source).fingerprint)
        self.path.write_bytes(b"different snapshot")
        os.utime(self.path, ns=(first.metadata.mtime_ns, first.metadata.mtime_ns))
        self.assertNotEqual(first.fingerprint, reader.read(self.source).fingerprint)
        with self.assertRaises(SaveError) as cm:
            reader.verify(first)
        self.assertEqual(cm.exception.code, ErrorCode.SAVE_CHANGED_DURING_READ)

    def test_file_replacement_same_bytes_detected(self):
        reader = SnapshotReader()
        first = reader.read(self.source)
        replacement = self.path.with_suffix(".tmp")
        replacement.write_bytes(first.data)
        os.utime(replacement, ns=(first.metadata.mtime_ns, first.metadata.mtime_ns))
        os.replace(replacement, self.path)
        with self.assertRaises(SaveError) as cm:
            reader.verify(first)
        self.assertEqual(cm.exception.code, ErrorCode.SAVE_CHANGED_DURING_READ)

    def test_write_during_parse_never_accepted(self):
        fake = FakeParser()

        def parse(data):
            self.path.write_bytes(b"emulator changed file")
            return observed()

        fake.parse = parse
        with self.assertRaises(SaveError) as cm:
            SaveInspector(fake).inspect(self.source)
        self.assertEqual(cm.exception.code, ErrorCode.SAVE_CHANGED_DURING_READ)

    def test_invalid_paths_and_missing_or_empty_save(self):
        for value in (r"\\server\share\file.sav", r"\\.\device", ""):
            with self.assertRaises(SaveError):
                SaveSource.enroll(value)
        with self.assertRaises(SaveError) as cm:
            SaveSource.enroll(self.path.with_name("absent.sav"))
        self.assertEqual(cm.exception.code, ErrorCode.SAVE_NOT_FOUND)
        self.path.write_bytes(b"")
        with self.assertRaises(SaveError) as cm:
            SnapshotReader().read(self.source)
        self.assertEqual(cm.exception.code, ErrorCode.TRUNCATED_SAVE)

    def test_permission_and_windows_lock_classification(self):
        with patch(
            "app.save_parser.files._open_read",
            side_effect=PermissionError("private path"),
        ):
            with self.assertRaises(SaveError) as cm:
                SnapshotReader().read(self.source)
        self.assertEqual(str(cm.exception), "ACCESS_DENIED")
        locked = PermissionError()
        locked.winerror = 32
        self.assertEqual(file_error(locked).code, ErrorCode.FILE_LOCKED)

    def test_parser_exception_never_becomes_empty_success(self):
        fake = FakeParser()
        with patch.object(fake, "parse", side_effect=RuntimeError("secret")):
            with self.assertRaises(SaveError) as cm:
                SaveInspector(fake).inspect(self.source)
        self.assertEqual(str(cm.exception), "PARSER_FAILURE")

    def test_process_protocol_errors_and_timeout_are_sanitized(self):
        parser = PkhexProcessParser(self.path)
        payload = dict(
            schema_version=1, parser_version=parser.version, observation=None
        )
        for code in (
            "CORRUPT_SAVE",
            "UNSUPPORTED_GAME",
            "UNSUPPORTED_VERSION",
            "AMBIGUOUS_IDENTITY",
            "TRUNCATED_SAVE",
        ):
            result = subprocess.CompletedProcess(
                [], 0, json.dumps(payload | {"error": code}).encode(), b"secret"
            )
            with (
                patch("subprocess.run", return_value=result),
                self.assertRaises(SaveError) as cm,
            ):
                parser.parse(b"test")
            self.assertEqual(str(cm.exception), code)
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("secret path", 1)
        ):
            with self.assertRaises(SaveError) as cm:
                parser.parse(b"test")
        self.assertEqual(str(cm.exception), "PARSER_FAILURE")
        for invalid in (b"not json", b"{}"):
            with patch(
                "subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, invalid, b""),
            ):
                with self.assertRaises(SaveError):
                    parser.parse(b"test")

    def test_error_success_exclusivity(self):
        for observation, error in (
            (None, None),
            (observed().model_dump(mode="json"), "CORRUPT_SAVE"),
        ):
            with self.assertRaises(ValidationError):
                ParserResponse.model_validate_json(
                    json.dumps(
                        dict(
                            schema_version=1,
                            parser_version="v1",
                            observation=observation,
                            error=error,
                        )
                    )
                )

    def test_successful_snapshot_inspection(self):
        fake = FakeParser()
        result = SaveInspector(fake).inspect(self.source)
        self.assertEqual(result.observation, observed())
        self.assertEqual(result.snapshot.data, b"synthetic snapshot")
        self.assertEqual(fake.calls, 1)
