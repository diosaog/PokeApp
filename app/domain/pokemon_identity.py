"""Versioned, private read-only evidence and conservative individual reconciliation."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid5

IDENTITY_SCHEMA_VERSION = 1
RECONCILIATION_VERSION = 1
NATIVE_IDENTITY_SCHEMA_VERSION = 2
NATIVE_RECONCILIATION_VERSION = 2


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


@dataclass(frozen=True)
class TrustedNativeIdentityEvidence(PokemonIdentityEvidence):
    """Private Gen6/7 reconciliation input, derived only by trusted ingestion.

    This is intentionally separate from the unchanged neutral reader wire shape.
    The evidence supports a scoped association; it is not a globally unique ID
    or proof that the source was never edited, cloned or traded.
    """

    is_egg: bool = False
    source_trainer_match: bool = False

    def __post_init__(self):
        if (type(self.schema_version) is not int or self.schema_version != 2
                or type(self.format) is not int or self.format not in (6, 7)):
            raise ValueError("unsupported_native_identity_evidence")
        for name, upper in (("pid", 2**32 - 1), ("encryption_constant", 2**32 - 1),
                            ("ot_tid", 65535), ("ot_sid", 65535), ("origin_version", 255),
                            ("language", 255), ("ot_gender", 1)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= upper:
                raise ValueError("invalid_identity_" + name)
        if (not isinstance(self.ot_name, str) or not self.ot_name.strip()
                or self.origin_version == 0 or self.language == 0):
            raise ValueError("incomplete_identity_evidence")
        if type(self.is_egg) is not bool or type(self.source_trainer_match) is not bool:
            raise ValueError("invalid_native_identity_context")
        object.__setattr__(self, "ivs", tuple(self.ivs))
        if len(self.ivs) != 6 or any(type(v) is not int or not 0 <= v <= 31 for v in self.ivs):
            raise ValueError("invalid_identity_ivs")
        for name, upper in (("met_location", 65535), ("met_level", 100), ("egg_location", 65535)):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or not 0 <= value <= upper):
                raise ValueError("invalid_identity_" + name)
        for name in ("met_date", "egg_date"):
            value = getattr(self, name)
            if value is not None:
                from datetime import date
                if not isinstance(value, str):
                    raise ValueError("invalid_identity_" + name)
                date.fromisoformat(value)

    @property
    def candidate_key(self) -> str:
        # Native IVs, met and egg facts are guards, not tie-breakers for clones.
        # Visible species/form/name/stats/moves/location never enter this key.
        return digest(asdict(self))

    @property
    def unresolved_reason(self) -> str | None:
        if not self.source_trainer_match:
            return "original_trainer_unproven"
        if self.is_egg or self.egg_location not in (None, 0) or self.egg_date is not None:
            return "egg_or_hatch_unproven"
        if (self.met_location in (None, 0) or self.met_level in (None, 0)
                or self.met_date is None or self.egg_location is None):
            return "incomplete_native_identity"
        return None


def identity_evidence_from_dict(value: dict) -> PokemonIdentityEvidence:
    """Reconstruct persisted evidence without changing any schema-1 digest."""
    identity_type = TrustedNativeIdentityEvidence if value.get("schema_version") == 2 else PokemonIdentityEvidence
    return identity_type(**value)


def trusted_native_identity(evidence, *, trainer, is_egg: bool) -> TrustedNativeIdentityEvidence:
    """Promote neutral evidence after server parsing, never from a browser claim.

    The caller must already have established save ownership and native integrity.
    Exact OT/name/language comparison deliberately leaves uncertain trades unknown.
    """
    raw = asdict(evidence)
    if raw.get("schema_version") != 1 or raw.get("format") not in (6, 7):
        raise ValueError("unsupported_native_identity_evidence")
    def trainer_value(name):
        return trainer.get(name) if isinstance(trainer, dict) else getattr(trainer, name, None)
    matches = all(raw[key] == trainer_value(name) for key, name in (
        ("ot_name", "name"), ("ot_tid", "tid"), ("ot_sid", "sid"),
        ("ot_gender", "gender"), ("language", "language"),
    ))
    return TrustedNativeIdentityEvidence(**(raw | {
        "schema_version": 2, "is_egg": is_egg, "source_trainer_match": matches,
    }))


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
                      *, save_file_id: str,
                      unresolved_evidence: tuple[PokemonIdentityEvidence, ...] = ()) -> Reconciliation:
    """Previous is the scoped head state, including retained missing entities."""
    namespace = UUID(save_file_id)
    if len({p.id for p in previous}) != len(previous) or len({p.location for p in incoming}) != len(incoming):
        raise ValueError("duplicate_identity_input")
    if any(isinstance(p.evidence, TrustedNativeIdentityEvidence) for p in (*previous, *incoming)) or unresolved_evidence:
        return _reconcile_native(previous, incoming, namespace, unresolved_evidence)
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


def native_identity_collision(a: PokemonIdentityEvidence, b: PokemonIdentityEvidence) -> bool:
    """Either identifier colliding is enough to forbid automatic allocation."""
    return a.pid == b.pid or (a.encryption_constant is not None
                             and a.encryption_constant == b.encryption_constant)


def _reconcile_native(previous, incoming, namespace, unresolved_evidence):
    if any(not isinstance(obs.evidence, TrustedNativeIdentityEvidence) for obs in incoming):
        raise ValueError("mixed_identity_schema")
    by_pid, by_ec = defaultdict(list), defaultdict(list)
    for entity in previous:
        by_pid[entity.evidence.pid].append(entity)
        if entity.evidence.encryption_constant is not None:
            by_ec[entity.evidence.encryption_constant].append(entity)
    pid_counts = Counter(obs.evidence.pid for obs in incoming)
    ec_counts = Counter(obs.evidence.encryption_constant for obs in incoming)
    unresolved_pids = {old.pid for old in unresolved_evidence}
    unresolved_ecs = {old.encryption_constant for old in unresolved_evidence
                      if old.encryption_constant is not None}
    bindings, seen = [], set()
    for obs in sorted(incoming, key=lambda value: value.location):
        evidence = obs.evidence
        candidates = list({entity.id: entity for entity in (
            *by_pid[evidence.pid], *by_ec[evidence.encryption_constant],
        )}.values())
        unique = pid_counts[evidence.pid] == 1 and ec_counts[evidence.encryption_constant] == 1
        poisoned = evidence.pid in unresolved_pids or evidence.encryption_constant in unresolved_ecs
        if evidence.unresolved_reason is not None or not unique or poisoned:
            outcome = "AMBIGUOUS"
        elif not candidates:
            outcome = "NEW"
        elif (len(candidates) == 1 and candidates[0].identity_status == "unambiguous"
              and candidates[0].evidence.candidate_key == evidence.candidate_key):
            outcome = "MATCHED"
        else:
            outcome = "AMBIGUOUS"
        if outcome == "NEW":
            # Allocation is stable on retries of this accepted save. The UUID is
            # an application ID, not a claim that the native evidence is global.
            binding = PokemonBinding(obs, outcome, str(uuid5(namespace, "pokeapp-identity-v2:" + evidence.candidate_key)))
        elif outcome == "MATCHED":
            binding = PokemonBinding(obs, outcome, candidates[0].id)
            seen.add(candidates[0].id)
        else:
            ids = tuple(sorted(entity.id for entity in candidates))
            binding = PokemonBinding(obs, outcome, None, ids)
            seen.update(ids)
        bindings.append(binding)
    return Reconciliation(tuple(bindings), tuple(sorted(entity.id for entity in previous if entity.id not in seen)))


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
