"""New23D gates only: real loopback PG/native + isolated immutable Storage.

Uses retained23C native fixture output; never opens owner saves or remote services.
Auth is synthetic; SQL, API, worker roles, parser/writer and local journal are real.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import psycopg
from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.item_use_transport import ItemUseTransport
from app.application.item_use_verification import TrustedItemUseVerification
from app.application.item_use_worker import SignedArtifactReader, verify_one
from app.application.save_ingestion import TrustedSaveIngestion
from app.domain.item_use import ItemUsePrepareRequest
from app.domain.item_use_status import physical_state
from app.launcher.item_use import EngineeringItemUse
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles
from app.repositories.errors import ItemUseRejectedError, PersistenceError
from app.repositories.item_verifier_pg import ItemVerifierPG
from app.repositories.supabase.item_use import SupabaseItemUseRepository
from app.repositories.supabase.item_use_transport import SupabaseItemUseTransport
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter
from tools.validate_accounts_local import LocalPG
from tools.validate_phase23_local import parity
from tools.validate_phase23c_local import LocalSourceStore, LocalVerifierStore
from tools.validate_supabase_v2_identity_sql import LocalClient


class Blobs:
    """Local object transport, never a hosted Storage claim."""

    origin = "https://storage.fixture.invalid"

    def __init__(self, objects):
        self.objects = objects
        self.failure = None

    def put(self, key, data, digest):
        assert sha256(data).hexdigest() == digest
        if self.failure == "before":
            raise PersistenceError("injected")
        assert self.objects.setdefault(key, data) == data
        if self.failure == "after":
            raise PersistenceError("injected")

    def sign(self, key):
        return (
            self.origin
            + "/storage/v1/object/sign/raw-saves/"
            + key
            + "?token=fictional"
        )

    def serve(self, request):
        key = request.url.path.split("/raw-saves/", 1)[1]
        return httpx.Response(200, content=self.objects[key])


def rejected(call, exception=ItemUseRejectedError):
    try:
        call()
    except exception:
        return
    raise AssertionError("expected rejection")


def run(args):
    pg = LocalPG(args.pg_bin, 55475)
    report = {"status": "RUNNING", "checks": [], "cluster": str(pg.root)}
    worker = None

    def passed(name):
        report["checks"].append(name)
        print("PASS " + name, flush=True)

    try:
        pg.start()
        config = SimpleNamespace(
            psql=str(args.pg_bin / "psql.exe"),
            host="127.0.0.1",
            port=pg.port,
            user="postgres",
            password="",
            database="pokeapp_v2_validation_accounts",
        )
        client = LocalClient(config)
        sources = LocalSourceStore(client)
        store = LocalVerifierStore(pg, client, sources)
        parser, native = (
            PkhexProcessParser(args.native_exe),
            PkhexProcessWriter(args.native_exe),
        )
        ingestion = TrustedSaveIngestion(sources, parser)
        repo = SupabaseItemUseRepository(client)
        verifier = TrustedItemUseVerification(
            store, parser, native
        )  # plan only; never its test proof recorder
        objects = Blobs(sources.blobs)
        reader = SignedArtifactReader(
            objects.origin,
            client=httpx.Client(transport=httpx.MockTransport(objects.serve)),
        )
        intake = SupabaseItemUseTransport(client)
        allowed = set()

        def transport():
            return ItemUseTransport(intake, objects, allowed_trainers=allowed)

        pg.sql(
            "create role phase23d_worker login inherit; grant pokeapp_item_verifier to phase23d_worker;"
        )
        worker = psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            user="phase23d_worker",
            dbname=config.database,
            autocommit=True,
        )
        rpc = ItemVerifierPG(worker)

        def work(call=rpc):
            return verify_one(call, reader, parser, native)

        def insert(table, row):
            return client.table(table).insert(row).execute().data[0]

        source = (args.fixtures / "X/source").read_bytes()
        expected = (args.fixtures / "X/expected").read_bytes()

        def setup():
            tid = str(uuid4())
            allowed.add(tid)
            insert(
                "trainers",
                {
                    "id": tid,
                    "display_name": "Transport " + tid[:8],
                    "slug": "transport-" + tid,
                },
            )
            pg.sql(
                "update seasons set status='draft',started_at=null where status='active';"
            )
            sid = insert(
                "seasons",
                {
                    "name": "23D " + tid,
                    "status": "active",
                    "started_at": "2026-10-01T00:00:00Z",
                },
            )["id"]
            player = insert("season_players", {"season_id": sid, "trainer_id": tid})
            receipt = ingestion.receive(
                sid,
                tid,
                sha256(source).hexdigest(),
                None,
                observation_digest(parser.parse(source), parser.version),
                source,
            )
            saved = store.one("save_files", id=receipt.save_id)
            head = store.one("pokemon_identity_revisions", save_file_id=saved["id"])
            target = store.one(
                "pokemon_observations",
                revision_id=head["id"],
                source="box",
                box_number=8,
                slot_number=1,
            )
            purchase = insert(
                "purchases",
                {
                    "season_id": sid,
                    "trainer_id": tid,
                    "season_player_id": player["id"],
                    "shop_item_id": store.one("shop_items", code="revivir_pokemon")[
                        "id"
                    ],
                    "unit_price": 12,
                },
            )
            a = repo.prepare(
                ItemUsePrepareRequest(
                    sid,
                    tid,
                    purchase["id"],
                    target["pokemon_entity_id"],
                    saved["id"],
                    saved["sha256"],
                    str(uuid4()),
                    str(uuid4()),
                )
            )
            return a

        def claim(a):
            key = str(uuid4())
            repo.claim(
                a["id"],
                a["season_id"],
                a["trainer_id"],
                {"claim_id": key, "operation_id": a["operation_id"]},
            )
            return (a["id"], a["season_id"], a["trainer_id"], key)

        def pending(a):
            assert store.one("purchases", id=a["purchase_id"])["status"] == "pending"
            assert not store.rows("redemptions", purchase_id=a["purchase_id"])
            assert not store.rows("coin_transactions", season_id=a["season_id"])

        def finish(a, scope):
            return repo.complete(
                *scope[:3],
                {
                    "claim_id": scope[3],
                    "operation_id": a["operation_id"],
                    "status": "APPLIED_VERIFIED",
                    "observed_sha256": sha256(expected).hexdigest(),
                },
            )

        if args.extra_only:
            for filename in ("extra-money", "extra-pkm"):
                a = setup()
                scope = claim(a)
                data = (args.forgeries / filename).read_bytes()
                assert parser.parse(data).game == "X"
                transport().submit(*scope, data)
                assert work() == "REJECTED"
                pending(a)
            passed(
                "native_valid_extra_money_and_IV_correct_hash_rejected_through_transport"
            )
            a = setup()
            scope = claim(a)
            transport().submit(*scope, expected)

            def stale_finish(request):
                if request["operation"] == "finish":
                    pg.sql(
                        f"update season_players set current_save_file_id=null where season_id='{a['season_id']}';"
                    )
                return rpc(request)

            assert work(stale_finish) == "RETRY_LATER"
            assert not store.rows("item_use_verifications", authorization_id=a["id"])
            pending(a)
            passed("SQL_finish_CAS_rechecks_authority_after_native_verification")
            pg.sql(
                "insert into storage.buckets(id,name) values('raw-saves','raw-saves') on conflict do nothing; insert into storage.objects(bucket_id,name) values('raw-saves','item-use/private'),('raw-saves','control'); create policy fixture_read on storage.objects for select to authenticated using(true);"
            )
            rows = pg.sql(
                "set role authenticated; select name from storage.objects order by name; reset role;"
            ).stdout.splitlines()
            assert rows == ["control"], rows
            pg.sql("drop policy fixture_read on storage.objects;")
            passed("restrictive_Storage_policy_overrides_other_permissive_browser_read")
            report["status"] = "PASS"
            return

        # Real API + PG + private worker, no browser/admin proof issuing.
        a = setup()
        scope = claim(a)
        service = transport()
        app = create_app(
            container=ApiContainer(item_use_transport=service, item_use_repository=repo)
        )
        app.dependency_overrides[require_enabled_principal] = lambda: SimpleNamespace(
            trainer_id=a["trainer_id"]
        )
        url = f"/v1/launcher/seasons/{scope[1]}/item-uses/{scope[0]}/result?claim_id={scope[3]}"
        with TestClient(app) as api:
            assert (
                api.put(
                    url,
                    content=expected,
                    headers={"Content-Type": "application/octet-stream"},
                ).json()["status"]
                == "QUEUED"
            )
            assert work() == "VERIFIED"
            result = api.get(url).json()
            assert (
                set(result) == {"authorization_id", "status", "result_sha256"}
                and result["status"] == "VERIFIED"
            )
            pending(a)
            assert (
                api.put(
                    url,
                    content=expected,
                    headers={"Content-Type": "application/octet-stream"},
                ).json()
                == result
            )
            response = api.put(
                f"/v1/launcher/seasons/{scope[1]}/item-uses/{scope[0]}",
                json={
                    "claim_id": scope[3],
                    "operation_id": a["operation_id"],
                    "status": "APPLIED_VERIFIED",
                    "observed_sha256": sha256(expected).hexdigest(),
                },
            )
            assert response.status_code == 200, response.text
            assert response.json()["physical_state"] == "APPLIED_VERIFIED"
        final = finish(a, scope)
        assert final["status"] == "APPLIED_VERIFIED"
        historical = store.one("item_use_authorizations", id=a["id"])["receipt"]
        assert "pending" in json.dumps(historical)
        assert finish(a, scope) == final
        assert store.one("item_use_authorizations", id=a["id"])["receipt"] == historical
        assert len(store.rows("redemptions", purchase_id=a["purchase_id"])) == 1
        assert not store.rows("coin_transactions", season_id=a["season_id"])
        assert (
            physical_state("revive", repo.list(a["season_id"], a["trainer_id"])[0])
            == "APPLIED_VERIFIED"
        )
        passed(
            "real_HTTP_PG_worker_native_exactly_once_and_immutable_historical_receipt"
        )

        a = setup()
        scope = claim(a)
        service = transport()
        for failure in ("before", "after"):
            objects.failure = failure
            rejected(lambda: service.submit(*scope, expected), PersistenceError)
            assert service.status(*scope)["status"] == "UPLOADING"
            assert work() == "IDLE"
            pending(a)
        objects.failure = None
        service.submit(*scope, expected)

        def lost_ack(request):
            value = rpc(request)
            if request["operation"] == "finish":
                raise PersistenceError("injected response loss")
            return value

        assert work(lost_ack) == "RETRY_LATER"
        assert transport().status(*scope)["status"] == "VERIFIED"
        assert work() == "IDLE"
        pending(a)
        passed(
            "upload_interruptions_and_lost_verification_ack_reconcile_without_consumption"
        )

        a = setup()
        scope = claim(a)
        service = transport()
        service.submit(*scope, expected)
        pg.sql(
            "create function public.inject_proof_failure() returns trigger language plpgsql as $$ begin raise exception 'injected'; end $$; create trigger inject before insert on item_use_verifications for each row execute function public.inject_proof_failure();"
        )
        assert work() == "RETRY_LATER"
        assert not store.rows("item_use_verifications", authorization_id=a["id"])
        pending(a)
        pg.sql(
            "drop trigger inject on item_use_verifications; drop function inject_proof_failure();"
        )
        pg.sql(
            f"update item_use_artifacts set lease_until=now()-interval '1 second' where authorization_id='{a['id']}';"
        )
        assert service.status(*scope)["status"] == "RETRY_REQUIRED"
        service.submit(*scope, expected)
        assert work() == "VERIFIED"
        pending(a)
        passed("proof_insert_failure_rolls_back_and_expired_lease_requeues_same_bytes")

        # Correct supplied hashes are insufficient; byte transformation is checked.
        for change in ("corrupt", "wrong_transform", "extra_pkm", "wrong_save"):
            a = setup()
            scope = claim(a)
            if change == "corrupt":
                data = expected[:-1] + bytes([expected[-1] ^ 1])
            elif change == "wrong_save":
                data = (args.fixtures / "Y/expected").read_bytes()
            else:
                intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])
                if change == "wrong_transform":
                    changed = replace(
                        intent,
                        mutation={
                            "kind": "test_marking",
                            "location": "box",
                            "box_index": 7,
                            "slot_index": 0,
                            "expected_original": 0,
                            "new_value": 1,
                        },
                    )
                    data = native.prepare(source, changed).output
                else:
                    # Start with correct revive; mutate a PKM byte (checksum may fail).
                    data = bytearray(expected)
                    data[0x22600] ^= 1
                    data = bytes(data)
            transport().submit(*scope, data)
            assert work() == "REJECTED", change
            pending(a)
        passed("tamper_correct_hash_wrong_transform_other_save_and_extra_pkm_denied")

        a = setup()
        scope = claim(a)
        service = transport()
        rejected(
            lambda: service.submit(
                a["id"], a["season_id"], str(uuid4()), scope[3], expected
            )
        )
        rejected(
            lambda: service.submit(
                a["id"], str(uuid4()), a["trainer_id"], scope[3], expected
            )
        )
        rejected(lambda: service.submit(*scope[:3], str(uuid4()), expected))
        rejected(
            lambda: repo.claim(
                *scope[:3],
                {"claim_id": str(uuid4()), "operation_id": a["operation_id"]},
            )
        )
        service.submit(*scope, expected)
        rejected(lambda: service.submit(*scope, source))
        pg.sql(
            f"update item_use_authorizations set expires_at=now()-interval '1 second' where id='{a['id']}';"
        )
        assert service.status(*scope)["status"] == "EXPIRED" and work() == "IDLE"
        pending(a)
        passed("trainer_season_claim_hash_binding_and_expiry_fail_closed")

        a = setup()
        scope = claim(a)
        service = transport()
        service.submit(*scope, expected)
        jobs = []

        def lease(_):
            with psycopg.connect(
                host="127.0.0.1",
                port=pg.port,
                user="phase23d_worker",
                dbname=config.database,
                autocommit=True,
            ) as c:
                return ItemVerifierPG(c)(
                    {"operation": "lease", "lease_id": str(uuid4())}
                )

        with ThreadPoolExecutor(2) as pool:
            jobs = list(pool.map(lease, range(2)))
        assert sum(j is not None for j in jobs) == 1
        old = next(j for j in jobs if j)
        pg.sql(
            f"update item_use_artifacts set lease_until=now()-interval '1 second' where authorization_id='{a['id']}';"
        )
        service.submit(*scope, expected)
        rejected(
            lambda: rpc(
                {
                    "operation": "context",
                    "authorization_id": a["id"],
                    "lease_id": old["lease_id"],
                }
            ),
            PersistenceError,
        )
        # Change trusted current pointer after intake; worker cannot approve stale bytes.
        pg.sql(
            f"update season_players set current_save_file_id=null where season_id='{a['season_id']}';"
        )
        assert work() == "REJECTED"
        pending(a)
        passed("concurrent_worker_lease_fencing_and_stale_source_denial")

        for role in ("anon", "authenticated", "service_role", "phase23d_worker"):
            for table in ("item_use_verifications", "item_use_artifacts"):
                assert (
                    pg.sql(
                        f"select has_table_privilege('{role}','{table}','INSERT') or has_table_privilege('{role}','{table}','UPDATE') or has_table_privilege('{role}','{table}','DELETE');"
                    ).stdout.strip()
                    == "f"
                )
            if role != "phase23d_worker":
                assert (
                    pg.sql(
                        f"select has_function_privilege('{role}','item_verifier_job(jsonb)','EXECUTE');"
                    ).stdout.strip()
                    == "f"
                )
        assert (
            pg.sql(
                "select has_table_privilege('phase23d_worker','trainers','SELECT') or has_function_privilege('phase23d_worker','api_complete_item_use(uuid,uuid,uuid,text,text,uuid,text,text)','EXECUTE');"
            ).stdout.strip()
            == "f"
        )
        passed("real_private_role_grants_no_browser_API_or_worker_direct_proof_DML")

        # Existing journal + new transport recovery after Launcher restart; no new apply.
        a = setup()
        root = pg.root / "launcher"
        root.mkdir()
        path = root / "main"
        path.write_bytes(source)
        intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])

        def bridge():
            engine = LocalWriteEngine(
                root / "profile",
                native,
                files=WindowsWriteFiles(process_names=list),
                engineering_capability=EngineeringCapability.for_fixture_root(root),
            )
            return EngineeringItemUse(
                LocalWriteController(SaveActivityGate(), lambda: str(path), engine),
                repo,
                season_id=a["season_id"],
                trainer_id=a["trainer_id"],
            )

        local = bridge()
        local.bind_revive(a, intent, pokemon_entity_id=a["target_pokemon_entity_id"])
        assert (
            local.apply(a["id"], closed_emulator_confirmed=True)
            == "LOCAL_VERIFIED_AWAITING_CONFIRMATION"
        )
        service = transport()

        class LostUpload:
            status = service.status

            def submit(self, *args):
                service.submit(*args)
                raise PersistenceError("injected")

        rejected(
            lambda: local.submit_verification(a["id"], LostUpload()), PersistenceError
        )
        before = path.stat().st_mtime_ns
        local = bridge()
        assert local.submit_verification(a["id"], service) == "QUEUED"
        assert work() == "VERIFIED"
        assert local.submit_verification(a["id"], service) == "VERIFIED"
        assert local.complete(a["id"]) == "APPLIED_VERIFIED"
        assert bridge().complete(a["id"]) == "APPLIED_VERIFIED"
        assert path.stat().st_mtime_ns == before and path.read_bytes() == expected
        assert (
            local.engine._backup_bytes(local.engine._load(intent.operation_id))
            == source
        )
        assert len(store.rows("redemptions", purchase_id=a["purchase_id"])) == 1
        passed(
            "real_Launcher_restart_lost_upload_no_reapplication_backup_and_one_consumption"
        )
        report["parity"] = parity(pg)
        passed("056_upgrade_bootstrap_catalog_parity_previous_rows_preserved")
        report["status"] = "PASS"
    finally:
        if worker is not None:
            worker.close()
        pg.stop()
        report["cleanup"] = "owned_database_dropped_cluster_stopped"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--pg-bin", type=Path, required=True)
    cli.add_argument("--native-exe", type=Path, required=True)
    cli.add_argument("--fixtures", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--extra-only", action="store_true")
    cli.add_argument("--forgeries", type=Path)
    run(cli.parse_args())
