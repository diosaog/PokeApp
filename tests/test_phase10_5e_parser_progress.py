from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from app.launcher.journal import LocalJournal
from app.save_parser.files import SaveSource, SnapshotReader
from app.save_parser.models import ObservedSave, progress_evidence, progress_layout
from phase9_fixtures import observed


def progress(primary="unova", *others, flags=None):
    return {
        "schema_version": 1,
        "primary_region": primary,
        "regions": [
            {"region": region, "badge_flags": flags or [False] * 8}
            for region in (primary, *others)
        ],
    }


def save_with_progress(value, *, game="B2W2", generation=5):
    body = observed().model_dump(mode="json")
    return ObservedSave.model_validate_json(
        json.dumps(
            body
            | {
                "game": game,
                "generation": generation,
                "party": [None] * 6,
                "progress": value,
            }
        )
    )


class ObservedProgressTests(unittest.TestCase):
    def test_neutral_progress_envelope_preserves_exact_source_and_unknown(self):
        source_hash = "ab" * 32
        result = progress_evidence(save_with_progress(progress()), source_hash)
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "game": "B2W2",
                "generation": 5,
                "source_hash": source_hash,
                "progress": progress() | {"champion_defeated": None},
            },
        )
        self.assertIsNone(progress_evidence(observed(), source_hash)["progress"])
        for invalid in ("", "aa" * 31, "AB" * 32, "gg" * 32, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                progress_evidence(observed(), invalid)

    def test_absent_legacy_progress_stays_unknown_not_observed_zero(self):
        body = observed().model_dump(mode="json")
        del body["progress"]
        old = ObservedSave.model_validate_json(json.dumps(body))
        zero = save_with_progress(progress())
        self.assertIsNone(old.progress)
        self.assertEqual(zero.progress.regions[0].badge_flags, (False,) * 8)
        self.assertNotEqual(old.progress, zero.progress)
        self.assertIsNone(save_with_progress(None).progress)

    def test_exact_sparse_flags_and_regions_roundtrip_for_supported_games(self):
        flags = [True, False, True, False, False, True, False, True]
        for game in (
            "R",
            "S",
            "RS",
            "E",
            "FR",
            "LG",
            "FRLG",
            "D",
            "P",
            "DP",
            "Pt",
            "HG",
            "SS",
            "HGSS",
            "B",
            "W",
            "BW",
            "B2",
            "W2",
            "B2W2",
        ):
            with self.subTest(game=game):
                generation, regions = progress_layout(game)
                result = save_with_progress(
                    progress(*regions, flags=flags), game=game, generation=generation
                )
                self.assertEqual(result.progress.regions[0].badge_flags, tuple(flags))
                self.assertEqual(
                    result, ObservedSave.model_validate_json(result.model_dump_json())
                )

    def test_hgss_kanto_medals_cannot_become_primary_progress(self):
        value = progress("johto", "kanto")
        value["regions"][1]["badge_flags"] = [True] * 8
        result = save_with_progress(value, game="HGSS", generation=4)
        self.assertEqual(result.progress.primary_region, "johto")
        self.assertEqual(result.progress.regions[0].badge_flags, (False,) * 8)
        self.assertEqual(result.progress.regions[1].badge_flags, (True,) * 8)

    def test_wrong_game_generation_missing_extra_or_reordered_regions_rejected(self):
        for game, generation, value in (
            ("HGSS", 4, progress("johto")),
            ("HGSS", 4, progress("kanto", "johto")),
            ("BW", 5, progress("johto")),
            ("RS", 3, progress("hoenn", "kanto")),
            ("E", 4, progress("hoenn")),
            ("UNKNOWN", 5, progress()),
        ):
            with (
                self.subTest(game=game, value=value),
                self.assertRaises(ValidationError),
            ):
                save_with_progress(value, game=game, generation=generation)

    def test_progress_strict_shape_no_counts_manual_authority_or_coercion(self):
        invalid = [
            progress("unova", "unova"),
            progress(flags=[False] * 7),
            progress(flags=[False] * 9),
            progress(flags=[1] + [False] * 7),
            progress(flags=["true"] + [False] * 7),
            progress(flags=[None] + [False] * 7),
            progress() | {"badge_count": 2},
            progress() | {"approved_by": "admin"},
            progress() | {"schema_version": 2},
            progress() | {"schema_version": True},
            progress() | {"schema_version": 1.0},
            progress() | {"primary_region": "kanto"},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                save_with_progress(value)

    def test_old_journal_remains_readable_and_new_parser_reobserves_same_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "save.sav"
            path.write_bytes(b"generated source")
            source = SaveSource.enroll(path)
            fingerprint = SnapshotReader().read(source).fingerprint
            journal = LocalJournal(Path(folder) / "journal.sqlite")
            original, _ = journal.record(
                source,
                expected=None,
                fingerprint=fingerprint,
                parser_version="pokeapp-reader/1;pkhex/24.11.11",
                observation=observed(),
            )
            # Reproduce the actual old serialized shape rather than merely null.
            with journal.connection() as db:
                payload = observed().model_dump(mode="json")
                payload.pop("progress")
                db.execute(
                    "UPDATE observations SET payload=? WHERE id=?",
                    (json.dumps(payload), original.id),
                )
            self.assertIsNone(journal.head(source).observation.progress)
            current, changed = journal.record(
                source,
                expected=original.id,
                fingerprint=fingerprint,
                parser_version="pokeapp-reader/2;pkhex/24.11.11",
                observation=save_with_progress(progress()),
            )
            self.assertTrue(changed)
            self.assertEqual(current.revision, 2)
            self.assertIsNotNone(journal.head(source).observation.progress)
            with journal.connection() as db:
                old = db.execute(
                    "SELECT payload FROM observations WHERE id=?", (original.id,)
                ).fetchone()["payload"]
            self.assertNotIn("progress", json.loads(old))
