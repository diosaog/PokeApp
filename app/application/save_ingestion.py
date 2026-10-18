"""Original bytes → isolated server parser → existing authoritative V2 save model."""

from dataclasses import asdict
from hashlib import sha256
from threading import BoundedSemaphore
from uuid import NAMESPACE_URL, uuid5

from app.domain.pokemon_identity import (
    PokemonEntity,
    PokemonIdentityEvidence,
    digest,
    reconcile_pokemon,
)
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.files import MAX_SAVE_BYTES
from app.save_parser.models import SaveError, progress_evidence
from app.save_parser.registration import SaveRegistration, observation_digest


def reject(code, status=409):
    raise SeasonAdminRejected(code, status)


def parsed_payload(observation, save_id, trainer_id, raw_hash):
    """Neutral slot envelope already consumed by PC, identity and progress reads."""

    def stats(values):
        return dict(zip(("hp", "atk", "defense", "spa", "spd", "spe"), values))

    def pokemon(p):
        if p is None:
            return None
        value = {
            "species": f"Pokémon #{p.species_id}",
            "nickname": p.nickname,
            "level": p.level,
            "types": [],
            "item": f"Item #{p.item_id}" if p.item_id else "",
            "moves": [{"name": f"Move #{m.id}", "pp": m.pp} for m in p.moves if m.id],
            "is_shiny": p.shiny,
            "ability": f"Ability #{p.ability_id}",
            "nature": f"Nature #{p.nature_id}",
            "ivs": stats(p.ivs),
            "evs": stats(p.evs),
            "identity_evidence": asdict(p.identity),
            "legacy_fingerprints": [],
        }
        if observation.game in {"OR", "AS", "SN", "MN", "US", "UM"}:
            # Public form/type facts from the same trusted parser, never inferred
            # from nickname or from another game's species table.
            value.update(form=p.form, item_generation=observation.generation)
            value["types"] = list(dict.fromkeys(f"Type #{t}" for t in p.type_ids))
        return value

    return {
        "save_record_id": save_id,
        "trainer_id": trainer_id,
        "source_hash": raw_hash,
        "game": observation.game,
        "generation": observation.generation,
        "trainer": observation.trainer.model_dump(mode="json"),
        "observed_progress": progress_evidence(observation, raw_hash),
        "party": [
            {"slot_number": i, "pokemon": pokemon(p)}
            for i, p in enumerate(observation.party, 1)
        ],
        "boxes": [
            {
                "box_number": b.number,
                "slots": [
                    {"slot_number": i, "pokemon": pokemon(p)}
                    for i, p in enumerate(b.slots, 1)
                ],
            }
            for b in observation.boxes
        ],
    }


class TrustedSaveIngestion:
    def __init__(self, repository, parser):
        self.repository, self.parser = repository, parser
        self.slots = BoundedSemaphore(2)

    def context(self, season_id, trainer_id):
        context = self.repository.execute(
            "context", {"season_id": season_id, "trainer_id": trainer_id}
        )
        return {"current_save_id": context["current_save_id"]}

    def receipt(self, season_id, trainer_id, raw_hash):
        return SaveRegistration.model_validate(
            self.repository.execute(
                "receipt",
                {"season_id": season_id, "trainer_id": trainer_id, "sha256": raw_hash},
            )
        )

    def receive(
        self, season_id, trainer_id, raw_hash, expected_save_id, local_digest, data
    ):
        if not data or len(data) > MAX_SAVE_BYTES:
            reject("INVALID_SAVE_SIZE", 413)
        if sha256(data).hexdigest() != raw_hash:
            reject("SAVE_HASH_MISMATCH")
        if not self.slots.acquire(blocking=False):
            reject("SAVE_PARSER_BUSY", 429)
        try:
            return self._receive(
                season_id, trainer_id, raw_hash, expected_save_id, local_digest, data
            )
        finally:
            self.slots.release()

    def _receive(self, sid, tid, raw_hash, expected, local_digest, data):
        scope = {"season_id": sid, "trainer_id": tid}
        # Reconciliation before parsing/storage. Never rewind a newer current save on replay.
        try:
            receipt = self.receipt(sid, tid, raw_hash)
        except SeasonAdminRejected as error:
            if error.status != 404:
                raise
        else:
            if receipt.observation_digest != local_digest:
                reject("SAVE_PARSE_MISMATCH")
            return receipt
        context = self.repository.execute("context", scope)
        if context["current_save_id"] != expected:
            reject("SAVE_CONTEXT_CHANGED")
        try:
            observed = self.parser.parse(data)
        except SaveError as error:
            reject(error.code.value, 422)
        observed_digest = observation_digest(observed, self.parser.version)
        if observed_digest != local_digest:
            reject("SAVE_PARSE_MISMATCH")
        identity = {
            "game": observed.game,
            "trainer": observed.trainer.model_dump(mode="json"),
        }
        if (
            context["save_identity"] is not None
            and context["save_identity"] != identity
        ):
            reject("SAVE_TRAINER_MISMATCH")
        if context["current_save_id"] is not None and context["save_identity"] is None:
            reject("SAVE_IDENTITY_UNPROVEN")
        save_id = str(uuid5(NAMESPACE_URL, f"pokeapp:save:{sid}:{tid}:{raw_hash}"))
        parsed_id = str(
            uuid5(NAMESPACE_URL, f"pokeapp:parsed:{save_id}:{self.parser.version}")
        )
        payload = parsed_payload(observed, save_id, tid, raw_hash)
        plan = None
        if observed.generation < 6:
            incoming = observed.identity_observations()
            previous = tuple(
                PokemonEntity(
                    r["id"],
                    PokemonIdentityEvidence(**r["initial_evidence"]),
                    r["identity_status"],
                )
                for r in context["entities"]
            )
            reconciliation = reconcile_pokemon(previous, incoming, save_file_id=save_id)
            head = context["head"]
            plan = dict(
                **scope,
                save_file_id=save_id,
                parsed_save_id=parsed_id,
                parsed_payload=payload,
                expected_predecessor_id=head["id"] if head else None,
                capture_stream_id=head["capture_stream_id"]
                if head
                else str(uuid5(NAMESPACE_URL, f"pokeapp:accept:{sid}:{tid}")),
                capture_sequence=head["capture_sequence"] + 1 if head else 1,
                identity_schema_version=1,
                reconciliation_version=1,
                input_signature=digest([asdict(o) for o in incoming]),
                bindings=[],
            )
            for binding in reconciliation.bindings:
                obs = binding.observation
                plan["bindings"].append(
                    {
                        **asdict(obs.location),
                        "outcome": binding.outcome,
                        "pokemon_entity_id": binding.pokemon_entity_id,
                        "candidate_entity_ids": list(binding.candidate_entity_ids),
                        "evidence": asdict(obs.evidence),
                        "candidate_key": obs.evidence.candidate_key,
                        "observation_signature": obs.signature,
                        "legacy_fingerprints": [],
                    }
                )
        # 'trusted' prefix is deliberately outside browser-owned Storage path policies.
        key = f"trusted/{tid}/{sid}/{raw_hash}.sav"
        request = dict(
            **scope,
            sha256=raw_hash,
            save_id=save_id,
            parsed_id=parsed_id,
            expected_save_id=expected,
            storage_key=key,
            parser_version=self.parser.version,
            observation_digest=observed_digest,
            save_identity=identity,
            payload=payload,
            identity_plan=plan,
        )
        self.repository.store_raw(key, data, raw_hash)
        return SaveRegistration.model_validate(
            self.repository.execute("register", request)
        )
