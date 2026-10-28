"""Phase 30 release readiness: read-only production audit and schema parity.

``audit``  reads the production state through tools.production_readonly
           (Supabase read-only SQL, Railway reads, public GET/HEAD) and writes
           counts and states only — no personal data, no credential.
``parity`` rebuilds 001-053 (``--upto 64`` after the release) on a disposable loopback cluster shaped like the
           Supabase project (``postgres`` is not a superuser, Supabase default
           privileges, pgcrypto in ``extensions``) and compares its catalog with
           production's, object by object.

Run: python -m tools.phase30_release_audit audit|parity --pg-bin <dir> --output <json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = sorted((ROOT / "supabase/v2/migrations").glob("*.sql"))
# 054-064 went out with the final release; 065 (personal saves, «Mi PC»
# outside seasons) is the window after it.
DEPLOYED = [m for m in MIGRATIONS if int(m.name[:3]) <= 64]
PENDING = [m for m in MIGRATIONS if int(m.name[:3]) == 65]
WINDOW = f"{PENDING[0].name[:3]}-{PENDING[-1].name[:3]}"
SCHEMAS = "('public','v1_shadow')"


def _acl(column: str) -> str:
    return f"coalesce((select string_agg(a::text, ',' order by a::text) from unnest({column}) a), '-')"


# One text column ``x`` per object, the same SQL on both sides. Extension-owned
# objects are left out (pgcrypto lives in ``extensions`` on Supabase).
NOT_EXTENSION = (
    "not exists (select 1 from pg_depend e where e.objid={oid} and e.deptype='e')"
)
CATALOG = {
    "relations": f"""select 'rel '||n.nspname||'.'||c.relname||' kind='||c.relkind::text||' rls='||c.relrowsecurity
        ||' force='||c.relforcerowsecurity||' owner='||pg_get_userbyid(c.relowner)||' acl='||{_acl("c.relacl")} as x
        from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname in {SCHEMAS} and c.relkind in ('r','p','v','m','S','f')
        and {NOT_EXTENSION.format(oid="c.oid")}""",
    "columns": f"""select 'col '||n.nspname||'.'||c.relname||'.'||a.attname||' #'||a.attnum||' '||format_type(a.atttypid,a.atttypmod)
        ||' nn='||a.attnotnull||' def='||coalesce(pg_get_expr(d.adbin,d.adrelid),'-')||' gen='||a.attgenerated::text
        ||' identity='||a.attidentity::text||' acl='||{_acl("a.attacl")} as x
        from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
        left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
        where n.nspname in {SCHEMAS} and a.attnum>0 and not a.attisdropped and c.relkind in ('r','p','v','m','f')
        and {NOT_EXTENSION.format(oid="c.oid")}""",
    "constraints": f"""select 'con '||n.nspname||'.'||c.relname||' '||k.conname||' '||regexp_replace(pg_get_constraintdef(k.oid), '[[:space:]]+', ' ', 'g') as x
        from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace
        where n.nspname in {SCHEMAS}""",
    "indexes": f"select 'idx '||schemaname||'.'||indexname||' '||indexdef as x from pg_indexes where schemaname in {SCHEMAS}",
    "functions": f"""select 'fn '||p.oid::regprocedure::text||' md5='||md5(replace(pg_get_functiondef(p.oid),chr(13),''))
        ||' owner='||pg_get_userbyid(p.proowner)||' acl='||{_acl("p.proacl")} as x
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname in {SCHEMAS} and p.prokind in ('f','p') and {NOT_EXTENSION.format(oid="p.oid")}""",
    "views": f"""select 'view '||n.nspname||'.'||c.relname||' md5='||md5(pg_get_viewdef(c.oid)) as x
        from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname in {SCHEMAS} and c.relkind in ('v','m')""",
    "triggers": f"""select 'trg '||n.nspname||'.'||c.relname||' '||t.tgname||' md5='||md5(pg_get_triggerdef(t.oid))
        ||' enabled='||t.tgenabled::text as x
        from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
        where n.nspname in {SCHEMAS} and not t.tgisinternal""",
    "policies": """select 'pol '||schemaname||'.'||tablename||' '||policyname||' '||permissive||' '||roles::text||' '||cmd
        ||' md5='||md5(coalesce(qual,'')||'|'||coalesce(with_check,'')) as x
        from pg_policies where schemaname in ('public','v1_shadow','storage')""",
    "types": f"""select 'type '||n.nspname||'.'||t.typname||' '||t.typtype::text||' '||coalesce((select string_agg(e.enumlabel,','
        order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid),'') as x
        from pg_type t join pg_namespace n on n.oid=t.typnamespace
        where n.nspname in {SCHEMAS} and t.typtype in ('e','d','c')
        and (t.typrelid=0 or (select relkind from pg_class where oid=t.typrelid)='c')
        and {NOT_EXTENSION.format(oid="t.oid")}""",
    "schemas": "select 'schema '||nspname||' owner='||pg_get_userbyid(nspowner)||' acl='||"
    + _acl("nspacl")
    + " as x from pg_namespace where nspname in ('public','v1_shadow')",
}

SUPABASE_ROLES = [
    "anon", "authenticated", "authenticator", "dashboard_user", "pgbouncer",
    "service_role", "supabase_auth_admin", "supabase_etl_admin",
    "supabase_privileged_role", "supabase_read_only_user",
    "supabase_realtime_admin", "supabase_replication_admin",
    "supabase_storage_admin", "cli_login_postgres",
]  # fmt: skip


class SupabaseLikePG:
    """Disposable loopback PostgreSQL shaped like the Supabase V2 project.

    The bootstrap superuser is ``supabase_admin``; ``postgres`` is a plain role
    with CREATEROLE/CREATEDB/BYPASSRLS that owns the database, exactly as in
    production, so migrations run here with production's privileges. Default
    privileges grant anon/authenticated/service_role on new public objects, and
    pgcrypto lives in ``extensions`` (no migration uses uuid-ossp).
    """

    database = "pokeapp"

    def __init__(self, pg_bin: Path, port: int, parent: Path | None = None):
        # A cluster holding a copy of real data lives in the owner-only folder.
        self.bin, self.port = Path(pg_bin), port
        self.root = Path(tempfile.mkdtemp(prefix="pokeapp-phase30-pg-", dir=parent))
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.upper().startswith(("PG", "SUPABASE", "POKEAPP_V2_SUPABASE"))
        }
        self.env["PGTZ"] = "UTC0"

    def run(self, name, args, content: bytes | None = None, ok=True):
        if name == "pg_ctl":
            with (self.root / "pg_ctl.log").open("ab") as log:
                result = subprocess.run(
                    [str(self.bin / "pg_ctl.exe"), *args],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    env=self.env,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=120,
                    check=False,
                )
        else:
            result = subprocess.run(
                [str(self.bin / f"{name}.exe"), *args],
                input=content,
                capture_output=True,
                env=self.env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
        if ok and result.returncode:
            detail = (result.stderr or b"")[-3000:].decode("utf-8", "replace")
            raise RuntimeError(f"{name} failed: {detail}")
        return result

    def sql(self, text: str, user="postgres", database=None, ok=True):
        """Run a script with psql (bytes in: no newline translation)."""
        result = self.run(
            "psql",
            ["-h", "127.0.0.1", "-p", str(self.port), "-U", user,
             "-d", database or self.database, "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-f", "-"],
            text.encode("utf-8"),
            ok,
        )  # fmt: skip
        result.out = result.stdout.decode("utf-8")
        result.err = result.stderr.decode("utf-8", "replace")
        return result

    def lines(self, query: str, user="postgres") -> list[str]:
        return [x for x in self.sql(query + ";", user).out.splitlines() if x]

    def start(self, storage_mock=True):
        self.run("initdb", ["-D", str(self.root / "data"), "-U", "supabase_admin",
                            "--auth=trust", "--encoding=UTF8", "--locale=C"])  # fmt: skip
        self.run("pg_ctl", ["-D", str(self.root / "data"), "-l", str(self.root / "server.log"),
                            "-o", f"-h 127.0.0.1 -p {self.port}", "-w", "start"])  # fmt: skip
        roles = "".join(f"create role {r} nologin;" for r in SUPABASE_ROLES)
        self.sql(
            roles
            + "alter role service_role bypassrls; alter role supabase_read_only_user bypassrls;"
            " alter role authenticator login noinherit;"
            " grant anon, authenticated, service_role to authenticator;"
            " create role postgres login createrole createdb bypassrls;"
            " grant anon, authenticated, service_role, authenticator, supabase_privileged_role to postgres;"
            " create database pokeapp owner postgres;",
            "supabase_admin",
            "postgres",
        )
        setup = """
            grant usage on schema public to postgres, anon, authenticated, service_role;
            create schema extensions authorization postgres;
            grant usage on schema extensions to anon, authenticated, service_role;
            create extension pgcrypto schema extensions;
            alter role postgres set search_path = "$user", public, extensions;
            alter default privileges for role postgres in schema public grant all on tables to anon, authenticated, service_role;
            alter default privileges for role postgres in schema public grant all on functions to anon, authenticated, service_role;
            alter default privileges for role postgres in schema public grant all on sequences to anon, authenticated, service_role;
        """
        if storage_mock:
            # Policy-only target for 013/044/051/056. In production storage.objects
            # belongs to supabase_storage_admin and the platform lets postgres
            # manage its policies; here postgres owns the mock instead.
            setup += """
            create schema storage authorization supabase_admin;
            grant usage on schema storage to postgres, anon, authenticated, service_role;
            create table storage.buckets(id text primary key, name text, public boolean,
              file_size_limit bigint, allowed_mime_types text[]);
            create table storage.objects(id uuid primary key default gen_random_uuid(),
              bucket_id text, name text, owner uuid, owner_id text);
            alter table storage.buckets owner to postgres;
            alter table storage.objects owner to postgres;
            alter table storage.objects enable row level security;
            grant all on storage.objects, storage.buckets to anon, authenticated, service_role;
            """
        self.sql(setup, "supabase_admin")

    def stop(self, remove=False):
        self.run(
            "pg_ctl",
            ["-D", str(self.root / "data"), "-w", "-m", "fast", "stop"],
            ok=False,
        )
        if remove:
            shutil.rmtree(self.root, ignore_errors=True)


def catalog_local(pg: SupabaseLikePG) -> dict[str, list[str]]:
    return {
        name: sorted(pg.lines(sql, "supabase_admin")) for name, sql in CATALOG.items()
    }


def catalog_production() -> dict[str, list[str]]:
    from tools.production_readonly import query

    return {name: sorted(r["x"] for r in query(sql)) for name, sql in CATALOG.items()}


def sha(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def compare(production: dict, local: dict) -> dict:
    report = {}
    for name in CATALOG:
        prod, loc = set(production[name]), set(local[name])
        report[name] = {
            "production": len(prod),
            "repository_053": len(loc),
            "only_production": sorted(prod - loc),
            "only_repository": sorted(loc - prod),
            "sha256_production": sha(sorted(prod)),
            "sha256_repository": sha(sorted(loc)),
        }
    return report


def parity(args) -> dict:
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        built = [m for m in MIGRATIONS if int(m.name[:3]) <= args.upto]
        for migration in built:
            pg.sql(migration.read_text(encoding="utf-8"))
        local = catalog_local(pg)
    finally:
        pg.stop(remove=True)
    production = catalog_production()
    report = compare(production, local)
    return {
        "check": f"production catalog vs repository 001-{args.upto:03d} on a Supabase-shaped cluster",
        "migrations_rebuilt": len(built),
        "identical": all(
            not v["only_production"] and not v["only_repository"]
            for v in report.values()
        ),
        "catalog": report,
    }


# Tables whose row counts are recorded (counts only, never contents).
COUNTED = "('public','v1_shadow','storage','auth','supabase_migrations')"


def audit(args) -> dict:
    from tools.production_readonly import (
        WEB,
        http,
        query,
        railway_deployments,
        railway_variables,
        supabase_get,
    )

    project = supabase_get("")
    backups = supabase_get("/database/backups")
    history = query(
        "select version, name from supabase_migrations.schema_migrations order by version"
    )
    names = [r["name"] for r in history]
    tables = query(
        f"""select n.nspname||'.'||c.relname as t from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where c.relkind in ('r','p') and n.nspname in {COUNTED} order by 1"""
    )
    counts = {}
    for chunk in range(0, len(tables), 40):
        part = [r["t"] for r in tables[chunk : chunk + 40]]
        union = " union all ".join(
            f"select '{t}' as t, count(*) as n from {'.'.join(chr(34) + p + chr(34) for p in t.split('.'))}"
            for t in part
        )
        counts.update({r["t"]: r["n"] for r in query(union)})
    pending_objects = query(
        """select c.relname as name from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relname in ('item_use_authorizations','item_use_verifications',
        'item_use_artifacts','item_use_transfers','item_use_transfer_legs','transfer_provenance',
        'transfer_commit_permits','admin_incident_commands','trainer_personal_saves')
        union all select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname='public' and p.proname in ('api_prepare_item_use','api_prepare_transfer',
        'admin_incident_overview','config_division_count','admin_robbery_cancel')
        union all select rolname from pg_roles where rolname='pokeapp_item_verifier'"""
    )
    seasons = query(
        """select s.status, count(*) as n,
        count(*) filter (where exists (select 1 from public.season_config_versions v where v.season_id=s.id
          and not (v.division_sizes ? 'B'))) as without_b
        from public.seasons s group by 1 order by 1"""
    )
    status_tables = query(
        """select c.relname as t from information_schema.columns i
        join pg_class c on c.relname=i.table_name join pg_namespace n on n.oid=c.relnamespace and n.nspname=i.table_schema
        where i.table_schema='public' and i.column_name='status' and c.relkind='r' order by 1"""
    )
    states = query(
        " union all ".join(
            f"select '{r['t']}' as t, status::text as status, count(*) as n from public.{r['t']} group by 2"
            for r in status_tables
        )
    )
    activity = query(
        """select (select max(created_at) from public.coin_transactions)::text as last_coin,
        (select max(purchased_at) from public.purchases)::text as last_purchase,
        (select max(updated_at) from public.seasons)::text as last_season_change,
        (select max(uploaded_at) from public.save_files)::text as last_save_upload"""
    )
    variables = railway_variables()
    flags = {
        k: variables.get(k, "<unset>")
        for k in (
            "POKEAPP_ADMIN_INCIDENTS_ENABLED",
            "POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED",
            "POKEAPP_TRANSFER_ENGINEERING_ENABLED",
            "POKEAPP_ACCOUNT_MANAGEMENT_ENABLED",
        )
    }
    deployments = [
        {k: d.get(k) for k in ("id", "status", "createdAt")}
        for d in railway_deployments(5)
    ]
    health = http("GET", "https://pokeapp-api-production.up.railway.app/health")
    openapi = http(
        "GET", "https://pokeapp-api-production.up.railway.app/openapi.json"
    ).json()
    launcher = http("HEAD", WEB + "/launcher/download")
    feed = http("GET", WEB + "/launcher/updates/stable.json")
    return {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "supabase": {
            "project": project["id"],
            "name": project["name"],
            "status": project["status"],
            "postgres": project.get("database", {}).get("version"),
            "backups": {
                "pitr_enabled": backups.get("pitr_enabled"),
                "walg_enabled": backups.get("walg_enabled"),
                "platform_backups_listed": len(backups.get("backups") or []),
            },
            "migration_history": {
                "records": len(history),
                "first": names[0],
                "last": names[-1],
                "repository_files_recorded": sorted(
                    m.stem for m in DEPLOYED if m.stem in names
                ),
                "repository_files_not_recorded": sorted(
                    m.stem for m in DEPLOYED if m.stem not in names
                ),
                "records_without_repository_file": sorted(
                    set(names) - {m.stem for m in MIGRATIONS}
                ),
                "pending_recorded": sorted(m.stem for m in PENDING if m.stem in names),
            },
            "release_objects_present": sorted(r["name"] for r in pending_objects),
            "row_counts": counts,
            "seasons_by_status": seasons,
            "states_by_table": states,
            "activity": activity[0],
        },
        "railway": {
            "deployments": deployments,
            "variable_names": sorted(variables),
            "feature_flags": flags,
        },
        "api": {
            "health": health.status_code,
            "routes": len(openapi.get("paths", {})),
            "division_sizes_required": openapi.get("components", {})
            .get("schemas", {})
            .get("DivisionSizes", {})
            .get("required"),
        },
        "web": {
            "launcher_download": {
                "status": launcher.status_code,
                "bytes": launcher.headers.get("content-length"),
                "etag": launcher.headers.get("etag"),
            },
            "update_feed_content_type": feed.headers.get("content-type"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "parity"])
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--port", type=int, default=55530)
    parser.add_argument(
        "--upto", type=int, default=53, help="53 before the release, 64 after"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args) if args.command == "audit" else parity(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps({k: v for k, v in report.items() if k != "catalog"}, default=str)[
            :4000
        ]
    )


if __name__ == "__main__":
    main()
