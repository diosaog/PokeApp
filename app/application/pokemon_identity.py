"""Opt-in V2 parsed-save identity boundary. No legacy upload or API wiring."""
from dataclasses import asdict
from typing import Protocol

from app.domain.pokemon_identity import (
    CaptureOrder, ParsedPokemonObservation, PokemonEntity, PokemonIdentityEvidence,
    PokemonLocation, digest, reconcile_pokemon,
)
from app.repositories.errors import ConflictError


class PokemonIdentityRepository(Protocol):
    def load_context(self, *, season_id: str, trainer_id: str, parsed_save_id: str) -> dict: ...
    def commit(self, request: dict) -> dict: ...


def observations_from_payload(payload: dict) -> tuple[ParsedPokemonObservation, ...]:
    """V2 slot DTO shape only; absent evidence is rejected, not guessed."""
    from pkmmeta import pokemon_fingerprint, pokemon_fingerprint_stable

    result = []
    def add(raw, location):
        if raw is None:
            return
        evidence = PokemonIdentityEvidence(**raw['identity_evidence'])
        # These are locators supplied/computed by parser, never authoritative IDs.
        locators = raw.get('legacy_fingerprints')
        if locators is None:
            locators = [pokemon_fingerprint(raw), pokemon_fingerprint_stable(raw)]
        if not isinstance(locators, (tuple, list)) or any(not isinstance(v, str) or not v for v in locators):
            raise ValueError('invalid_legacy_locators')
        result.append(ParsedPokemonObservation(location, evidence, tuple(sorted(set(locators)))))

    if not isinstance(payload, dict) or 'party' not in payload or 'boxes' not in payload:
        raise ValueError('complete_parsed_observations_required')
    for slot in payload['party']:
        add(slot['pokemon'], PokemonLocation('party', 0, slot['slot_number']))
    for box in payload['boxes']:
        for slot in box['slots']:
            add(slot['pokemon'], PokemonLocation('box', box['box_number'], slot['slot_number']))
    return tuple(sorted(result, key=lambda o: o.location))


def reconcile_parsed_save(repository: PokemonIdentityRepository, *, season_id: str, trainer_id: str,
                          parsed_save_id: str, capture_order: CaptureOrder | None = None) -> dict:
    if not isinstance(capture_order, CaptureOrder):
        raise ConflictError('trusted_capture_order_required')
    context = repository.load_context(season_id=season_id, trainer_id=trainer_id, parsed_save_id=parsed_save_id)
    parsed, saved, head = context['parsed'], context['save'], context['head']
    if saved['season_id'] != season_id or saved['trainer_id'] != trainer_id or parsed['save_file_id'] != saved['id']:
        raise ConflictError('identity_scope_mismatch')
    try:
        incoming = observations_from_payload(parsed['payload'])
        previous = tuple(PokemonEntity(row['id'], PokemonIdentityEvidence(**row['initial_evidence']), row['identity_status'])
                         for row in context['entities'])
        plan = reconcile_pokemon(previous, incoming, save_file_id=saved['id'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConflictError('invalid_identity_source') from exc
    request = dict(season_id=season_id, trainer_id=trainer_id, save_file_id=saved['id'],
                   parsed_save_id=parsed_save_id, parsed_payload=parsed['payload'],
                   expected_predecessor_id=head['id'] if head else None,
                   capture_stream_id=capture_order.stream_id, capture_sequence=capture_order.sequence,
                   identity_schema_version=1, reconciliation_version=1,
                   input_signature=digest([asdict(obs) for obs in incoming]), bindings=[])
    for binding in plan.bindings:
        obs = binding.observation
        request['bindings'].append({**asdict(obs.location), 'outcome': binding.outcome,
            'pokemon_entity_id': binding.pokemon_entity_id, 'candidate_entity_ids': list(binding.candidate_entity_ids),
            'evidence': asdict(obs.evidence), 'candidate_key': obs.evidence.candidate_key,
            'observation_signature': obs.signature, 'legacy_fingerprints': list(obs.legacy_fingerprints)})
    return repository.commit(request)
