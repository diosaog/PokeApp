"""Versioned, private read-only evidence and conservative individual reconciliation."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID, uuid5

IDENTITY_SCHEMA_VERSION = 1
RECONCILIATION_VERSION = 1


@dataclass(frozen=True)
class PokemonIdentityEvidence:
    schema_version: int
    format: int
    pid: int
    ot_tid: int
    ot_sid: int
    origin_version: int
    language: int
    ot_name: str
    ot_gender: int
    met_location: int | None = None
    met_level: int | None = None
    egg_location: int | None = None
    met_date: str | None = None
    egg_date: str | None = None
    encryption_constant: int | None = None
    ivs: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1 or type(self.format) is not int or self.format not in (3, 4, 5):
            raise ValueError("unsupported_identity_evidence")
        for name, upper in (("pid", 2**32-1), ("ot_tid", 65535), ("ot_sid", 65535),
                            ("origin_version", 255), ("language", 255), ("ot_gender", 1)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= upper:
                raise ValueError("invalid_identity_" + name)
        if not isinstance(self.ot_name, str) or not self.ot_name or self.origin_version == 0 or self.language == 0:
            raise ValueError("incomplete_identity_evidence")
        # EC in PK3/4/5 is an API alias of PID, not another independent identifier.
        if self.encryption_constant is not None:
            raise ValueError("independent_ec_not_supported_in_gen3_5")
        object.__setattr__(self, "ivs", tuple(self.ivs))
        if len(self.ivs) != 6 or any(type(v) is not int or not 0 <= v <= 31 for v in self.ivs):
            raise ValueError("invalid_identity_ivs")
        for name in ("met_location", "met_level", "egg_location"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid_identity_" + name)
        for name in ("met_date", "egg_date"):
            value = getattr(self, name)
            if value is not None:
                from datetime import date
                date.fromisoformat(value)

    @property
    def candidate_key(self) -> str:
        # No species, slot, IVs, met/egg data, gender, shiny or mutable stats.
        # Deliberately broad: same PID collisions remain ambiguous, not falsely new.
        return digest([self.schema_version, self.format, self.pid, self.ot_tid,
                       self.ot_sid, self.origin_version, self.language, self.ot_name, self.ot_gender])


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True, order=True)
class PokemonLocation:
    source: Literal["party", "box"]
    box_number: int
    slot_number: int

    def __post_init__(self):
        if self.source not in ("party", "box") or type(self.box_number) is not int or type(self.slot_number) is not int:
            raise ValueError("invalid_identity_location")
        if not 1 <= self.slot_number <= (6 if self.source == "party" else 30):
            raise ValueError("invalid_identity_slot")
        if (self.source == "party" and self.box_number != 0) or (self.source == "box" and self.box_number < 1):
            raise ValueError("invalid_identity_box")


@dataclass(frozen=True)
class ParsedPokemonObservation:
    location: PokemonLocation
    evidence: PokemonIdentityEvidence
    legacy_fingerprints: tuple[str, ...] = ()

    @property
    def signature(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class PokemonEntity:
    id: str
    evidence: PokemonIdentityEvidence
    identity_status: str = "unambiguous"

    def __post_init__(self):
        UUID(self.id)
        if self.identity_status not in ("unambiguous", "missing", "ambiguous"):
            raise ValueError("invalid_identity_status")


@dataclass(frozen=True)
class PokemonBinding:
    observation: ParsedPokemonObservation
    outcome: Literal["MATCHED", "NEW", "AMBIGUOUS"]
    pokemon_entity_id: str | None
    candidate_entity_ids: tuple[str, ...] = ()

    def authoritative_id(self) -> str:
        if self.outcome == "AMBIGUOUS" or not self.pokemon_entity_id:
            raise ValueError("ambiguous_pokemon_identity")
        return str(UUID(self.pokemon_entity_id))

    def bind(self, pokemon):
        """Creates a V2 DTO; never changes legacy DTOs or historical snapshots."""
        return replace(pokemon, id=self.authoritative_id())


@dataclass(frozen=True)
class Reconciliation:
    bindings: tuple[PokemonBinding, ...]
    missing_entity_ids: tuple[str, ...]


def reconcile_pokemon(previous: tuple[PokemonEntity, ...], incoming: tuple[ParsedPokemonObservation, ...],
                      *, save_file_id: str) -> Reconciliation:
    """Previous is the scoped head state, including retained missing entities."""
    namespace = UUID(save_file_id)
    if len({p.id for p in previous}) != len(previous) or len({p.location for p in incoming}) != len(incoming):
        raise ValueError("duplicate_identity_input")
    groups = defaultdict(list)
    for entity in previous:
        groups[entity.evidence.pid].append(entity)
    counts = Counter(o.evidence.pid for o in incoming)
    bindings, seen = [], set()
    for obs in sorted(incoming, key=lambda o: o.location):
        candidates = groups[obs.evidence.pid]
        if not candidates:
            # Initial allocation only; stable on retries/reparse of the SAME save.
            entity_id = str(uuid5(namespace, "pokeapp-identity-v1:" + digest(asdict(obs.location))))
            binding = PokemonBinding(obs, "NEW", entity_id)
        elif (len(candidates) == 1 and counts[obs.evidence.pid] == 1
              and candidates[0].evidence.candidate_key == obs.evidence.candidate_key
              and candidates[0].identity_status != "ambiguous"):
            binding = PokemonBinding(obs, "MATCHED", candidates[0].id)
            seen.add(candidates[0].id)
        else:
            ids = tuple(sorted(p.id for p in candidates))
            binding = PokemonBinding(obs, "AMBIGUOUS", None, ids)
            seen.update(ids)
        bindings.append(binding)
    return Reconciliation(tuple(bindings), tuple(sorted(p.id for p in previous if p.id not in seen)))


def unique_legacy_flag_targets(bindings: tuple[PokemonBinding, ...]) -> dict[str, str | None]:
    candidates = defaultdict(set)
    unresolved = set()
    for binding in bindings:
        for fingerprint in binding.observation.legacy_fingerprints:
            if binding.pokemon_entity_id:
                candidates[fingerprint].add(binding.pokemon_entity_id)
            else:
                unresolved.add(fingerprint)
    return {key: next(iter(ids)) if len(ids) == 1 and key not in unresolved else None
            for key, ids in candidates.items()} | {key: None for key in unresolved}


@dataclass(frozen=True)
class CaptureOrder:
    """Backend attestation, NOT an upload timestamp or browser-provided counter."""
    stream_id: str
    sequence: int

    def __post_init__(self):
        UUID(self.stream_id)
        if type(self.sequence) is not int or not 0 < self.sequence < 2**63:
            raise ValueError("trusted_capture_order_required")


def bind_parsed_save(parsed_save, plan: Reconciliation):
    """Return a new private ParsedSave. Ambiguous occurrences keep an empty ID.

    The accompanying plan is mandatory for status; effects must use the current
    database observation boundary, never treat an empty/legacy DTO ID as a target.
    """
    by_location = {b.observation.location: b for b in plan.bindings}
    def bind_slot(slot, location):
        if slot.pokemon is None:
            return slot
        binding = by_location[location]
        return replace(slot, pokemon=replace(slot.pokemon, id=binding.pokemon_entity_id or ''))
    party = tuple(bind_slot(slot, PokemonLocation('party',0,slot.slot_number)) for slot in parsed_save.party)
    boxes = tuple(replace(box, slots=tuple(bind_slot(slot, PokemonLocation('box',box.box_number,slot.slot_number))
                  for slot in box.slots)) for box in parsed_save.boxes)
    return replace(parsed_save, party=party, boxes=boxes)


@dataclass(frozen=True)
class IdentityResolutionDecision:
    """Future audited command contract only; no resolution execution in 8F.0."""
    observation_id: str
    pokemon_entity_id: str
    expected_head_revision_id: str
    actor_trainer_id: str
    reason: str
    evidence_reference: str

    def __post_init__(self):
        for name in ("observation_id", "pokemon_entity_id", "expected_head_revision_id", "actor_trainer_id"):
            UUID(getattr(self, name))
        if not self.reason.strip() or not self.evidence_reference.strip():
            raise ValueError("audited_identity_decision_required")
