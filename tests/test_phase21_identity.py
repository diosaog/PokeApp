"""Scoped native identity rules; synthetic observations are not gameplay proof."""

import unittest
from dataclasses import asdict, replace
from types import SimpleNamespace
from uuid import uuid4

from app.domain.pokemon_identity import (
    ParsedPokemonObservation,
    PokemonEntity,
    PokemonIdentityEvidence,
    PokemonLocation,
    digest,
    identity_evidence_from_dict,
    reconcile_pokemon,
    trusted_native_identity,
    unique_legacy_flag_targets,
)
from app.save_parser.xy_identity import ObservedXYIdentity

TRAINER = dict(name="Fixture", tid=12345, sid=6789, gender=0, language=2)


def neutral(**changes):
    return ObservedXYIdentity(**(dict(
        schema_version=1, format=6, pid=123456789, ot_tid=12345, ot_sid=6789,
        origin_version=24, language=2, ot_name="Fixture", ot_gender=0,
        met_location=10, met_level=5, egg_location=0, met_date="2026-01-02",
        egg_date=None, encryption_constant=987654321, ivs=(17, 2, 3, 4, 5, 6),
    ) | changes))


def evidence(**changes):
    return replace(trusted_native_identity(neutral(), trainer=TRAINER, is_egg=False), **changes)


def observation(ev=None, *, source="party", box=0, slot=1):
    return ParsedPokemonObservation(PokemonLocation(source, box, slot), ev or evidence())


def reconcile(previous=(), incoming=None, **kwargs):
    return reconcile_pokemon(previous, incoming if incoming is not None else (observation(),),
                             save_file_id=kwargs.pop("save_file_id", str(uuid4())), **kwargs)


def entities(plan):
    return tuple(PokemonEntity(binding.authoritative_id(), binding.observation.evidence)
                 for binding in plan.bindings)


class TrustedNativeIdentityTests(unittest.TestCase):
    def test_conversion_is_separate_and_reconstructs(self):
        raw = neutral()
        original = asdict(raw)
        converted = trusted_native_identity(raw, trainer=SimpleNamespace(**TRAINER), is_egg=False)
        self.assertEqual(converted.schema_version, 2)
        self.assertTrue(converted.source_trainer_match)
        self.assertEqual(asdict(raw), original)
        self.assertNotIn("is_egg", original)
        self.assertNotIn("source_trainer_match", original)
        self.assertEqual(identity_evidence_from_dict(asdict(converted)), converted)

    def test_each_trainer_fact_is_required_and_foreign_ot_stays_unknown(self):
        for key, changed in (("name", "Foreign"), ("tid", 9), ("sid", 9),
                             ("gender", 1), ("language", 7), ("language", None)):
            value = trusted_native_identity(neutral(), trainer=TRAINER | {key: changed}, is_egg=False)
            self.assertFalse(value.source_trainer_match)
            binding = reconcile(incoming=(observation(value),)).bindings[0]
            self.assertEqual((binding.outcome, binding.pokemon_entity_id, binding.candidate_entity_ids),
                             ("AMBIGUOUS", None, ()))

    def test_gen6_and_gen7_supported_and_initial_retry_stable(self):
        for generation in (6, 7):
            incoming = (observation(evidence(format=generation)),)
            saved = str(uuid4())
            first = reconcile(incoming=incoming, save_file_id=saved)
            self.assertEqual(first, reconcile(incoming=incoming, save_file_id=saved))
            self.assertEqual(first.bindings[0].outcome, "NEW")

    def test_party_pc_box_swap_preserves_identity_and_flags(self):
        first = reconcile(incoming=(observation(), observation(evidence(pid=88, encryption_constant=77), slot=2)))
        previous = entities(first)
        flags = {previous[0].id: {"dead": True, "robado": True, "blindado": True, "revivido": True}}
        incoming = (observation(source="box", box=8, slot=30),
                    observation(previous[1].evidence, source="box", box=1, slot=2))
        result = reconcile(previous, incoming)
        self.assertEqual({b.pokemon_entity_id for b in result.bindings}, {e.id for e in previous})
        self.assertEqual(flags[previous[0].id], {"dead": True, "robado": True, "blindado": True, "revivido": True})
        self.assertEqual(unique_legacy_flag_targets(result.bindings), {})

    def test_visible_mutations_cannot_change_native_identity(self):
        from app.save_parser.models import ParsedPokemon
        raw = dict(species_id=650, nickname="Before", level=5, form=0, gender=0,
                   shiny=False, is_egg=False, ability_id=1, nature_id=1, item_id=0,
                   moves=[dict(id=1, pp=10)] * 4, ivs=list(neutral().ivs), evs=[0] * 6,
                   identity=asdict(neutral()))
        # Use JSON validation for the actual native wire tuples.
        import json
        before = ParsedPokemon.model_validate_json(json.dumps(raw))
        first = reconcile(incoming=(observation(trusted_native_identity(
            before.identity, trainer=TRAINER, is_egg=before.is_egg)),))
        for changes in (dict(level=40), dict(species_id=652), dict(nickname="After"),
                        dict(moves=[dict(id=15, pp=20)] * 4), dict(item_id=50), dict(form=1)):
            changed = ParsedPokemon.model_validate_json(json.dumps(raw | changes))
            current = trusted_native_identity(changed.identity, trainer=TRAINER, is_egg=changed.is_egg)
            binding = reconcile(entities(first), (observation(current),)).bindings[0]
            self.assertEqual(binding.pokemon_entity_id, first.bindings[0].pokemon_entity_id)

    def test_slot_replacement_allocates_only_distinct_unique_evidence(self):
        previous = entities(reconcile())
        result = reconcile(previous, (observation(evidence(pid=88, encryption_constant=77)),))
        self.assertEqual(result.bindings[0].outcome, "NEW")
        self.assertNotEqual(result.bindings[0].pokemon_entity_id, previous[0].id)
        self.assertEqual(result.missing_entity_ids, (previous[0].id,))

    def test_first_sight_clones_and_either_identifier_collision_never_allocate(self):
        for changed in (evidence(), evidence(pid=88), evidence(encryption_constant=77),
                        evidence(ivs=(31,) * 6)):
            result = reconcile(incoming=(observation(), observation(changed, slot=2)))
            self.assertTrue(all(b.outcome == "AMBIGUOUS" and b.pokemon_entity_id is None
                                and not b.candidate_entity_ids for b in result.bindings))

    def test_similar_but_distinct_identifiers_do_not_merge(self):
        result = reconcile(incoming=(observation(), observation(evidence(pid=88, encryption_constant=77), slot=2)))
        self.assertEqual(len({b.authoritative_id() for b in result.bindings}), 2)

    def test_changed_immutable_core_and_either_collision_remain_unresolved(self):
        previous = entities(reconcile())
        for change in (dict(pid=88), dict(encryption_constant=77), dict(ivs=(31,) * 6),
                       dict(ot_tid=99), dict(origin_version=25), dict(format=7),
                       dict(met_location=11), dict(met_level=6), dict(met_date="2026-02-03")):
            binding = reconcile(previous, (observation(evidence(**change)),)).bindings[0]
            self.assertEqual(binding.outcome, "AMBIGUOUS")
            self.assertEqual(binding.candidate_entity_ids, (previous[0].id,))

    def test_clone_disappearing_cannot_unpoison_first_sight_ambiguity(self):
        first = reconcile(incoming=(observation(), observation(slot=2)))
        unresolved = tuple(b.observation.evidence for b in first.bindings)
        later = reconcile(incoming=(observation(source="box", box=3, slot=4),),
                          unresolved_evidence=unresolved)
        self.assertEqual(later.bindings[0].outcome, "AMBIGUOUS")
        # The retained poison must also survive an empty intermediate save.
        self.assertEqual(reconcile(incoming=(), unresolved_evidence=unresolved).bindings, ())
        self.assertEqual(reconcile(unresolved_evidence=unresolved).bindings[0].outcome, "AMBIGUOUS")

    def test_missing_and_ambiguous_entities_do_not_silently_reappear(self):
        entity = entities(reconcile())[0]
        for status in ("missing", "ambiguous"):
            binding = reconcile((replace(entity, identity_status=status),)).bindings[0]
            self.assertEqual(binding.outcome, "AMBIGUOUS")
            self.assertIsNone(binding.pokemon_entity_id)

    def test_eggs_hatching_and_incomplete_native_met_facts_are_unknown(self):
        for change in (dict(is_egg=True), dict(egg_location=60002), dict(egg_date="2026-01-01"),
                       dict(met_location=None), dict(met_location=0), dict(met_level=None),
                       dict(met_level=0), dict(met_date=None), dict(egg_location=None)):
            value = evidence(**change)
            self.assertIsNotNone(value.unresolved_reason)
            self.assertEqual(reconcile(incoming=(observation(value),)).bindings[0].outcome, "AMBIGUOUS")
        egg = evidence(is_egg=True, egg_location=60002, egg_date="2026-01-01")
        hatched = replace(egg, is_egg=False, met_location=20, met_date="2026-01-03")
        self.assertEqual(reconcile(incoming=(observation(hatched),),
                                   unresolved_evidence=(egg,)).bindings[0].outcome, "AMBIGUOUS")

    def test_native_evidence_fails_closed_on_invalid_values(self):
        for change in (dict(schema_version=1), dict(format=5), dict(pid=True), dict(encryption_constant=None),
                       dict(encryption_constant=-1), dict(ivs=(32,) * 6), dict(ot_name=" "),
                       dict(is_egg=1), dict(source_trainer_match=1), dict(met_date="2026-02-30"),
                       dict(met_level=101), dict(egg_location=-1)):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                evidence(**change)
        self.assertEqual(evidence(pid=0, encryption_constant=0).pid, 0)

    def test_unknown_binding_cannot_be_a_competitive_target(self):
        binding = reconcile(incoming=(observation(evidence(is_egg=True)),)).bindings[0]
        with self.assertRaisesRegex(ValueError, "ambiguous_pokemon_identity"):
            binding.authoritative_id()

    def test_private_collection_dto_reads_schema2_without_public_evidence(self):
        from app.domain.pokemon import PrivatePokemon
        native = evidence()
        pokemon = PrivatePokemon(species="Chespin", identity_evidence=asdict(native))
        self.assertEqual(pokemon.identity_evidence, native)
        public = asdict(pokemon.to_public())
        for private in ("identity_evidence", "ivs", "evs", "ability", "nature"):
            self.assertNotIn(private, public)

    def test_gen3_5_historical_evidence_shape_and_digest_are_unchanged(self):
        old = PokemonIdentityEvidence(1, 5, 123456789, 12345, 6789, 20, 2, "Fixture", 0,
                                      ivs=(17, 0, 0, 0, 0, 0))
        self.assertEqual(old.candidate_key, "240b974641e3fe1fc1d72f92f137b0dbd745e3f740e2132cf96fb3c273b9d926")
        self.assertEqual(digest(asdict(old)), "b19484011b6b7c31c95a388e356955f2e6bb0cd0d6256d3529fdaafbfba51f34")
        self.assertNotIn("is_egg", asdict(old))
        self.assertNotIn("source_trainer_match", asdict(old))
        self.assertEqual(identity_evidence_from_dict(asdict(old)), old)


if __name__ == "__main__":
    unittest.main()
