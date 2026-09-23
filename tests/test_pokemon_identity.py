from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import Mock

from app.application.pokemon_identity import observations_from_payload, reconcile_parsed_save
from app.domain.pokemon import PrivatePokemon
from app.domain.pokemon_identity import (
    CaptureOrder, IdentityResolutionDecision, ParsedPokemonObservation, PokemonEntity,
    PokemonIdentityEvidence, PokemonLocation, bind_parsed_save, reconcile_pokemon, unique_legacy_flag_targets,
)
from app.repositories.errors import ConflictError
from pkmmeta import pokemon_fingerprint_stable

ROOT = Path(__file__).resolve().parents[1]


def evidence(**changes):
    return PokemonIdentityEvidence(**dict(schema_version=1, format=5, pid=123456789, ot_tid=12345,
        ot_sid=6789, origin_version=20, language=2, ot_name='Fixture', ot_gender=0, ivs=(17,0,0,0,0,0)) | changes)


def observation(slot=1, *, ev=None, source='party', box=0, fingerprints=('legacy',)):
    return ParsedPokemonObservation(PokemonLocation(source, box, slot), ev or evidence(), fingerprints)


def previous_from(plan):
    return tuple(PokemonEntity(b.authoritative_id(), b.observation.evidence) for b in plan.bindings)


class PokemonIdentityTests(unittest.TestCase):
    def first(self, incoming=None):
        return reconcile_pokemon((), incoming or (observation(),), save_file_id=str(uuid4()))

    def test_i04_i08_mutable_snapshot_and_location_excluded(self):
        first = self.first()
        for source, box, slot in [('box',8,30), ('party',0,6), ('box',1,1)]:
            obs = observation(slot, source=source, box=box)
            result = reconcile_pokemon(previous_from(first), (obs,), save_file_id=str(uuid4()))
            self.assertEqual(result.bindings[0].authoritative_id(), first.bindings[0].authoritative_id())

    def test_i10_distinct_same_species(self):
        result = self.first((observation(), observation(2, ev=evidence(pid=99))))
        self.assertEqual(len({b.authoritative_id() for b in result.bindings}), 2)

    def test_i11_i14_true_clones_not_collapsed(self):
        result = self.first((observation(), observation(2)))
        self.assertEqual(len({b.authoritative_id() for b in result.bindings}), 2)
        self.assertEqual(result.bindings[0].observation.evidence, result.bindings[1].observation.evidence)

    def test_i12_versions_reject_unknown(self):
        with self.assertRaises(ValueError): evidence(schema_version=2)
        with self.assertRaises(ValueError): evidence(format=6)

    def test_i13_one_entity_per_occurrence(self):
        self.assertEqual(len(self.first().bindings), 1)

    def test_i15_i16_movement_preserves_entity(self):
        self.test_i04_i08_mutable_snapshot_and_location_excluded()

    def test_i19_missing_retained(self):
        previous = previous_from(self.first())
        result = reconcile_pokemon(previous, (), save_file_id=str(uuid4()))
        self.assertEqual(result.missing_entity_ids, (previous[0].id,))
        self.assertEqual(result.bindings, ())

    def test_i20_unambiguous_reappearance(self):
        previous = tuple(replace(e, identity_status='missing') for e in previous_from(self.first()))
        result = reconcile_pokemon(previous, (observation(),), save_file_id=str(uuid4()))
        self.assertEqual(result.bindings[0].authoritative_id(), previous[0].id)

    def test_i21_new_pokemon(self):
        result = reconcile_pokemon(previous_from(self.first()), (observation(ev=evidence(pid=99)),), save_file_id=str(uuid4()))
        self.assertEqual(result.bindings[0].outcome, 'NEW')
        self.assertEqual(len(result.missing_entity_ids), 1)

    def test_i22_clone_swap_never_uses_location(self):
        previous = previous_from(self.first((observation(), observation(2))))
        result = reconcile_pokemon(previous, (observation(3), observation(4)), save_file_id=str(uuid4()))
        self.assertTrue(all(b.outcome == 'AMBIGUOUS' and b.pokemon_entity_id is None for b in result.bindings))
        self.assertEqual(set(result.bindings[0].candidate_entity_ids), {e.id for e in previous})

    def test_i23_ambiguous_binding_denied(self):
        previous = previous_from(self.first((observation(), observation(2))))
        binding = reconcile_pokemon(previous, (observation(),), save_file_id=str(uuid4())).bindings[0]
        with self.assertRaises(ValueError): binding.bind(PrivatePokemon(species='Gengar'))

    def test_i24_i34_i35_initial_retry_stable(self):
        save = str(uuid4())
        a = reconcile_pokemon((), (observation(),), save_file_id=save)
        b = reconcile_pokemon((), (observation(),), save_file_id=save)
        self.assertEqual(a, b)

    def test_i25_unique_flag_mapping(self):
        binding = self.first().bindings[0]
        self.assertEqual(unique_legacy_flag_targets((binding,)), {'legacy': binding.pokemon_entity_id})

    def test_i26_i27_collision_unresolved(self):
        bindings = self.first((observation(), observation(2))).bindings
        self.assertIsNone(unique_legacy_flag_targets(bindings)['legacy'])

    def test_i29_target_one_clone(self):
        bindings = self.first((observation(), observation(2))).bindings
        self.assertNotEqual(bindings[0].authoritative_id(), bindings[1].authoritative_id())

    def test_i30_legacy_collision_preserved(self):
        raw = dict(dex_id=94, species='Gengar', ot_tid=12345, ot_sid=6789, gender='M', level=50)
        self.assertEqual(pokemon_fingerprint_stable(dict(raw, nickname='A', ivs={'hp':1})),
                         pokemon_fingerprint_stable(dict(raw, nickname='B', ivs={'hp':31})))

    def test_i31_private_evidence_not_in_public_projection(self):
        pokemon = PrivatePokemon(species='Gastly', identity_evidence=evidence())
        bound = self.first().bindings[0].bind(pokemon)
        self.assertTrue(bound.id)
        self.assertNotIn('identity_evidence', asdict(bound.to_public()))
        self.assertEqual(pokemon.id, '')

    def test_i32_three_sequential_saves(self):
        first = self.first()
        previous = previous_from(first)
        for slot in (3,4,5):
            plan = reconcile_pokemon(previous, (observation(slot),), save_file_id=str(uuid4()))
            self.assertEqual(plan.bindings[0].pokemon_entity_id, first.bindings[0].pokemon_entity_id)
            previous = previous_from(plan)

    def test_i33_unproven_order_rejected_before_repository(self):
        with self.assertRaises(ConflictError):
            reconcile_parsed_save(None, season_id=str(uuid4()), trainer_id=str(uuid4()), parsed_save_id=str(uuid4()))

    def test_invalid_evidence_fails_closed(self):
        for changes in ({'pid':None}, {'pid':True}, {'ot_name':''}, {'language':0}, {'ivs':(32,)*6}, {'encryption_constant':1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): evidence(**changes)

    def test_pid_zero_is_real_not_absent(self):
        self.assertEqual(evidence(pid=0).pid, 0)

    def test_stat_edit_not_new_entity(self):
        previous = previous_from(self.first())
        result = reconcile_pokemon(previous, (observation(ev=evidence(ivs=(31,)*6)),), save_file_id=str(uuid4()))
        self.assertEqual(result.bindings[0].pokemon_entity_id, previous[0].id)

    def test_same_pid_different_ivs_conservative_ambiguity(self):
        previous = previous_from(self.first((observation(), observation(2, ev=evidence(ivs=(31,)*6)))))
        result = reconcile_pokemon(previous, (observation(), observation(2)), save_file_id=str(uuid4()))
        self.assertTrue(all(b.outcome == 'AMBIGUOUS' for b in result.bindings))

    def test_changed_ot_or_generation_requires_review(self):
        for ev in (evidence(ot_tid=99), evidence(format=4)):
            result = reconcile_pokemon(previous_from(self.first()), (observation(ev=ev),), save_file_id=str(uuid4()))
            self.assertEqual(result.bindings[0].outcome, 'AMBIGUOUS')

    def test_ambiguous_entity_does_not_silently_recover(self):
        previous = (replace(previous_from(self.first())[0], identity_status='ambiguous'),)
        result = reconcile_pokemon(previous, (observation(),), save_file_id=str(uuid4()))
        self.assertEqual(result.bindings[0].outcome, 'AMBIGUOUS')

    def test_duplicate_location_rejected(self):
        with self.assertRaises(ValueError): self.first((observation(), observation()))

    def test_invalid_location_rejected(self):
        for args in [('party',1,1), ('party',0,7), ('box',0,1), ('box',1,31)]:
            with self.assertRaises(ValueError): PokemonLocation(*args)

    def test_capture_order_validation(self):
        for seq in (0,-1,True):
            with self.assertRaises(ValueError): CaptureOrder(str(uuid4()), seq)

    def test_resolution_requires_audit_reason(self):
        with self.assertRaises(ValueError):
            IdentityResolutionDecision(*(str(uuid4()) for _ in range(4)), reason='', evidence_reference='fixture')

    def test_payload_legacy_evidence_absence_rejected(self):
        with self.assertRaises(KeyError):
            observations_from_payload({'party':[{'slot_number':1,'pokemon':{'species':'Gengar'}}], 'boxes':[]})

    def test_parsed_save_can_expose_reconciled_uuid_without_mutating_original(self):
        from app.domain.saves import ParsedSave, PartySlot
        parsed = ParsedSave(1,str(uuid4()),str(uuid4()),party=(PartySlot(1,PrivatePokemon(species='Gastly')),))
        plan = self.first()
        bound = bind_parsed_save(parsed,plan)
        self.assertEqual(bound.party[0].pokemon.id, plan.bindings[0].authoritative_id())
        self.assertEqual(parsed.party[0].pokemon.id, '')

    def test_application_loads_authoritative_source_and_commits_versioned_plan(self):
        repository = Mock()
        season, trainer, saved, parsed = (str(uuid4()) for _ in range(4))
        repository.load_context.return_value = dict(parsed=dict(id=parsed,save_file_id=saved,
            payload=dict(party=[dict(slot_number=1,pokemon=dict(species='Gastly',identity_evidence=asdict(evidence())))],boxes=[])),
            save=dict(id=saved,season_id=season,trainer_id=trainer), head=None,entities=[])
        repository.commit.side_effect = lambda request:request
        result = reconcile_parsed_save(repository,season_id=season,trainer_id=trainer,parsed_save_id=parsed,
                                       capture_order=CaptureOrder(str(uuid4()),1))
        self.assertEqual(result['bindings'][0]['outcome'],'NEW')
        self.assertEqual(result['reconciliation_version'],1)
        self.assertIsNone(result['expected_predecessor_id'])

    def test_application_refuses_scope_mismatch(self):
        repository = Mock()
        repository.load_context.return_value = dict(parsed={},save=dict(season_id='foreign'),head=None)
        with self.assertRaises(ConflictError):
            reconcile_parsed_save(repository,season_id=str(uuid4()),trainer_id=str(uuid4()),parsed_save_id=str(uuid4()),
                                   capture_order=CaptureOrder(str(uuid4()),1))
        repository.commit.assert_not_called()

    def test_repo_rejects_wrong_receipt(self):
        from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
        from app.repositories.errors import PersistenceError
        client = Mock()
        client.rpc.return_value.execute.return_value.data = {'revision': {'save_file_id':'wrong'}}
        with self.assertRaises(PersistenceError):
            SupabasePokemonIdentityRepository(client).commit({'save_file_id':str(uuid4())})

    def test_new_privacy_and_lock_schema_contract(self):
        sql = (ROOT/'supabase/v2/migrations/023_pokemon_identity.sql').read_text().lower()
        for fragment in ('for update', 'security invoker set search_path', 'identity_head_changed',
                         'identity_out_of_order', 'identity_multiple_candidates', 'identity_evidence_source_mismatch',
                         'unique(save_file_id, pokemon_entity_id)', 'unique(season_id, pokemon_entity_id, flag_type)'):
            self.assertIn(fragment,sql)
        for forbidden in ('security definer','drop table','update public.team_locks','update public.pokemon_flags','create view'):
            self.assertNotIn(forbidden,sql)

    def test_changed_evidence_and_exact_copy_both_ambiguous(self):
        previous = previous_from(self.first())
        result = reconcile_pokemon(previous, (observation(),observation(2,ev=evidence(ot_tid=99))), save_file_id=str(uuid4()))
        self.assertTrue(all(b.outcome=='AMBIGUOUS' for b in result.bindings))


class ReadOnlyBridgeIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidate = Path(tempfile.gettempdir()) / 'pokeapp-dotnet9' / 'dotnet.exe'
        dotnet = os.environ.get('POKEAPP_DOTNET') or (str(candidate) if candidate.exists() else shutil.which('dotnet'))
        if not dotnet:
            raise unittest.SkipTest('Install .NET 9 SDK or set POKEAPP_DOTNET for real PKHeX probe')
        build = subprocess.run([dotnet, 'build', 'tools/identity_bridge_probe/IdentityBridgeProbe.csproj', '--nologo'],
                               cwd=ROOT, capture_output=True, text=True)
        if build.returncode:
            raise AssertionError(build.stdout + build.stderr)
        output = subprocess.check_output([dotnet, str(ROOT / '.dotnet-sdk/identity-probe/bin/net9.0/IdentityBridgeProbe.dll')], text=True)
        cls.probe = json.loads(output)

    def verify_generation(self, gen):
        self.assertEqual(self.probe['version'], '24.11.11.0')
        row = next(r for r in self.probe['rows'] if r['format'] == gen)
        initial = PokemonIdentityEvidence(**row['initial']['IdentityEvidence'])
        self.assertEqual(initial.format, gen)
        self.assertEqual((initial.ot_tid, initial.ot_sid, initial.pid), (12345,6789,123456789))
        self.assertIsNone(initial.encryption_constant)
        if gen == 3: self.assertIsNone(initial.egg_location)
        previous = PokemonEntity(str(uuid4()), initial)
        for stage in ('evolved','final'):
            current = PokemonIdentityEvidence(**row[stage]['IdentityEvidence'])
            self.assertEqual(current.candidate_key, initial.candidate_key)
            result = reconcile_pokemon((previous,), (observation(ev=current),), save_file_id=str(uuid4()))
            self.assertEqual(result.bindings[0].pokemon_entity_id, previous.id)
        self.assertEqual([row[s]['SpeciesId'] for s in ('initial','evolved','final')], [92,93,94])

    def test_i01_gen3_i05_i06_i07_i09_i17_i18(self): self.verify_generation(3)
    def test_i02_gen4_i05_i06_i07_i09_i17_i18(self): self.verify_generation(4)
    def test_i03_gen5_i05_i06_i07_i09_i17_i18(self): self.verify_generation(5)

    def test_python_normalizer_preserves_evidence(self):
        from conex_pkhex import _pkm_to_ui
        row = self.probe['rows'][2]['initial']
        result = _pkm_to_ui(row)
        self.assertEqual(result['identity_evidence'], row['IdentityEvidence'])


if __name__ == '__main__': unittest.main()
