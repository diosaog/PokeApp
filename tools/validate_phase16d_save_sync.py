"""Disposable PostgreSQL + native parser + real HTTP trusted registration proof.

Only external Auth and raw object transport are local substitutes. Original
synthetic bytes, application services, SQL, JWT/PIN bridge and web reads are real.
Never accepts a remote DB or live credentials. Reuses local transport helpers,
not the Phase13 fixture or its historical test suite.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import uvicorn

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.supabase_repository import SupabaseTrainerAuthRepository
from app.application.save_ingestion import TrustedSaveIngestion
from app.auth.service import PinAuthBridge
from app.launcher.backend import BackendClient, LauncherSession
from app.launcher.journal import LocalJournal, LocalReceipt
from app.launcher.trusted_sync import TrustedStore, deliver_trusted
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from app.repositories.supabase.launcher import SupabaseLauncherRepository
from app.repositories.supabase.save_ingestion import SupabaseSaveIngestionRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.cloud import CloudObservation
from app.save_parser.models import SaveFingerprint
from app.save_parser.registration import observation_digest
from tools.phase13_staging import PEPPER, PIN, LocalQuery, SyntheticAuth, uid
from tools.validate_supabase_v2_identity_sql import LocalClient, SqlError, literal
from tools.validate_supabase_v2_schema import (
    BOOTSTRAP_SQL,
    MIGRATIONS,
    SUPABASE_ROLE_MOCK_SQL,
)


class Client(LocalClient):
    def table(self, name):
        return LocalQuery(self, name)


class RawRepository(SupabaseSaveIngestionRepository):
    def __init__(self, client, folder):
        super().__init__(client)
        self.folder, self.last = folder, None

    def store_raw(self, key, data, raw_hash):
        assert sha256(data).hexdigest() == raw_hash
        path = self.folder / key
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(data)
        except FileExistsError:
            assert path.read_bytes() == data

    def execute(self, operation, request):
        if operation == "register":
            self.last = request
        return super().execute(operation, request)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pg-bin", type=Path, required=True)
    p.add_argument("--port", type=int, default=55464)
    p.add_argument("--parser", type=Path, required=True)
    p.add_argument("--fixtures", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--browser", action="store_true")
    p.add_argument("--parity", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    database = "pokeapp_v2_validation_phase16d_" + uuid4().hex[:12]
    created, server, thread = [], None, None

    def run(program, db, tail, query=None):
        cmd = [
            str(args.pg_bin / (program + ".exe")),
            "-h",
            "127.0.0.1",
            "-p",
            str(args.port),
            "-U",
            "postgres",
        ]
        if program in ("psql", "pg_dump"):
            cmd += ["-d", db]
        result = subprocess.run(
            cmd + tail,
            check=False,
            input=query,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, PGCLIENTENCODING="UTF8"),
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()

    def sql(query, db=database):
        return run(
            "psql", db, ["-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-f", "-"], query
        )

    def scalar(query):
        return json.loads(sql(query))

    def snapshot():
        tables = scalar(
            "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
        )
        parts = [
            f"select '{t}' name, md5(coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]')::text) hash from public.{t} t"
            for t in tables
        ]
        return scalar(
            "select jsonb_object_agg(name,hash) from ("
            + " union all ".join(parts)
            + ") q"
        )

    try:
        for db, sources in [(database, MIGRATIONS)] + (
            [(database + "_bootstrap", [BOOTSTRAP_SQL])] if args.parity else []
        ):
            run("createdb", "postgres", [db])
            created.append(db)
            sql(SUPABASE_ROLE_MOCK_SQL, db)
            sql(
                """create schema storage;
              create table storage.buckets(id text primary key,name text,public boolean);
              create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);
              alter table storage.objects enable row level security;
              grant usage on schema storage to authenticated,service_role;
              grant all on storage.objects to authenticated,service_role;
            """,
                db,
            )
            for source in sources:
                sql(source.read_text(encoding="utf-8"), db)
        if args.parity:
            dumps = [
                "\n".join(
                    x
                    for x in run(
                        "pg_dump",
                        db,
                        [
                            "--schema-only",
                            "--schema=public",
                            "--schema=v1_shadow",
                            "--schema=storage",
                        ],
                    ).splitlines()
                    if not x.startswith(("\\restrict ", "\\unrestrict "))
                )
                for db in created
            ]
            assert dumps[0] == dumps[1]
            (args.output / "schema.sql").write_text(dumps[0], encoding="utf-8")
        before = snapshot()
        local = SimpleNamespace(
            psql=str(args.pg_bin / "psql.exe"),
            host="127.0.0.1",
            port=args.port,
            user="postgres",
            password="",
            database=database,
        )
        client = Client(local)
        sid, tid, rival = str(uuid4()), uid("Alia"), uid("Bruno")
        sql(f"""insert into public.trainers(id,display_name,slug,auth_user_id) values
          ('{tid}','16D Alia','phase16d-alia','{uid("Alia/auth")}'),('{rival}','16D Bruno','phase16d-bruno','{uid("Bruno/auth")}');
          insert into public.seasons(id,name,status,started_at) values ('{sid}','16D disposable','active',now());
          insert into public.season_players(season_id,trainer_id) values ('{sid}','{tid}'),('{sid}','{rival}');
          insert into public.season_player_stats(season_player_id,season_id,trainer_id)
            select id,season_id,trainer_id from public.season_players where season_id='{sid}';
          insert into public.season_config_versions(season_id,version_number,name,effective_from_matchday,total_matchdays,division_count,rules_json)
            values ('{sid}',1,'16D',1,4,2,'{{"badge_reward_coins":4,"game_completion_reward_coins":12}}');""")
        fixture = snapshot()
        parser = PkhexProcessParser(args.parser)
        repo = RawRepository(client, args.output / "storage")
        service = TrustedSaveIngestion(repo, parser)
        auth, trainers = SyntheticAuth(), SupabaseTrainerAuthRepository(client)
        container = ApiContainer(
            auth_bridge=PinAuthBridge(trainers=trainers, auth=auth, pepper=PEPPER),
            session_refresher=auth,
            token_verifier=auth,
            principal_repository=trainers,
            frontend_read_repository=SupabaseFrontendReadRepository(client),
            launcher_repository=SupabaseLauncherRepository(client),
            save_ingestion=service,
        )
        app = create_app(
            container=container,
            config=APIConfig(cors_origins=("http://127.0.0.1:5173",)),
        )
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8164, log_level="error")
        )
        thread = threading.Thread(target=server.run)
        thread.start()
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started
        # Synthetic Auth provider + real PIN bridge/JWT and repository authorization.
        backend = BackendClient("http://127.0.0.1:8164")
        session = LauncherSession(backend)
        assert session.login("phase16d-alia", PIN).trainer_id == tid
        raw = (args.fixtures / "gen5.sav").read_bytes()
        raw_hash = sha256(raw).hexdigest()
        observed = parser.parse(raw)
        digest = observation_digest(observed, parser.version)
        # The former private intake is still deliberately unable to change any business table.
        inbox = CloudObservation(
            fingerprint=SaveFingerprint(sha256=raw_hash, size=len(raw)),
            parser_version=parser.version,
            observation=observed,
        )
        session.request(
            "PUT",
            f"/v1/launcher/seasons/{sid}/observations/{inbox.identifier(tid, sid)}",
            body=inbox.model_dump(mode="json"),
        )
        private = snapshot()
        assert {k: v for k, v in private.items() if k != "launcher_observations"} == {
            k: v for k, v in fixture.items() if k != "launcher_observations"
        }
        store = TrustedStore(LocalJournal(args.output / "journal.sqlite3"))
        local_receipt = LocalReceipt(
            "fixture", 1, inbox.fingerprint, parser.version, observed
        )
        store.enqueue_raw(backend.origin, tid, sid, local_receipt, raw)
        first = deliver_trusted(
            session, store, store.pending(backend.origin, tid), selected_hash=raw_hash
        )
        pc = session.request("GET", f"/v1/read/seasons/{sid}/pc")
        assert (
            pc["status"] == "ready"
            and pc["save"]["id"] == first.save_id
            and len(pc["pokemon"]) == 2
        )
        assert all("identity_evidence" not in p["pokemon"] for p in pc["pokemon"])
        accepted = snapshot()
        assert service.receive(sid, tid, raw_hash, None, digest, raw) == first
        assert snapshot() == accepted
        # Simultaneous first acceptance of a native changed save pays four new
        # observed badges once. Replaying the older bytes cannot rewind the head.
        progress = (args.fixtures / "gen5-progress.sav").read_bytes()
        progress_hash = sha256(progress).hexdigest()
        progress_digest = observation_digest(parser.parse(progress), parser.version)
        with ThreadPoolExecutor(max_workers=2) as pool:
            pair = list(
                pool.map(
                    lambda _: service.receive(
                        sid,
                        tid,
                        progress_hash,
                        first.save_id,
                        progress_digest,
                        progress,
                    ),
                    range(2),
                )
            )
        assert pair[0] == pair[1]
        assert (
            scalar(
                f"select count(*) from public.progress_reward_claims where trainer_id='{tid}'"
            )
            == 4
        )
        assert (
            scalar(
                f"select sum(amount)::int from public.coin_transactions where trainer_id='{tid}'"
            )
            == 16
        )
        assert not service.receive(sid, tid, raw_hash, None, digest, raw).is_current
        assert (
            scalar(
                f"select to_jsonb(current_save_file_id::text) from public.season_players where season_id='{sid}' and trainer_id='{tid}'"
            )
            == pair[0].save_id
        )
        accepted = snapshot()
        # Independent connections, exact same idempotent receipt.
        with ThreadPoolExecutor(max_workers=2) as pool:
            pair = list(
                pool.map(
                    lambda _: service.receive(sid, tid, raw_hash, None, digest, raw),
                    range(2),
                )
            )
        assert (
            pair == [first.model_copy(update={"is_current": False})] * 2
            and snapshot() == accepted
        )
        # Rival cannot claim the same native trainer identity or read its PC through own endpoint.
        other = LauncherSession(backend)
        other.login("phase16d-bruno", PIN)
        assert (
            other.request("GET", f"/v1/read/seasons/{sid}/pc")["status"]
            == "no_current_save"
        )
        try:
            service.receive(sid, rival, raw_hash, None, digest, raw)
        except SeasonAdminRejected as e:
            assert e.status == 409
        else:
            raise AssertionError("Cross-owner save accepted")
        assert snapshot() == accepted
        for damaged in (raw[:100], bytes(len(raw))):
            try:
                service.receive(
                    sid,
                    tid,
                    sha256(damaged).hexdigest(),
                    pair[0].save_id,
                    digest,
                    damaged,
                )
            except SeasonAdminRejected as e:
                assert e.status in (409, 422)
            else:
                raise AssertionError("Corrupt save accepted")
        assert snapshot() == accepted
        # X/Y bytes enter the same PC model; no invented 023 identity/progress rewards.
        xy = (args.fixtures / "xy/X/main").read_bytes()
        xy_hash = sha256(xy).hexdigest()
        xy_obs = parser.parse(xy)
        xy_result = service.receive(
            sid, rival, xy_hash, None, observation_digest(xy_obs, parser.version), xy
        )
        assert xy_result.is_current
        xy_pc = other.request("GET", f"/v1/read/seasons/{sid}/pc")
        assert xy_pc["status"] == "ready" and all(
            p["pokemon_entity_id"] is None for p in xy_pc["pokemon"]
        )
        assert (
            scalar(
                f"select count(*) from public.pokemon_identity_revisions where trainer_id='{rival}'"
            )
            == 0
        )
        assert (
            scalar(
                f"select count(*) from public.progress_reward_claims where trainer_id='{rival}'"
            )
            == 0
        )
        # Transaction rollback after an actual registration: every public table matches.
        request = repo.last.copy()
        rollback_before = snapshot()
        request.update(
            save_id=str(uuid4()),
            parsed_id=str(uuid4()),
            sha256="e" * 64,
            expected_save_id=xy_result.save_id,
        )
        request["storage_key"] = f"trusted/{rival}/{sid}/" + "e" * 64 + ".sav"
        request["payload"] = request["payload"] | {
            "save_record_id": request["save_id"],
            "source_hash": "e" * 64,
        }
        text = json.dumps(request | {"operation": "register"})
        try:
            sql(
                "do $x$ begin perform public.api_register_save("
                + literal(text)
                + "::jsonb); perform 1/0; end $x$;"
            )
        except RuntimeError as e:
            assert "division by zero" in str(e)
        else:
            raise AssertionError("Expected rollback")
        assert snapshot() == rollback_before
        request["expected_save_id"] = None
        try:
            repo.execute("register", request)
        except SeasonAdminRejected as e:
            assert e.status == 409
        else:
            raise AssertionError("Stale CAS accepted")
        assert snapshot() == rollback_before
        # Service RPC and all save writes unavailable directly to browser roles.
        for role in ("anon", "authenticated"):
            for query in (
                "select public.api_register_save('{}')",
                "update public.season_players set current_save_file_id=null",
                "insert into public.save_files default values",
                "insert into public.parsed_saves default values",
            ):
                try:
                    Client(local, role).execute(query)
                except SqlError as e:
                    assert getattr(e, "code", None) == "42501", str(e)
                else:
                    raise AssertionError("Browser write permitted")
        assert sha256((args.fixtures / "gen5.sav").read_bytes()).hexdigest() == raw_hash
        sql(f"update public.trainers set is_admin=true where id='{tid}';")
        browser_admin = Client(local, "authenticated", uid("Alia/auth"))
        for action in ("insert", "update", "delete"):
            assert (
                scalar(
                    f"select count(*) from pg_policies where schemaname='storage' and policyname='trusted_raw_no_browser_{action}' and permissive='RESTRICTIVE'"
                )
                == 1
            )
        try:
            browser_admin.execute(
                "insert into storage.objects(bucket_id,name) values('raw-saves','trusted/forged.sav') returning to_jsonb(objects)"
            )
        except SqlError as error:
            assert error.code == "42501"
        else:
            raise AssertionError("Browser admin can forge trusted storage")
        sql(
            "insert into storage.objects(bucket_id,name) values('raw-saves','trusted/test.sav');"
        )
        assert (
            browser_admin.execute(
                "with r as (delete from storage.objects where name='trusted/test.sav' returning *) select count(*) from r"
            ).data
            == 0
        )
        assert (
            browser_admin.execute(
                "with r as (update storage.objects set name='changed' where name='trusted/test.sav' returning *) select count(*) from r"
            ).data
            == 0
        )
        sql(
            f"delete from storage.objects; update public.trainers set is_admin=false where id='{tid}';"
        )
        if args.browser:
            proof = {
                "season": sid,
                "trainer": tid,
                "rival": rival,
                "api": "http://127.0.0.1:8164",
                "pin": PIN,
                "parser": str(args.parser),
                "fixture": str(args.fixtures / "gen5-later.sav"),
            }
            (args.output / "browser-input.json").write_text(json.dumps(proof))
            result = subprocess.run(
                ["node", "tools/validate_phase16d_web.mjs", str(args.output)],
                cwd=ROOT,
                check=False,
            )
            assert result.returncode == 0
            assert scalar("select count(*) from public.save_files") == 4
            assert (
                scalar(
                    f"select count(*) from public.progress_reward_claims where trainer_id='{tid}'"
                )
                == 4
            )
        backend.close()
        # Cleanup only this disposable database's complete fixture; no hosted target can enter.
        sql(
            f"delete from public.launcher_observations where season_id='{sid}'; delete from public.progress_reward_claims where season_id='{sid}'; delete from public.coin_transactions where season_id='{sid}'; "
            f"update public.season_players set current_save_file_id=null where season_id='{sid}'; delete from public.pokemon_observations where season_id='{sid}'; "
            f"delete from public.pokemon_identity_revisions where season_id='{sid}'; delete from public.pokemon_entities where season_id='{sid}'; delete from public.parsed_saves where save_file_id in(select id from public.save_files where season_id='{sid}'); "
            f"delete from public.save_files where season_id='{sid}'; delete from public.season_player_stats where season_id='{sid}'; delete from public.season_players where season_id='{sid}'; "
            f"delete from public.season_config_versions where season_id='{sid}'; delete from public.seasons where id='{sid}'; delete from public.trainers where id in ('{tid}','{rival}');"
        )
        restored = snapshot()
        assert restored == before, [k for k in before if before[k] != restored[k]]
        report = {
            "status": "PASS",
            "public_tables_restored": len(before),
            "migrations": len(MIGRATIONS),
            "bootstrap_parity": args.parity,
            "native_gen5_xy": True,
            "real_http_pin_jwt": True,
            "private_inbox_no_effects": True,
            "raw_registered_pc_readback": True,
            "same_hash_replay_concurrency": True,
            "cross_owner_denied": True,
            "xy_identity_progress_unknown": True,
            "transaction_rollback": True,
            "browser_writes_denied": True,
            "source_bytes_unchanged": True,
            "browser": args.browser,
            "concurrent_new_save_rewards_once": True,
            "stale_cas_denied": True,
            "old_replay_no_rewind": True,
        }
        (args.output / "postgres.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=15)
        for db in reversed(created):
            run("dropdb", "postgres", [db])


if __name__ == "__main__":
    main()
