"""Phase24A disposable PostgreSQL/native/Launcher gates. No remote credentials.

Engineering coordinator only: never certifies ownership completion or emulator.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import psycopg

from app.application.item_use_verification import VerificationRejected
from app.application.item_use_worker import SignedArtifactReader
from app.application.save_ingestion import TrustedSaveIngestion
from app.application.transfer_transport import TransferTransport
from app.application.transfer_verification import TransferVerification
from app.launcher.save_activity import SaveActivityGate
from app.launcher.transfer import EngineeringTransfer
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import (
    PRODUCTION_MUTATIONS,
    EngineeringCapability,
    LocalWriteEngine,
)
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.item_use import SupabaseItemUseRepository
from app.repositories.supabase.transfer import TransferRepository
from app.repositories.transfer_verifier_pg import TransferVerifierPG
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter
from tools.validate_accounts_local import LocalPG
from tools.validate_phase23_local import parity
from tools.validate_phase23c_local import LocalSourceStore, LocalVerifierStore
from tools.validate_phase23d_local import Blobs, rejected
from tools.validate_supabase_v2_identity_sql import LocalClient


def run(args, closure=None):
    pg = LocalPG(args.pg_bin, 55477 if closure else 55476)
    report = {"status": "RUNNING", "checks": [], "games": [], "cluster": str(pg.root)}
    worker = None

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

    try:
        pg.start()
        client = LocalClient(
            SimpleNamespace(
                psql=str(args.pg_bin / "psql.exe"),
                host="127.0.0.1",
                port=pg.port,
                user="postgres",
                password="",
                database="pokeapp_v2_validation_accounts",
            )
        )
        parser, native = (
            PkhexProcessParser(args.native_exe),
            PkhexProcessWriter(args.native_exe),
        )
        sources = LocalSourceStore(client)
        ingestion = TrustedSaveIngestion(sources, parser)
        store = LocalVerifierStore(pg, client, sources)
        repo = TransferRepository(client)
        pg.sql(
            "create role phase24_worker login nosuperuser nocreatedb nocreaterole nobypassrls; grant pokeapp_item_verifier to phase24_worker;"
        )
        worker = psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            dbname="pokeapp_v2_validation_accounts",
            user="phase24_worker",
            autocommit=True,
        )
        rpc = TransferVerifierPG(worker)
        blobs = Blobs(sources.blobs)
        reader = SignedArtifactReader(
            blobs.origin,
            client=httpx.Client(transport=httpx.MockTransport(blobs.serve)),
        )
        verifier = TransferVerification(
            rpc,
            lambda s: sources.blobs[s["storage_key"]],
            reader,
            parser,
            native,
            store_raw=sources.store_raw,
        )
        transport = TransferTransport(repo, blobs)

        def insert(table, row):
            return client.table(table).insert(row).execute().data[0]

        def setup(game):
            pg.sql(
                "update seasons set status='draft',started_at=null where status='active';"
            )
            sid = insert(
                "seasons",
                {
                    "name": "24A " + str(uuid4()),
                    "status": "active",
                    "started_at": "2026-10-01T00:00:00Z",
                },
            )["id"]
            scope = {"season_id": sid}
            for side in ("source", "destination"):
                tid = str(uuid4())
                insert(
                    "trainers",
                    {
                        "id": tid,
                        "display_name": "Disposable " + tid[:8],
                        "slug": "transfer-" + tid,
                    },
                )
                player = insert("season_players", {"season_id": sid, "trainer_id": tid})
                data = (args.fixtures / game / side).read_bytes()
                receipt = ingestion.receive(
                    sid,
                    tid,
                    sha256(data).hexdigest(),
                    None,
                    observation_digest(parser.parse(data), parser.version),
                    data,
                )
                scope[side] = {
                    "tid": tid,
                    "player": player,
                    "data": data,
                    "save": receipt.save_id,
                }
            head = store.one(
                "pokemon_identity_revisions", save_file_id=scope["source"]["save"]
            )
            entity = store.one(
                "pokemon_observations",
                revision_id=head["id"],
                source="box",
                box_number=1,
                slot_number=1,
            )["pokemon_entity_id"]
            item = store.one("shop_items", code="robar_pokemon")
            purchase = insert(
                "purchases",
                {
                    "season_id": sid,
                    "trainer_id": scope["destination"]["tid"],
                    "season_player_id": scope["destination"]["player"]["id"],
                    "shop_item_id": item["id"],
                    "unit_price": item["base_price"],
                },
            )
            scope.update(
                purchase=purchase["id"],
                entity=entity,
                request={
                    "season_id": sid,
                    "trainer_id": scope["destination"]["tid"],
                    "purchase_id": purchase["id"],
                    "pokemon_entity_id": entity,
                    "operation_id": str(uuid4()),
                },
            )
            return scope

        def bridge(c, side, aid, plan, *, fault=None):
            root = pg.root / (aid + "-" + side)
            root.mkdir(exist_ok=True)
            target = root / "main"
            if not target.exists():
                target.write_bytes(c[side]["data"])
            engine = LocalWriteEngine(
                root / "profile",
                native,
                files=WindowsWriteFiles(process_names=list),
                engineering_capability=EngineeringCapability.for_fixture_root(root),
                fault_hook=fault,
            )
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine
            )
            b = EngineeringTransfer(
                controller, repo, season_id=c["season_id"], trainer_id=c[side]["tid"]
            )
            b.bind(aid, side, plan)
            return b, target

        def unconsumed(c):
            assert store.one("purchases", id=c["purchase"])["status"] == "pending"
            assert not store.rows("redemptions", purchase_id=c["purchase"])
            assert (
                store.one("pokemon_entities", id=c["entity"])["owner_trainer_id"]
                == c["source"]["tid"]
            )

        assert not PRODUCTION_MUTATIONS
        for game in args.games:
            c = setup(game)
            if game == "X":
                rejected(
                    lambda c=c: repo.reserve(
                        c["request"] | {"trainer_id": c["source"]["tid"]}
                    ),
                    PersistenceError,
                )
                # Persisted shields deny authorization before any physical capability.
                flag = insert(
                    "pokemon_entity_flags",
                    {
                        "season_id": c["season_id"],
                        "trainer_id": c["source"]["tid"],
                        "pokemon_entity_id": c["entity"],
                        "flag_type": "blindado",
                        "flag_value": True,
                    },
                )
                rejected(lambda c=c: repo.reserve(c["request"]), PersistenceError)
                pg.sql(f"delete from pokemon_entity_flags where id='{flag['id']}';")
                passed("wrong owner and persisted shield rejected")
            if args.additional and game == "X":
                with ThreadPoolExecutor(max_workers=2) as pool:
                    reservations = list(
                        pool.map(lambda _, c=c: repo.reserve(c["request"]), range(2))
                    )
                assert reservations[0] == reservations[1]
                passed("concurrent identical reservation one authority")
            aid = repo.reserve(c["request"])["authorization_id"]
            assert repo.reserve(c["request"])["authorization_id"] == aid
            rejected(
                lambda c=c: repo.reserve(c["request"] | {"operation_id": str(uuid4())}),
                PersistenceError,
            )
            if args.additional and game == "X":
                copy = store.one("purchases", id=c["purchase"])
                another = insert(
                    "purchases",
                    {
                        k: copy[k]
                        for k in (
                            "season_id",
                            "trainer_id",
                            "season_player_id",
                            "shop_item_id",
                            "unit_price",
                        )
                    },
                )
                rejected(
                    lambda another=another, c=c: repo.reserve(
                        c["request"]
                        | {"purchase_id": another["id"], "operation_id": str(uuid4())}
                    ),
                    PersistenceError,
                )
                rejected(
                    lambda aid=aid, c=c: repo.leg(
                        {
                            "operation": "get",
                            "authorization_id": aid,
                            "season_id": c["season_id"],
                            "trainer_id": str(uuid4()),
                        }
                    ),
                    PersistenceError,
                )
                flag = insert(
                    "pokemon_entity_flags",
                    {
                        "season_id": c["season_id"],
                        "trainer_id": c["source"]["tid"],
                        "pokemon_entity_id": c["entity"],
                        "flag_type": "robado",
                        "flag_value": True,
                    },
                )
                rejected(lambda aid=aid: verifier.prepare(aid), VerificationRejected)
                pg.sql(f"delete from pokemon_entity_flags where id='{flag['id']}';")
                passed("second theft, foreign participant, later protection rejected")
            plans = verifier.prepare(aid)
            assert {k: v.to_payload() for k, v in verifier.prepare(aid).items()} == {
                k: v.to_payload() for k, v in plans.items()
            }
            donor, dp = bridge(c, "source", aid, plans["source"])
            receiver, rp = bridge(c, "destination", aid, plans["destination"])
            rejected(
                lambda aid=aid, donor=donor: donor.prepare(
                    aid, closed_emulator_confirmed=False
                ),
                WriteSafetyError,
            )
            donor.prepare(aid, closed_emulator_confirmed=True)
            rejected(
                lambda aid=aid, donor=donor: donor.apply(
                    aid, closed_emulator_confirmed=True
                ),
                PersistenceError,
            )
            receiver.prepare(aid, closed_emulator_confirmed=True)
            rejected(
                lambda aid=aid, receiver=receiver: receiver.apply(
                    aid, closed_emulator_confirmed=True
                ),
                PersistenceError,
            )
            rejected(
                lambda donor=donor, plans=plans: donor.engine.confirm(
                    plans["source"].operation_id, closed_emulator_confirmed=True
                ),
                WriteSafetyError,
            )
            if args.additional and game == "X":
                pg.sql(
                    f"update trainers set globally_enabled=false where id='{c['destination']['tid']}';"
                )
                rejected(
                    lambda aid=aid, donor=donor: donor.apply(
                        aid, closed_emulator_confirmed=True
                    ),
                    PersistenceError,
                )
                assert dp.read_bytes() == c["source"]["data"]
                pg.sql(
                    f"update trainers set globally_enabled=true where id='{c['destination']['tid']}';"
                )
                passed("disabled peer prevents application without changing files")
            donor.apply(aid, closed_emulator_confirmed=True)
            unconsumed(c)
            rejected(
                lambda aid=aid, receiver=receiver: receiver.apply(
                    aid, closed_emulator_confirmed=True
                ),
                PersistenceError,
            )
            # Simulate two restarted Launchers, preserving the existing bindings/claims.
            donor, _ = bridge(c, "source", aid, plans["source"])
            receiver, _ = bridge(c, "destination", aid, plans["destination"])
            donor.apply(aid, closed_emulator_confirmed=True)
            if game == "X":
                blobs.failure = "after"
                rejected(
                    lambda aid=aid, donor=donor: donor.submit(aid, transport),
                    PersistenceError,
                )
                blobs.failure = None
            donor.submit(aid, transport)
            if args.additional and game == "X":
                artifact = rpc(
                    {"operation": "artifact", "authorization_id": aid, "side": "source"}
                )
                exact = blobs.objects[artifact["result_key"]]
                blobs.objects[artifact["result_key"]] = c["source"]["data"]
                rejected(
                    lambda aid=aid: verifier.verify(aid, "source"), VerificationRejected
                )
                blobs.objects[artifact["result_key"]] = exact
                assert (
                    rpc(
                        {
                            "operation": "artifact",
                            "authorization_id": aid,
                            "side": "source",
                        }
                    )["proof"]
                    is None
                )
                rejected(
                    lambda aid=aid, receiver=receiver: receiver.apply(
                        aid, closed_emulator_confirmed=True
                    ),
                    PersistenceError,
                )
                passed("manipulated artifact cannot issue proof or release recipient")
            assert verifier.verify(aid, "source")["status"] == "PENDING_DESTINATION"
            receiver.apply(aid, closed_emulator_confirmed=True)
            receiver.submit(aid, transport)
            assert (
                verifier.verify(aid, "destination")["status"]
                == "BOTH_VERIFIED_PENDING_IDENTITY"
            )
            assert (
                verifier.verify(aid, "destination")["status"]
                == "BOTH_VERIFIED_PENDING_IDENTITY"
            )
            donor.submit(aid, transport)
            receiver.submit(aid, transport)
            assert donor.state(aid)["completed"] is False
            assert (
                donor.controller.gate.recovery_required
                and receiver.controller.gate.recovery_required
            )
            for b, path, side in ((donor, dp, "source"), (receiver, rp, "destination")):
                record = b.engine._load(plans[side].operation_id)
                assert b.engine._backup_bytes(record) == c[side]["data"]
                assert (
                    path.read_bytes()
                    == (args.fixtures / game / (side + "-result")).read_bytes()
                )
                rejected(
                    lambda b=b, plans=plans, side=side: b.engine.restore(
                        plans[side].operation_id, closed_emulator_confirmed=True
                    ),
                    WriteSafetyError,
                )
            unconsumed(c)
            if closure:
                closure(locals())
            report["games"].append(
                {
                    "game": game,
                    "status": "COMMITTED"
                    if closure
                    else "BOTH_VERIFIED_PENDING_IDENTITY",
                    "originals_preserved": True,
                    "entitlement_consumed": bool(closure),
                }
            )
            print(
                "PASS",
                game,
                "paired apply, independent proof, restart and replay",
                flush=True,
            )
        passed(
            f"{len(args.games)} native/PG/Launcher paired workflows, both backups, no false completion"
        )
        # Direct public/API proof and private-table access must fail.
        for role in ("anon", "authenticated", "service_role"):
            assert pg.sql(
                f'set role {role}; select public.transfer_verifier(\'{{"operation":"context","authorization_id":"{aid}"}}\');',
                ok=False,
            ).returncode
            assert pg.sql(
                f"set role {role}; select * from item_use_transfer_legs;", ok=False
            ).returncode
        passed("restricted issuer and paired-table grants")
        # Existing native registration refuses foreign OT; prove why no competitive finish exists.
        parsed = parser.parse(rp.read_bytes())
        target = parsed.boxes[0].slots[0]
        from app.domain.pokemon_identity import trusted_native_identity

        assert (
            trusted_native_identity(
                target.identity, trainer=parsed.trainer, is_egg=target.is_egg
            ).unresolved_reason
            == "original_trainer_unproven"
        )
        passed("foreign OT remains unproven, ownership/consumption deliberately gated")
        # Reservations block ordinary future accepted-save revisions and pointer advance.
        assert (
            closure
            or pg.sql(
                f"update season_players set current_save_file_id=null where season_id='{c['season_id']}' and trainer_id='{c['source']['tid']}';",
                ok=False,
            ).returncode
        )
        passed("reserved current-save pointer cannot advance")
        if args.additional and not closure:
            a = store.one("item_use_authorizations", id=aid)
            old = SupabaseItemUseRepository(client)
            claim = {"operation_id": a["operation_id"], "claim_id": str(uuid4())}
            old.claim(aid, c["season_id"], c["destination"]["tid"], claim)
            rejected_completion = old.complete(
                aid,
                c["season_id"],
                c["destination"]["tid"],
                claim | {"status": "APPLIED_VERIFIED", "observed_sha256": "a" * 64},
            )
            assert rejected_completion["status"] == "BLOCKED_UNCERTAIN"
            unconsumed(c)
            assert not pg.sql(
                "select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prosecdef and p.prorettype<>'trigger'::regtype and has_function_privilege('phase24_worker',p.oid,'EXECUTE') and proname not in('item_verifier_job','transfer_verifier');"
            ).stdout.strip()
            passed("worker exact function allowlist and no one-leg completion")
        if not args.skip_parity:
            report["parity"] = parity(pg)
            passed("current upgrade/bootstrap parity and prior table preservation")
        if args.additional:
            shadow = pg.sql(
                "select count(*) from information_schema.tables where table_schema='v1_shadow';"
            ).stdout
            pg.sql(Path("supabase/v2/reset_dev.sql").read_text(encoding="utf-8"))
            assert (
                pg.sql(
                    "select to_regclass('public.item_use_transfer_legs') is null;"
                ).stdout.strip()
                == "t"
            )
            assert (
                pg.sql(
                    "select count(*) from information_schema.tables where table_schema='v1_shadow';"
                ).stdout
                == shadow
            )
            passed("disposable reset removes new adjunct and preserves Shadow schema")
        report["status"] = "PASS"
    finally:
        if worker:
            worker.close()
        pg.stop()
        report["cleanup"] = "owned databases dropped; cluster stopped"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pg-bin", type=Path, required=True)
    p.add_argument("--native-exe", type=Path, required=True)
    p.add_argument("--fixtures", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--skip-parity", action="store_true")
    p.add_argument(
        "--games",
        nargs="+",
        choices=("X", "Y", "OR", "AS", "SN", "MN", "US", "UM"),
        default=["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"],
    )
    p.add_argument("--additional", action="store_true")
    run(p.parse_args())
