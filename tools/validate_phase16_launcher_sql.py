"""Loopback-only 16A build parity, private intake and zero business effects proof."""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_phase16_launcher import body

from app.repositories.supabase.launcher import SupabaseLauncherRepository
from app.save_parser.cloud import ObservationReceipt
from tools.validate_supabase_v2_identity_sql import LocalClient, SqlError, literal
from tools.validate_supabase_v2_schema import (
    BOOTSTRAP_SQL,
    MIGRATIONS,
    SUPABASE_ROLE_MOCK_SQL,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55446)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    prefix = "pokeapp_v2_validation_phase16_"

    def run(program, database, tail, sql=None):
        command = [
            str(args.pg_bin / (program + ".exe")),
            "-h",
            "127.0.0.1",
            "-p",
            str(args.port),
            "-U",
            "postgres",
        ]
        if program in ("psql", "pg_dump"):
            command += ["-d", database]
        result = subprocess.run(
            command + tail,
            check=False,
            input=sql,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, PGCLIENTENCODING="UTF8"),
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()

    def sql(database, query):
        return run(
            "psql", database, ["-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-f", "-"], query
        )

    def snapshots(database):
        tables = json.loads(
            sql(
                database,
                "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public';",
            )
        )
        return {
            t: sql(
                database,
                f"select md5(coalesce(jsonb_agg(r order by r::text),'[]')::text) from (select to_jsonb(t) r from public.{t} t) q;",
            )
            for t in tables
        }

    created, dumps = [], []
    try:
        for kind in ("migrations", "bootstrap"):
            database = prefix + kind
            if (
                sql(
                    "postgres",
                    f"select count(*) from pg_database where datname='{database}';",
                )
                != "0"
            ):
                raise RuntimeError("Refusing existing local database")
            run("createdb", "postgres", [database])
            created.append(database)
            sql(database, SUPABASE_ROLE_MOCK_SQL)
            for path in MIGRATIONS if kind == "migrations" else [BOOTSTRAP_SQL]:
                sql(database, path.read_text(encoding="utf-8"))
            raw = run(
                "pg_dump",
                database,
                ["--schema-only", "--schema=public", "--schema=v1_shadow"],
            )
            normalized = "\n".join(
                line
                for line in raw.splitlines()
                if not line.startswith(("\\restrict ", "\\unrestrict "))
            )
            (args.evidence / (kind + "-schema.sql")).write_text(
                normalized, encoding="utf-8"
            )
            dumps.append(normalized)
        assert dumps[0] == dumps[1], (
            "Migration/bootstrap schema, grants and ownership differ"
        )
        database = created[0]
        before = snapshots(database)
        tid, other, sid, spid = (str(uuid4()) for _ in range(4))
        sql(
            database,
            f"""
          insert into public.trainers(id,display_name,slug) values
          ('{tid}','16A local','phase16_local'),('{other}','16A rival','phase16_rival');
          insert into public.seasons(id,name,status,created_by_trainer_id) values ('{sid}','16A local','draft','{tid}');
          insert into public.season_players(id,season_id,trainer_id) values ('{spid}','{sid}','{tid}');
          insert into public.season_player_stats(season_player_id,season_id,trainer_id) values ('{spid}','{sid}','{tid}');
        """,
        )
        fixture = snapshots(database)
        local_args = SimpleNamespace(
            psql=str(args.pg_bin / "psql.exe"),
            host="127.0.0.1",
            port=args.port,
            user="postgres",
            password="",
            database=database,
        )
        service = LocalClient(local_args)
        repo = SupabaseLauncherRepository(service)
        value = body()
        request = {
            "trainer_id": tid,
            "season_id": sid,
            "id": value.identifier(tid, sid),
            "payload_digest": value.digest(),
            "body": value.model_dump(mode="json"),
        }
        first = ObservationReceipt.model_validate(repo.execute("receive", request))
        assert first.competitive_authority is False
        assert repo.execute("receipt", request) == first.model_dump()
        assert repo.execute("receive", request) == first.model_dump()
        after = snapshots(database)
        assert {k: v for k, v in after.items() if k != "launcher_observations"} == {
            k: v for k, v in fixture.items() if k != "launcher_observations"
        }

        def denied(query, code, role="service_role"):
            try:
                LocalClient(local_args, role).execute(query)
            except SqlError as error:
                assert error.code == code, (error.code, code)
            else:
                raise AssertionError("Expected denial")

        def call(req):
            return (
                "select public.api_launcher_observation("
                + literal(json.dumps(req))
                + "::jsonb)"
            )

        denied(
            call(request | {"operation": "receive", "payload_digest": "b" * 64}),
            "PT409",
        )
        denied(call(request | {"operation": "receipt", "trainer_id": other}), "PT403")
        denied(
            call(request | {"operation": "receive", "id": str(uuid4()), "body": {}}),
            "PT422",
        )
        for role in ("anon", "authenticated"):
            denied("select body from public.launcher_observations", "42501", role)
            denied(call(request | {"operation": "receipt"}), "42501", role)
        denied("update public.launcher_observations set body='{}'", "42501")
        denied("delete from public.launcher_observations", "42501")
        # Two independent real connections, one immutable authoritative receipt.
        value2 = body("b")
        req2 = request | {
            "id": value2.identifier(tid, sid),
            "body": value2.model_dump(mode="json"),
            "payload_digest": value2.digest(),
        }
        barrier = Barrier(2)

        def concurrent(_):
            barrier.wait()
            return SupabaseLauncherRepository(LocalClient(local_args)).execute(
                "receive", req2
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            pair = list(pool.map(concurrent, range(2)))
        assert pair[0] == pair[1]
        assert (
            sql(database, "select count(*) from public.launcher_observations;") == "2"
        )
        value3 = body("c")
        req3 = request | {
            "operation": "receive",
            "id": value3.identifier(tid, sid),
            "body": value3.model_dump(mode="json"),
            "payload_digest": value3.digest(),
        }
        # Raise after INSERT within the same transaction: receipt and all effects roll back.
        denied(
            "do $proof$ begin perform public.api_launcher_observation("
            + literal(json.dumps(req3))
            + "::jsonb); perform 1/0; end $proof$",
            "22012",
        )
        assert (
            sql(database, "select count(*) from public.launcher_observations;") == "2"
        )
        sql(
            database,
            f"update public.seasons set status='discarded',discarded_at=now() where id='{sid}';",
        )
        assert (
            repo.execute("receive", request) == first.model_dump()
        )  # successful replay survives closed scope
        denied(call(req3), "PT409")
        sql(
            database,
            f"update public.trainers set globally_enabled=false where id='{tid}';",
        )
        denied(call(request | {"operation": "receipt"}), "PT403")
        # Restore precisely our fixture rows, then compare every public table.
        sql(
            database,
            f"""
          delete from public.launcher_observations where season_id='{sid}';
          delete from public.season_player_stats where season_player_id='{spid}';
          delete from public.season_players where id='{spid}';
          delete from public.seasons where id='{sid}';
          delete from public.trainers where id in ('{tid}','{other}');
        """,
        )
        assert snapshots(database) == before
        security = json.loads(
            sql(
                database,
                """select jsonb_build_object('rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
          'invoker',not p.prosecdef,'search_path',p.proconfig) from pg_class c cross join pg_proc p
          where c.oid='public.launcher_observations'::regclass and p.oid='public.api_launcher_observation(jsonb)'::regprocedure;""",
            )
        )
        assert security["rls"] and security["force_rls"] and security["invoker"]
        report = {
            "status": "PASS",
            "schema_sha256": sha256(dumps[0].encode()).hexdigest(),
            "schema_lines": len(dumps[0].splitlines()),
            "rebuilt_migrations": len(MIGRATIONS),
            "exact_public_table_restoration": len(before),
            "checks": [
                "private intake",
                "no competitive effects",
                "receipt replay",
                "concurrent receive",
                "rollback after insertion",
                "closed-scope replay",
                "disabled denial",
                "cross-owner denial",
                "malformed denial",
                "RLS/browser grants",
                "immutable service privileges",
            ],
            "security": security,
        }
        (args.evidence / "postgres.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
    finally:
        for database in created:
            run("dropdb", "postgres", [database])
        assert (
            sql(
                "postgres",
                "select count(*) from pg_database where datname like 'pokeapp_v2_validation_phase16_%';",
            )
            == "0"
        )


if __name__ == "__main__":
    main()
