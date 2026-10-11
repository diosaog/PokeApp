"""Real PostgreSQL proof for the private, isolated Phase 11 import.

Only creates fresh local validation databases. Raw subprocess output and source
data stay in the caller's private evidence directory, never in console output.
Build and proof stages can run separately without rebuilding an unchanged schema.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from threading import Lock
from typing import Any
from uuid import uuid4

from tools import validate_supabase_v2_schema as schema


ROOT = Path(__file__).resolve().parents[1]
MANUAL_TRAINER = "11111111-1111-4111-8111-111111111111"
MANUAL_SEASON = "22222222-2222-4222-8222-222222222222"
MANUAL_PLAYER = "33333333-3333-4333-8333-333333333333"
FIXTURE_SQL = f"""
insert into public.trainers(id, display_name, slug)
values ('{MANUAL_TRAINER}', 'Local preservation fixture', 'phase11_local_owner');
insert into public.seasons(id, name, status, started_at, created_by_trainer_id)
values ('{MANUAL_SEASON}', 'Local active manual season', 'active',
        '2026-10-01T00:00:00Z', '{MANUAL_TRAINER}');
insert into public.season_players(id, season_id, trainer_id)
values ('{MANUAL_PLAYER}', '{MANUAL_SEASON}', '{MANUAL_TRAINER}');
insert into public.season_player_stats(season_player_id, season_id, trainer_id)
values ('{MANUAL_PLAYER}', '{MANUAL_SEASON}', '{MANUAL_TRAINER}');
"""
CLEANUP_FIXTURE_SQL = f"""
delete from public.season_player_stats where season_player_id='{MANUAL_PLAYER}';
delete from public.season_players where id='{MANUAL_PLAYER}';
delete from public.seasons where id='{MANUAL_SEASON}';
delete from public.trainers where id='{MANUAL_TRAINER}';
"""


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def fingerprint_sources() -> dict[str, str]:
    paths = [*schema.MIGRATIONS, schema.BOOTSTRAP_SQL]
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


class LocalPostgres:
    def __init__(self, args: argparse.Namespace):
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Phase 11 proof only permits loopback PostgreSQL")
        if not re.fullmatch(r"pokeapp_v2_validation_phase11_[a-z0-9_]+", args.database_prefix):
            raise ValueError("Invalid disposable Phase 11 database prefix")
        self.args = args
        self.out = args.evidence.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.command_index = max((int(p.name.split("-")[1]) for p in self.out.glob("command-*.log")), default=0)
        self.command_lock = Lock()

    def run(self, program: str, database: str, tail: list[str], sql: str | None = None,
            *, failure: bool = False) -> str:
        command = [str(self.args.pg_bin / (program + (".exe" if os.name == "nt" else ""))),
                   "-h", self.args.host, "-p", str(self.args.port), "-U", self.args.user]
        command += (["-d", database] if program in {"psql", "pg_dump"} else []) + tail
        env = os.environ.copy()
        env["PGPASSWORD"] = self.args.password
        env["PGCLIENTENCODING"] = "UTF8"
        with self.command_lock:
            self.command_index += 1
            index = self.command_index
        result = subprocess.run(command, input=sql, capture_output=True, text=True,
                                encoding="utf-8", env=env, cwd=ROOT, check=False)
        log = self.out / f"command-{index:04d}-{program}.log"
        log.write_text(result.stdout + "\nSTDERR\n" + result.stderr, encoding="utf-8")
        if failure:
            if result.returncode == 0:
                raise AssertionError(f"Expected rejection; private log {log.name}")
            if not re.search(r"ERROR:\s+(22012|23503|23505|23514|42501):", result.stderr):
                raise AssertionError(f"Unexpected error instead of intended denial; private log {log.name}")
        elif result.returncode:
            raise RuntimeError(f"Local {program} failed; inspect private log {log.name}")
        return result.stdout

    def sql(self, database: str, sql: str, *, failure: bool = False) -> str:
        return self.run("psql", database, ["-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose"],
                        sql, failure=failure).strip()

    def json(self, database: str, sql: str) -> Any:
        return json.loads(self.sql(database, sql))

    def tables(self, database: str, namespace: str) -> list[str]:
        return self.json(database, "select coalesce(jsonb_agg(tablename order by tablename), '[]'::jsonb) "
                         f"from pg_tables where schemaname='{namespace}';")

    def snapshot(self, database: str, namespace: str, *, receipt_clocks: bool = True) -> dict[str, str]:
        result = {}
        for table in self.tables(database, namespace):
            expression = "to_jsonb(t)"
            if namespace == "v1_shadow" and table == "batches" and not receipt_clocks:
                expression += " - 'completed_at'"
            # JSONB preserves bytea as escaped text and exact numeric values. Only
            # the optional operational receipt clock is excluded from comparison.
            sql = (
                "select encode(sha256(convert_to(coalesce(jsonb_agg(r order by r::text), "
                f"'[]'::jsonb)::text, 'UTF8')), 'hex') from (select {expression} as r "
                f'from "{namespace}"."{table}" t) rows;'
            )
            result[table] = self.sql(database, sql)
        return result


def build(pg: LocalPostgres) -> dict[str, Any]:
    sources = fingerprint_sources()
    result: dict[str, Any] = {"source_sha256": sources, "builds": [], "status": "RUNNING"}
    dumps = []
    for kind, suffix in (("migrations", "a"), ("bootstrap", "b")):
        database = f"{pg.args.database_prefix}_{suffix}"
        if pg.args.resume_build and kind == "bootstrap":
            database += "_" + uuid4().hex[:6]
        exists = pg.sql("postgres", f"select count(*) from pg_database where datname='{database}';")
        retained = pg.args.resume_build and kind == "migrations"
        if exists != "0" and not retained:
            raise RuntimeError("Build refuses an existing database; use proof stage for a prepared build")
        if retained:
            prior = json.loads((pg.out / "migrations-build-evidence.json").read_text(encoding="utf-8"))
            assert prior["source_sha256"] == sources and prior["database"] == database
        else:
            pg.run("createdb", "postgres", [database])
            pg.sql(database, schema.SUPABASE_ROLE_MOCK_SQL)
            for path in schema.MIGRATIONS if kind == "migrations" else [schema.BOOTSTRAP_SQL]:
                pg.sql(database, path.read_text(encoding="utf-8"))
        actual = pg.tables(database, "public")
        if sorted(actual) != sorted(schema.EXPECTED_TABLES):
            raise AssertionError("Public table inventory mismatch")
        shadow = pg.tables(database, "v1_shadow")
        if len(shadow) != 15:
            raise AssertionError("Private table inventory mismatch")
        raw = pg.run("pg_dump", database, ["--schema-only", "--schema=public", "--schema=v1_shadow"])
        normalized = "\n".join(line for line in raw.splitlines()
                               if not line.startswith(("\\restrict ", "\\unrestrict "))) + "\n"
        if retained:
            assert normalized == (pg.out / f"schema-{suffix}.sql").read_text(encoding="utf-8"), "Retained build changed"
        else:
            (pg.out / f"schema-{suffix}.sql").write_text(normalized, encoding="utf-8")
        dumps.append(normalized)
        result["builds"].append({"kind": kind, "database": database,
                                 "sha256": sha256(normalized.encode()).hexdigest(),
                                 "lines": len(normalized.splitlines()),
                                 "public_tables": len(actual), "private_tables": len(shadow),
                                 "retained_verified_build": retained})
        if kind == "migrations" and not retained:
            write(pg.out / "migrations-build-evidence.json", {"source_sha256": sources, "database": database})
        print(f"PASS {'retained verified' if retained else 'fresh'} {kind} build "
              f"({len(actual)} public / {len(shadow)} private tables)", flush=True)
    assert dumps[0] == dumps[1], "Schema/grants/ownership parity mismatch"
    assert sources == fingerprint_sources(), "Schema source changed during build"
    result["status"] = "PASS"
    result["normalization"] = "Only random pg_dump restrict/unrestrict tokens removed"
    write(pg.out / "build-evidence.json", result)
    return result


def check_security(pg: LocalPostgres, database: str) -> dict[str, Any]:
    result = pg.json(database, """
select jsonb_build_object(
 'tables', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
             where n.nspname='v1_shadow' and c.relkind='r'),
 'missing_rls', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
             where n.nspname='v1_shadow' and c.relkind='r' and not (relrowsecurity and relforcerowsecurity)),
 'role_schema_access', (select count(*) from (values ('anon'),('authenticated'),('service_role')) r(role)
             where has_schema_privilege(role,'v1_shadow','USAGE') or has_schema_privilege(role,'v1_shadow','CREATE')),
 'role_table_access', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
             cross join (values ('anon'),('authenticated'),('service_role')) r(role)
             where n.nspname='v1_shadow' and c.relkind='r'
               and (has_table_privilege(role,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                 or has_any_column_privilege(role,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))),
 'public_grants', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
             cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
             where n.nspname='v1_shadow' and c.relkind='r' and a.grantee=0),
 'functions', (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
             where n.nspname='v1_shadow'),
 'foreign_public_fks', (select count(*) from pg_constraint k
             join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace
             join pg_class f on f.oid=k.confrelid join pg_namespace fn on fn.oid=f.relnamespace
             where n.nspname='v1_shadow' and fn.nspname='public' and k.contype='f'));
""")
    assert result == {"tables": 15, "missing_rls": 0, "role_schema_access": 0,
                      "role_table_access": 0, "public_grants": 0, "functions": 0,
                      "foreign_public_fks": 0}, "Private security catalog mismatch"
    for role in ("anon", "authenticated", "service_role"):
        for table in pg.tables(database, "v1_shadow"):
            pg.sql(database, f"begin; set local role {role}; select count(*) from v1_shadow.{table}; rollback;",
                   failure=True)
        pg.sql(database, f"begin; set local role {role}; delete from v1_shadow.runs; rollback;", failure=True)
    result["actual_role_denials"] = 48
    return result


def check_constraints(pg: LocalPostgres, database: str) -> list[str]:
    """Reject impossible relational facts using actual surviving source rows."""
    cases = {
        "duplicate season participant": """
insert into v1_shadow.participants
select run_id, gen_random_uuid(), season_id, trainer_id, division, seed_order, flags
from v1_shadow.participants limit 1;
""",
        "progress from another owner's save": """
update v1_shadow.progress p set trainer_id=(
 select t.trainer_id from v1_shadow.participants t
 where t.run_id=p.run_id and t.season_id=p.season_id and t.trainer_id<>p.trainer_id limit 1)
where save_id is not null;
""",
        "unknown wallet with fabricated balance": """
update v1_shadow.wallets set known=false where known;
""",
        "known wallet missing a component": """
update v1_shadow.wallets set spend=null where known;
""",
        "nonfinite wallet component": """
update v1_shadow.wallets set spend='NaN'::numeric where known;
""",
        "infinite wallet component": """
update v1_shadow.wallets set spend='Infinity'::numeric where known;
""",
        "wallet balance does not reconcile": """
update v1_shadow.wallets set balance=balance+1 where known;
""",
        "nonfinite purchase price": """
update v1_shadow.purchases set price='NaN'::numeric;
""",
        "Cup match contains nonmember": """
update v1_shadow.cup_matches m set first_trainer_id=(
 select t.id from v1_shadow.trainers t where t.run_id=m.run_id and not exists (
   select 1 from v1_shadow.cup_participants p
   where p.run_id=m.run_id and p.cup_id=m.cup_id and p.trainer_id=t.id) limit 1);
""",
        "Cup winner outside pairing": """
update v1_shadow.cup_matches m set winner_id=(
 select p.trainer_id from v1_shadow.cup_participants p
 where p.run_id=m.run_id and p.cup_id=m.cup_id
 and p.trainer_id<>m.first_trainer_id and p.trainer_id<>m.second_trainer_id limit 1);
""",
        "Cup self match": """
update v1_shadow.cup_matches set second_trainer_id=first_trainer_id;
""",
    }
    before = pg.snapshot(database, "v1_shadow")
    for sql in cases.values():
        pg.sql(database, "begin;" + sql + "rollback;", failure=True)
        assert before == pg.snapshot(database, "v1_shadow"), "Constraint probe left residue"
    return list(cases)


def proof(pg: LocalPostgres, built: dict[str, Any]) -> dict[str, Any]:
    from tools.phase11_import import build_plan
    from tools.phase11_sql import render_batch, render_prepare, render_verify

    assert built["status"] == "PASS" and built["source_sha256"] == fingerprint_sources()
    plan = build_plan(pg.args.capture, pg.args.parsed, pg.args.save_directory, pg.args.candidates)
    assert plan == build_plan(pg.args.capture, pg.args.parsed, pg.args.save_directory, pg.args.candidates), "Nondeterministic plan"
    databases = [item["database"] for item in built["builds"]]
    assert databases[0] == f"{pg.args.database_prefix}_a"
    assert re.fullmatch(re.escape(pg.args.database_prefix) + r"_b(?:_[a-z0-9]+)?", databases[1])
    evidence: dict[str, Any] = {"status": "RUNNING", "groups": [], "rollback_boundaries": 0,
                                "started_utc": datetime.now(timezone.utc).isoformat(),
                                "plan_hash": plan["run"]["plan_hash"],
                                "source_sha256": {
                                    str(path.relative_to(ROOT)).replace("\\", "/"):
                                    sha256(path.read_bytes()).hexdigest()
                                    for path in (ROOT / "tools/phase11_import.py",
                                                 ROOT / "tools/phase11_sql.py", Path(__file__))}}
    originals = {db: pg.snapshot(db, "public") for db in databases}
    controls = {}
    try:
        for db in databases:
            assert pg.sql(db, "select count(*) from v1_shadow.runs;") == "0", "Unexpected prior import"
            pg.sql(db, "begin;" + FIXTURE_SQL + "commit;")
            controls[db] = pg.snapshot(db, "public")
        a, b = databases
        pg.sql(a, render_prepare(plan))
        for batch in plan["batches"]:
            pg.sql(a, render_batch(plan, batch["ordinal"]) + """
select 1 / case when to_regclass('pg_temp.phase11_expected_plan') is null
then 1 else 0 end as temporary_payload_removed_after_commit;
""")
        pg.sql(a, render_verify(plan, finalize=True))
        reference = pg.snapshot(a, "v1_shadow", receipt_clocks=False)
        exact_reference = pg.snapshot(a, "v1_shadow")
        evidence["groups"].append("clean deterministic import and complete row reconciliation")

        pg.sql(a, render_prepare(plan))
        for batch in plan["batches"]:
            pg.sql(a, render_batch(plan, batch["ordinal"]))
        pg.sql(a, render_verify(plan, finalize=True))
        assert exact_reference == pg.snapshot(a, "v1_shadow"), "Replay changed rows or operational receipts"
        evidence["groups"].append("complete replay preserves all rows and receipt timestamps")

        pg.sql(b, render_prepare(plan))
        for batch in plan["batches"]:
            ordinal = batch["ordinal"]
            before = pg.snapshot(b, "v1_shadow")
            if ordinal == 3:
                table = next(table for table, rows in batch["tables"].items() if rows)
                # Keep this same connection alive after the deliberate error;
                # COMMIT of the aborted transaction performs a full rollback.
                pg.sql(b, "\\set ON_ERROR_STOP off\n"
                       + render_batch(plan, ordinal, fail_after_table=table)
                       + "\\set ON_ERROR_STOP on\n"
                       + "select 1 / case when to_regclass('pg_temp.phase11_expected_plan') is null "
                         "then 1 else 0 end as temporary_payload_removed_after_rollback;")
                assert before == pg.snapshot(b, "v1_shadow"), "Same-session failure left residue"
            for table, rows in batch["tables"].items():
                if rows:
                    pg.sql(b, render_batch(plan, ordinal, fail_after_table=table), failure=True)
                    assert before == pg.snapshot(b, "v1_shadow"), "Failure left partial rows or receipt"
                    evidence["rollback_boundaries"] += 1
            if ordinal == plan["batches"][-1]["ordinal"]:
                # Separate psql processes concurrently execute the same final
                # command. Both must succeed with one authoritative effect.
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = [pool.submit(pg.sql, b, render_batch(plan, ordinal)) for _ in range(2)]
                    for future in results:
                        future.result()
            else:
                pg.sql(b, render_batch(plan, ordinal))
            if ordinal == 2:
                pg.sql(b, render_verify(plan))
                # Every invocation opens a new connection; this deliberately
                # loses all process/transaction state, then resumes by journal.
                pg.sql(b, render_prepare(plan))
                for prior in plan["batches"][:2]:
                    pg.sql(b, render_batch(plan, prior["ordinal"]))
        pg.sql(b, render_verify(plan, finalize=True))
        assert reference == pg.snapshot(b, "v1_shadow", receipt_clocks=False), "Restart diverged from reference"
        evidence["groups"].append("interruption after batch 2, prefix replay, restart equals clean run")
        evidence["groups"].append("concurrent final-batch replay produces one effect")
        evidence["groups"].append("injected failure after each nonempty batch table rolls back exactly")
        evidence["groups"].append("transaction-local payload removed after commit and same-session rollback")

        stale = deepcopy(plan)
        stale["run"]["plan_hash"] = "0" * 64
        pg.sql(b, render_prepare(stale), failure=True)
        pg.sql(b, render_verify(stale), failure=True)
        assert reference == pg.snapshot(b, "v1_shadow", receipt_clocks=False)
        evidence["groups"].append("stale plan rejected without mutation")

        # A trusted-owner corruption is local-only and intentionally committed
        # between verification calls, proving full row reconciliation is real.
        changed = pg.json(b, "select jsonb_build_object('id',id,'name',name) from v1_shadow.trainers order by id limit 1;")
        pg.sql(b, f"update v1_shadow.trainers set name=name || ' altered' where id='{changed['id']}';")
        pg.sql(b, render_verify(plan), failure=True)
        pg.sql(b, render_batch(plan, plan["batches"][-1]["ordinal"]), failure=True)
        escaped = changed["name"].replace("'", "''")
        pg.sql(b, f"update v1_shadow.trainers set name='{escaped}' where id='{changed['id']}';")
        pg.sql(b, render_verify(plan, finalize=True))
        assert reference == pg.snapshot(b, "v1_shadow", receipt_clocks=False)
        evidence["groups"].append("changed imported fact blocks verify and replay")

        evidence["constraint_denials"] = check_constraints(pg, b)
        evidence["groups"].append("relational source ownership, wallet precision and Cup constraints")
        evidence["security"] = check_security(pg, b)
        evidence["groups"].append("RLS, forced RLS, grants, columns and actual three-role denials")
        for db in databases:
            assert controls[db] == pg.snapshot(db, "public"), "Public/manual data changed"
        evidence["groups"].append("all public tables and active manual season remain exact")
        evidence["public_tables_preserved"] = len(controls[a])
        evidence["private_tables_reconciled"] = len(reference)
        evidence["batch_count"] = len(plan["batches"])
        evidence["deterministic_destination_hashes"] = reference
        evidence["status"] = "PASS"
    finally:
        # The databases were freshly created by this harness, never remote or
        # existing owner databases. Remove only this run's isolated fixtures.
        cleanup = {}
        for db in databases:
            tables = pg.tables(db, "v1_shadow")
            pg.sql(db, "begin; truncate " + ",".join(f"v1_shadow.{t}" for t in tables)
                   + ";" + CLEANUP_FIXTURE_SQL + "commit;")
            assert originals[db] == pg.snapshot(db, "public"), "Local public restoration mismatch"
            assert pg.sql(db, "select count(*) from v1_shadow.runs;") == "0"
            cleanup[db] = {"public_tables_restored": len(originals[db]), "private_fixture_rows": 0}
        evidence["cleanup"] = cleanup
        evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write(pg.out / "proof-evidence.json", evidence)
    print(f"PASS Phase 11 PostgreSQL: {len(evidence['groups'])} groups / "
          f"{evidence['rollback_boundaries']} rollback boundaries / "
          f"{evidence['public_tables_preserved']} public tables preserved", flush=True)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55439)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    parser.add_argument("--database-prefix", default="pokeapp_v2_validation_phase11_" + uuid4().hex[:8])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--stage", choices=("build", "proof", "all"), default="all")
    parser.add_argument("--resume-build", action="store_true", help="Retain a verified migrations build and retry bootstrap only")
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--parsed", type=Path)
    parser.add_argument("--save-directory", type=Path)
    parser.add_argument("--candidates", type=Path)
    args = parser.parse_args()
    if args.stage != "build" and any(value is None for value in (args.capture, args.parsed, args.save_directory)):
        parser.error("proof requires --capture, --parsed and --save-directory")
    pg = LocalPostgres(args)
    built = build(pg) if args.stage != "proof" else json.loads((pg.out / "build-evidence.json").read_text(encoding="utf-8"))
    if args.stage != "build":
        proof(pg, built)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
