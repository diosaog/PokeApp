"""Focused synthetic DTO boundaries; authentic-save acceptance is a separate gate."""
import json
import unittest
from copy import deepcopy

from pydantic import ValidationError
import test_phase16b_xy as xy_fixture
import test_phase16d_save_sync as sync_fixture
from app.save_parser.models import ObservedSave, compare_observations
from app.save_parser.registration import observation_digest
from app.application.save_ingestion import TrustedSaveIngestion
from app.repositories.supabase.season_admin import SeasonAdminRejected


def oras_payload(game='OR'):
    value = xy_fixture.xy_payload(game)
    for p in (value['party'][0], value['boxes'][30]['slots'][29]):
        p.update(species_id=479, form=1, type_ids=[12, 9], item_id=752)
        p['moves'][0]['id'] = 621
        p['identity']['origin_version'] = 27 if game == 'OR' else 26
    return value


def read(value):
    return ObservedSave.model_validate_json(json.dumps(value))


class ORASContractTests(unittest.TestCase):
    def test_both_games_metadata_and_no_competitive_facts(self):
        for game in ('OR', 'AS'):
            obs = read(oras_payload(game))
            self.assertEqual(obs.game, game)
            self.assertEqual(obs.party[0].type_ids, (12, 9))
            self.assertIsNone(obs.progress)
            self.assertEqual(len(obs.boxes), 31)
            with self.assertRaises(ValueError):
                obs.identity_observations()

    def test_old_xy_wire_and_digest_remain_unchanged(self):
        value = xy_fixture.xy_payload()
        # Captured from the unmodified entry source 08f00ac, including its
        # canonical nullable identity defaults (not the partial fixture dict).
        self.assertEqual(observation_digest(read(value), sync_fixture.VERSION),
                         'f6edc65a9e96a1277a0b23768aa44263f710dc13992c1c15bb6c2767bee6978e')
        wrong = deepcopy(value)
        wrong['party'][0]['moves'][0]['id'] = 621
        with self.assertRaises(ValidationError):
            read(wrong)

    def test_bad_or_missing_evidence_fails_closed(self):
        for key, bad in (('type_ids', None), ('type_ids', [12, 18]), ('type_ids', [True, 9]), ('form', -1)):
            value = oras_payload()
            value['party'][0][key] = bad
            with self.subTest(key=key), self.assertRaises(ValidationError):
                read(value)
        with self.assertRaises(ValidationError):
            read(oras_payload('ORAS'))

    def test_local_movement_and_duplicate_remain_conservative(self):
        value = oras_payload()
        moved = deepcopy(value)
        moved['boxes'][0]['slots'][0], moved['party'][0] = moved['party'][0], None
        self.assertEqual(compare_observations(read(value), read(moved))[0].status, 'MOVED')
        moved['party'][0] = deepcopy(moved['boxes'][0]['slots'][0])
        self.assertEqual(compare_observations(read(value), read(moved))[0].status, 'AMBIGUOUS')

    def test_game_and_trainer_switch_cannot_replace_current(self):
        repo = sync_fixture.Repository()
        parser = sync_fixture.FakeParser()
        parser.version = sync_fixture.VERSION
        parser.value = read(oras_payload())
        service = TrustedSaveIngestion(repo, parser)
        for identity in (
            {'game':'X', 'trainer':parser.value.trainer.model_dump(mode='json')},
            {'game':'AS', 'trainer':parser.value.trainer.model_dump(mode='json')},
            {'game':'OR', 'trainer':parser.value.trainer.model_dump(mode='json') | {'tid':1}},
        ):
            repo.context.update(current_save_id=sync_fixture.SID, save_identity=identity)
            with self.assertRaises(SeasonAdminRejected):
                service.receive(sync_fixture.SID, sync_fixture.TRAINER_ID, sync_fixture.HASH,
                                sync_fixture.SID, observation_digest(parser.value, parser.version), sync_fixture.DATA)
        self.assertEqual(repo.raw, [])
        self.assertEqual(repo.writes, [])
