"""X/Y neutral read contract; no production credentials or personal saves."""

import json
import unittest
from copy import deepcopy
from uuid import uuid4

from pydantic import ValidationError

from app.domain.pokemon_identity import PokemonIdentityEvidence
from app.save_parser.cloud import CloudObservation, MAX_OBSERVATION_BYTES
from app.save_parser.models import ObservedSave, compare_observations
from app.save_parser.xy_identity import ObservedXYIdentity
from phase9_fixtures import observed, pokemon
import test_phase16_launcher as launcher_fixture

body, receipt, SID = (
    launcher_fixture.body,
    launcher_fixture.receipt,
    launcher_fixture.SID,
)


def xy_payload(game="X"):
    value = observed().model_dump(mode="json")
    member = pokemon()
    member["species_id"] = 650
    member["moves"][0]["id"] = 617
    member["identity"].update(format=6, origin_version=24, encryption_constant=999)
    value.update(
        game=game,
        generation=6,
        progress=None,
        party=[member] + [None] * 5,
        boxes=[dict(number=i, slots=[None] * 30) for i in range(1, 32)],
    )
    value["boxes"][30]["slots"][29] = deepcopy(member)
    value["boxes"][30]["slots"][29]["identity"]["pid"] = 456
    return value


def xy(value=None):
    return ObservedSave.model_validate_json(json.dumps(value or xy_payload()))


class XYContractTests(unittest.TestCase):
    def test_games_full_boxes_and_serialization(self):
        for game in ("X", "Y"):
            value = xy(xy_payload(game))
            self.assertEqual(
                value, ObservedSave.model_validate_json(value.model_dump_json())
            )
            self.assertIsInstance(value.party[0].identity, ObservedXYIdentity)
            self.assertEqual(len(value.boxes), 31)
            self.assertEqual(value.party[1:], (None,) * 5)
            self.assertEqual(list(value.occupied())[-1][0].box_number, 31)
            self.assertEqual(list(value.occupied())[-1][0].slot_number, 30)
            self.assertIsNone(value.progress)

    def test_unsupported_games_mismatched_generations_layouts_and_progress(self):
        for change in (
            {"game": "OR"},
            {"game": "AS"},
            {"game": "SN"},
            {"game": "XY"},
            {"generation": 7},
            {"generation": 5},
            {"boxes": xy_payload()["boxes"][:24]},
            {
                "progress": {
                    "schema_version": 1,
                    "primary_region": "unova",
                    "regions": [{"region": "unova", "badge_flags": [False] * 8}],
                }
            },
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                xy(xy_payload() | change)

    def test_identity_requires_real_independent_ec_and_strict_values(self):
        for key, bad in (
            ("encryption_constant", None),
            ("encryption_constant", True),
            ("encryption_constant", -1),
            ("encryption_constant", 2**32),
            ("format", 7),
            ("pid", True),
            ("ot_name", ""),
            ("language", 0),
            ("ivs", [32] * 6),
        ):
            value = xy_payload()
            value["party"][0]["identity"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValidationError):
                xy(value)
        # Zero is a legitimate observed EC, not an absent field.
        value = xy_payload()
        value["party"][0]["identity"]["encryption_constant"] = 0
        self.assertEqual(xy(value).party[0].identity.encryption_constant, 0)

    def test_conservative_local_identity_never_allocates_competitive_ids(self):
        first = xy()
        moved = xy_payload()
        moved["boxes"][0]["slots"][3], moved["party"][0] = moved["party"][0], None
        self.assertEqual(compare_observations(first, xy(moved))[0].status, "MOVED")
        changed = xy_payload()
        changed["party"][0]["identity"]["encryption_constant"] += 1
        self.assertEqual(
            compare_observations(first, xy(changed))[0].status, "AMBIGUOUS"
        )
        clone = xy_payload()
        clone["party"][1] = deepcopy(clone["party"][0])
        self.assertEqual(compare_observations(first, xy(clone))[0].status, "AMBIGUOUS")
        with self.assertRaisesRegex(
            ValueError, "xy_competitive_identity_not_supported"
        ):
            first.identity_observations()
        with self.assertRaises(ValueError):
            PokemonIdentityEvidence(**xy_payload()["party"][0]["identity"])

    def test_existing_contracts_remain_readable_and_bounded(self):
        old = observed()
        self.assertEqual(old, ObservedSave.model_validate_json(old.model_dump_json()))
        self.assertIsInstance(old.party[0].identity, PokemonIdentityEvidence)
        for field, value in (
            ("species_id", 650),
            ("moves", [{"id": 617, "pp": 5}] * 4),
        ):
            invalid = old.model_dump(mode="json")
            invalid["party"][0][field] = value
            with self.assertRaises(ValidationError):
                ObservedSave.model_validate_json(json.dumps(invalid))
        self.assertEqual(
            CloudObservation.model_validate_json(body().model_dump_json()).digest(),
            body().digest(),
        )

    def test_full_930_slot_cloud_body_fits_existing_limit(self):
        value = xy_payload()
        for box in value["boxes"]:
            box["slots"] = [deepcopy(value["party"][0]) for _ in range(30)]
        envelope = CloudObservation(
            fingerprint=body().fingerprint,
            parser_version=body().parser_version,
            observation=xy(value),
        )
        self.assertLess(len(envelope.model_dump_json().encode()), MAX_OBSERVATION_BYTES)
        self.assertEqual(
            envelope.digest(),
            CloudObservation.model_validate_json(envelope.model_dump_json()).digest(),
        )


class XYApiTests(unittest.TestCase):
    def setUp(self):
        # Reuse the verified-JWT/participant dependency fixture, not a live API.
        self.fixture = launcher_fixture.CloudApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_xy_uses_existing_private_route_and_authority(self):
        f = self.fixture
        value = CloudObservation(
            fingerprint=body().fingerprint,
            parser_version=body().parser_version,
            observation=xy(),
        )
        expected = receipt(value)
        f.repo.execute.return_value = expected
        path = f.path.rsplit("/", 1)[0] + "/" + expected["id"]
        response = f.client.put(
            path, headers=f.headers, content=value.model_dump_json()
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["trust"], "client_observed")
        self.assertFalse(response.json()["competitive_authority"])
        self.assertNotIn("observation", response.json())
        self.assertEqual(
            f.repo.execute.call_args.args[1]["body"]["observation"]["game"], "X"
        )
        self.assertEqual(f.client.get(path).status_code, 401)
        self.assertEqual(
            f.client.put(path, content=value.model_dump_json()).status_code, 401
        )

    def test_forged_fields_invalid_identity_and_wrong_scope_stop_before_repo(self):
        f = self.fixture
        value = body().model_dump(mode="json") | {"observation": xy_payload()}
        for invalid in (
            value | {"trainer_id": str(uuid4())},
            value | {"competitive_authority": True},
            value | {"parser_version": "unknown"},
            value | {"observation": xy_payload("OR")},
        ):
            result = f.client.put(f.path, headers=f.headers, json=invalid)
            self.assertEqual(result.status_code, 422, result.text)
        f.repo.execute.assert_not_called()

    def test_malformed_identity_is_a_sanitized_422(self):
        f = self.fixture
        for identity_change in (
            {"unknown_private_field": 1},
            {"ivs": None},
            {"met_date": 5},
        ):
            value = body().model_dump(mode="json") | {"observation": xy_payload()}
            value["observation"]["party"][0]["identity"].update(identity_change)
            result = f.client.put(f.path, headers=f.headers, json=value)
            self.assertEqual(result.status_code, 422, result.text)
            self.assertNotIn("unknown_private_field", result.text)
        f.repo.execute.assert_not_called()
        good = CloudObservation.model_validate_json(
            json.dumps(body().model_dump(mode="json") | {"observation": xy_payload()})
        )
        alien = good.identifier(str(uuid4()), SID)
        self.assertEqual(
            f.client.put(
                f.path.rsplit("/", 1)[0] + "/" + alien,
                headers=f.headers,
                content=good.model_dump_json(),
            ).status_code,
            409,
        )
        f.repo.execute.assert_not_called()
