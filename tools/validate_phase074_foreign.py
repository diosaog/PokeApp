"""Foreign-OT training continuity through actual native bytes and PostgreSQL.

The already-committed transfer is an explicitly synthetic relational fixture,
not a claim that a real physical robbery was accepted. Two training operations
use the real service, immutable supplied native executable and real SQL; a later
ordinary native quick-item save synchronization must retain UUID and flags.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.save_ingestion import registration_request
from app.application.training import VirtualTraining
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.write_models import WriteIntent
from app.save_parser.writer import PkhexProcessWriter
from tools.phase30_release_audit import SupabaseLikePG
from tools.validate_phase074_concurrency import connection, rpc

ROOT = Path(__file__).resolve().parents[1]


def validate(pg, executable, fixture):
    parser, native = PkhexProcessParser(executable), PkhexProcessWriter(executable)
    donor_bytes = (fixture / "donor-source").read_bytes()
    empty_bytes = (fixture / "recipient-empty").read_bytes()
    received_bytes = (fixture / "recipient-received").read_bytes()
    donor_observed, empty_observed, received_observed = map(parser.parse, (donor_bytes, empty_bytes, received_bytes))
    assert donor_observed.trainer != received_observed.trainer
    assert donor_observed.party[0].identity == received_observed.party[0].identity
    sid, donor, recipient, donor_player, recipient_player, authority, robbery = (str(uuid4()) for _ in range(7))
    blobs = {}
    checks = []
    with connection(pg, autocommit=False) as conn:
        try:
            for tid, name in ((donor, "074 Foreign Donor"), (recipient, "074 Foreign Recipient")):
                conn.execute("insert into public.trainers(id,display_name,slug,is_admin,auth_user_id) values(%s,%s,%s,true,%s)",
                             (tid, name, "074-foreign-" + tid, str(uuid4())))
            conn.execute("insert into public.seasons(id,name,status,started_at,created_by_trainer_id) values(%s,'074 foreign fixture','active',now(),%s)", (sid, donor))
            conn.execute("insert into public.season_players(id,season_id,trainer_id,status) values(%s,%s,%s,'active'),(%s,%s,%s,'active')",
                         (donor_player, sid, donor, recipient_player, sid, recipient))
            conn.execute("insert into public.season_player_stats(season_player_id,season_id,trainer_id) select id,season_id,trainer_id from public.season_players where season_id=%s", (sid,))

            def register(tid, data, observation):
                context = rpc(conn, "api_register_save", dict(operation="context", season_id=sid, trainer_id=tid))
                request = registration_request(sid, tid, sha256(data).hexdigest(), context["current_save_id"], observation, parser.version, context)
                blobs[request["storage_key"]] = data
                result = rpc(conn, "api_register_save", request | {"operation": "register"})
                return request, result

            donor_initial, _ = register(donor, donor_bytes, donor_observed)
            recipient_initial, _ = register(recipient, empty_bytes, empty_observed)
            entity, donor_head = conn.execute("select pokemon_entity_id::text,revision_id::text from public.pokemon_observations"
                " where save_file_id=%s and source='party' and slot_number=1", (donor_initial["save_id"],)).fetchone()
            assert entity is not None
            original_evidence = conn.execute("select initial_evidence from public.pokemon_entities where id=%s", (entity,)).fetchone()[0]
            assert original_evidence["source_trainer_match"] is True
            # A paid robbery purchase and its already verified provenance are
            # relational test setup only. No production verifier permit is used.
            conn.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)"
                " select %s,%s,%s,%s,id,1,base_price,'paid','used' from public.shop_items where code='robar_pokemon'",
                (robbery, sid, recipient, recipient_player))
            conn.execute("insert into public.item_use_authorizations(id,operation_id,idempotency_key,purchase_id,season_id,trainer_id,"
                "target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code,status)"
                " values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'steal','APPLIED_VERIFIED')",
                (authority, authority, authority, robbery, sid, recipient, entity, recipient_initial["save_id"], recipient_initial["sha256"], donor_head))
            conn.execute("insert into public.item_use_transfers(authorization_id,donor_id,terminal) values(%s,%s,'COMMITTED')", (authority, donor))
            legacy_flag = str(uuid4())
            conn.execute("insert into public.pokemon_flags(id,season_id,trainer_id,season_player_id,fingerprint,flag_type,flag_value)"
                " values(%s,%s,%s,%s,%s,'blindado',true)", (legacy_flag, sid, donor, donor_player, "074-foreign-" + entity))
            conn.execute("insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,legacy_flag_id)"
                " values(%s,%s,%s,'blindado',%s)", (sid, donor, entity, legacy_flag))
            conn.execute("insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)"
                " values(%s,%s,%s,'robado',true)", (sid, donor, entity))
            flags = conn.execute("select jsonb_agg(to_jsonb(f) order by id) from public.pokemon_entity_flags f where pokemon_entity_id=%s", (entity,)).fetchone()[0]
            conn.execute("insert into public.transfer_provenance(authorization_id,pokemon_entity_id,season_id,donor_id,recipient_id,evidence,originals,results,proofs,original_flags)"
                " values(%s,%s,%s,%s,%s,%s,'{}','{}','{}',%s)", (authority, entity, sid, donor, recipient, Jsonb(original_evidence), Jsonb(flags)))
            conn.execute("update public.pokemon_entities set owner_trainer_id=%s where id=%s", (recipient, entity))
            conn.execute("update public.pokemon_entity_flags set trainer_id=%s where pokemon_entity_id=%s", (recipient, entity))
            register(recipient, received_bytes, received_observed)
            canonical = conn.execute("select initial_evidence from public.pokemon_entities where id=%s", (entity,)).fetchone()[0]
            observed_flag = conn.execute("select evidence->'source_trainer_match' from public.pokemon_observations where save_file_id="
                "(select current_save_file_id from public.season_players where id=%s) and pokemon_entity_id=%s", (recipient_player, entity)).fetchone()[0]
            assert canonical["source_trainer_match"] is True and observed_flag is False
            original_flags = conn.execute("select jsonb_agg(to_jsonb(f) order by id) from public.pokemon_entity_flags f where pokemon_entity_id=%s", (entity,)).fetchone()[0]
            provenance = conn.execute("select to_jsonb(p) from public.transfer_provenance p where authorization_id=%s", (authority,)).fetchone()[0]
            original_observations = conn.execute("select jsonb_agg(to_jsonb(o) order by id) from public.pokemon_observations o where pokemon_entity_id=%s", (entity,)).fetchone()[0]
            checks.append("foreign received bytes match existing UUID via committed relational proof; canonical True and observed False")

            class Repository:
                def execute(self, action, season_id, trainer_id, **values):
                    try:
                        with conn.transaction():
                            return rpc(conn, "api_training_operation", dict(operation=action, season_id=season_id, trainer_id=trainer_id, **values))
                    except Exception as error:
                        if getattr(error, "sqlstate", "").startswith("PT"):
                            raise SeasonAdminRejected(error.diag.message_primary.upper(), int(error.sqlstate[2:])) from None
                        raise

                def read_source(self, saved):
                    data = blobs[saved["storage_key"]]
                    assert sha256(data).hexdigest() == saved["sha256"]
                    return data

                def store_raw(self, key, data, expected_hash):
                    assert sha256(data).hexdigest() == expected_hash
                    assert key not in blobs or blobs[key] == data
                    blobs[key] = data

            service = VirtualTraining(Repository(), parser, native)
            current_bytes = received_bytes
            for stat in ("hp", "atk"):
                purchase, operation = str(uuid4()), str(uuid4())
                conn.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)"
                    " select %s,%s,%s,%s,id,1,6,'paid','pending' from public.shop_items where code='chapa_plateada'", (purchase, sid, recipient, recipient_player))
                listing = service.listing(sid, recipient)
                assert any(target["pokemon_entity_id"] == entity for target in listing["targets"])
                body = dict(purchase_id=purchase, pokemon_entity_id=entity, source_sha256=sha256(current_bytes).hexdigest(),
                            change=dict(kind="iv", stat=stat, nature_id=None))
                reserved = service.reserve(sid, recipient, operation, body)
                intent = WriteIntent.create(**reserved["intent"])
                prepared = native.prepare(current_bytes, intent)
                applied = service.complete(sid, recipient, operation, prepared.output)
                assert applied["status"] == "APPLIED"
                assert service.complete(sid, recipient, operation, prepared.output) == applied
                current_bytes = prepared.output
                canonical = conn.execute("select initial_evidence from public.pokemon_entities where id=%s", (entity,)).fetchone()[0]
                observed_flag = conn.execute("select evidence->'source_trainer_match' from public.pokemon_observations where save_file_id="
                    "(select current_save_file_id from public.season_players where id=%s) and pokemon_entity_id=%s", (recipient_player, entity)).fetchone()[0]
                assert canonical["source_trainer_match"] is True and observed_flag is False
                assert conn.execute("select public.transfer_identity_proven(%s,%s,%s)", (entity, recipient, Jsonb(canonical))).fetchone()[0]
                assert conn.execute("select status from public.purchases where id=%s", (purchase,)).fetchone()[0] == "used"
                checks.append(f"actual native silver {stat}: real service and atomic SQL consume once, same foreign entity UUID/proof")

            # Produce a genuinely new ordinary save, leaving all Pokemon intact.
            # Quick items keep their existing free contract and require no purchase.
            inventory = native.inventory(current_bytes)
            item = next(name for name, info in inventory["items"].items() if info["addable"] > 0)
            description = native.inspect_training(current_bytes, "party", None, 0)
            ordinary_intent = WriteIntent.create(game="Y", expected_sha256=sha256(current_bytes).hexdigest(),
                trainer_key=description["trainer_key"], mutation=dict(kind="add_item", item=item, quantity=1,
                expected_count=inventory["items"][item]["count"]))
            ordinary = native.prepare(current_bytes, ordinary_intent).output
            register(recipient, ordinary, parser.parse(ordinary))
            latest_entity = conn.execute("select initial_evidence,identity_status,owner_trainer_id::text from public.pokemon_entities where id=%s", (entity,)).fetchone()
            assert latest_entity[0]["ivs"][0:2] == [31, 31] and latest_entity[1:] == ("unambiguous", recipient)
            assert conn.execute("select jsonb_agg(to_jsonb(f) order by id) from public.pokemon_entity_flags f where pokemon_entity_id=%s", (entity,)).fetchone()[0] == original_flags
            assert conn.execute("select to_jsonb(p) from public.transfer_provenance p where authorization_id=%s", (authority,)).fetchone()[0] == provenance
            assert conn.execute("select jsonb_agg(to_jsonb(o) order by id) from public.pokemon_observations o where id=any(%s)",
                ([row["id"] for row in original_observations],)).fetchone()[0] == original_observations
            assert conn.execute("select count(*) from public.training_operations where pokemon_entity_id=%s and status='APPLIED'", (entity,)).fetchone()[0] == 2
            checks.append("later ordinary native quick-item synchronization keeps trained IVs, original UUID, legacy flag links and immutable transfer provenance")
            return {"pass": True, "checks": checks, "game": "Y", "parser_sha256": sha256(executable.read_bytes()).hexdigest(),
                    "boundary": "Actual native/parser/service/SQL training; prior committed transfer is a synthetic relational fixture, not physical robbery acceptance."}
        finally:
            conn.rollback()


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--pg-bin", type=Path, required=True)
    args.add_argument("--native", type=Path, required=True)
    args.add_argument("--fixtures", type=Path, required=True)
    args.add_argument("--evidence", type=Path, required=True)
    args.add_argument("--port", type=int, default=55676)
    options = args.parse_args()
    pg = SupabaseLikePG(options.pg_bin, options.port)
    try:
        pg.start()
        for migration in sorted((ROOT / "supabase/v2/migrations").glob("*.sql")):
            pg.sql(migration.read_text(encoding="utf-8"))
        result = validate(pg, options.native, options.fixtures)
    finally:
        pg.stop()
    options.evidence.parent.mkdir(parents=True, exist_ok=True)
    options.evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS foreign-OT native/service/SQL: two trainings, replay and later ordinary synchronization; flags/provenance retained")


if __name__ == "__main__":
    main()
