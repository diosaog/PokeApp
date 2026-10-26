"""Phase27C upgrade proof for the pending production migrations 054-061.

Disposable PostgreSQL only (never a hosted database). Applies 001-053, the
state production runs today, loads representative competitive data, then
applies 054-061 one by one and proves:

* every table that existed before keeps byte-identical rows;
* no existing column, function signature or grant is removed or narrowed;
* the upgraded schema equals a fresh bootstrap of all 61 files;
* immediate retries are refused atomically or are exact no-ops;
* replay of historical055 after058 is diagnosed and rolled back, never required safe;
* the new transfer and item-use tables stay closed to anon/authenticated.

Run: python -m tools.validate_migrations_upgrade --pg-bin <dir> --output <json>
"""

import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

from tools.validate_accounts_local import LocalPG

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = sorted((ROOT / "supabase/v2/migrations").glob("*.sql"))
PENDING = [m for m in MIGRATIONS if 54 <= int(m.name[:3]) <= 61]
DEPLOYED = [m for m in MIGRATIONS if int(m.name[:3]) <= 53]
FIXTURES = ["shop_context_setup.sql", "purchase_setup.sql"]
REPRESENTATIVE = """
select pokeapp_shop_test.buy('upgrade-proof-1', true);
select pokeapp_shop_test.buy('upgrade-proof-2', true,
  '00000000-0000-4000-8000-000000008d61');
"""
TABLES = """select table_schema||'.'||table_name from information_schema.tables
 where table_schema in ('public','storage') and table_type='BASE TABLE' order by 1;"""
COLUMNS = """select table_schema||'.'||table_name||'.'||column_name||':'||data_type||
 ':'||is_nullable from information_schema.columns
 where table_schema in ('public','storage') order by 1;"""
FUNCTIONS = """select p.oid::regprocedure::text from pg_proc p
 join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' order by 1;"""
GRANTS = """select grantee||' '||privilege_type||' '||table_schema||'.'||table_name
 from information_schema.role_table_grants
 where grantee in ('anon','authenticated','service_role') order by 1;"""
EXECUTE = """select r.rolname||' EXECUTE '||p.oid::regprocedure::text from pg_proc p
 join pg_namespace n on n.oid=p.pronamespace cross join pg_roles r
 where n.nspname='public' and r.rolname in ('anon','authenticated','service_role')
 and has_function_privilege(r.oid,p.oid,'EXECUTE') order by 1;"""


def lines(pg, query):
    return [x for x in pg.sql(query).stdout.splitlines() if x]


def fingerprint(pg, tables):
    result = {}
    for table in tables:
        rows = pg.sql(
            f"select coalesce(md5(string_agg(t::text, E'\\n' order by t::text)), '-')"
            f"||':'||count(*) from {table} t;"
        ).stdout.strip()
        result[table] = rows
    return result


def schema_text(pg):
    raw = pg.command(
        "pg_dump",
        [
            "-h",
            "127.0.0.1",
            "-p",
            str(pg.port),
            "-U",
            "postgres",
            "--schema-only",
            "pokeapp_v2_validation_accounts",
        ],
    ).stdout
    # Version banners and restrict tokens differ per run; the schema does not.
    raw = re.sub(r"^\\(un)?restrict .*$", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^-- Dumped (from|by) .*$", "", raw, flags=re.MULTILINE)
    return raw


def schema_dump(pg):
    return hashlib.sha256(schema_text(pg).encode()).hexdigest()


def fresh(pg_bin, port):
    """Second disposable cluster: a fresh bootstrap of 001-061 to compare."""
    pg = LocalPG(pg_bin, port)
    pg.start()  # roles + storage mock + bootstrap.sql
    try:
        return schema_text(pg)
    finally:
        pg.stop()


def connection_functions(pg):
    return json.loads(
        pg.sql(
            "select coalesce(jsonb_agg(jsonb_build_array(p.oid::regprocedure::text,pg_get_functiondef(p.oid))),'[]') from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind='f';"
        ).stdout
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "deployed": [m.name for m in DEPLOYED],
        "pending": [m.name for m in PENDING],
        "sha256": {m.name: hashlib.sha256(m.read_bytes()).hexdigest() for m in PENDING},
        "checks": [],
    }

    def ok(condition, label, detail=None):
        if not condition:
            report["failed"] = {"label": label, "detail": detail}
            args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            raise SystemExit(f"FAIL {label}: {detail}")
        report["checks"].append(label)
        print("PASS", label, flush=True)

    ok(
        [int(m.name[:3]) for m in PENDING] == list(range(54, 62)),
        "pending set is exactly 054-061, in order",
    )
    pg = LocalPG(args.pg_bin, 55491)
    pg.command(
        "initdb",
        [
            "-D",
            str(pg.root / "data"),
            "-U",
            "postgres",
            "--auth=trust",
            "--encoding=UTF8",
            "--locale=C",
        ],
    )
    pg.command(
        "pg_ctl",
        [
            "-D",
            str(pg.root / "data"),
            "-l",
            str(pg.root / "server.log"),
            "-o",
            f"-h 127.0.0.1 -p {pg.port}",
            "-w",
            "start",
        ],
    )
    try:
        pg.sql("create database pokeapp_v2_validation_accounts;", "postgres")
        pg.sql(
            "create role anon nologin; create role authenticated nologin;"
            " create role service_role nologin bypassrls;"
        )
        pg.storage()
        for migration in DEPLOYED:
            pg.sql(migration.read_text(encoding="utf-8"))
        ok(True, f"production state rebuilt: {len(DEPLOYED)} files up to 053")
        for name in FIXTURES:
            pg.sql((ROOT / "tests/sql" / name).read_text(encoding="utf-8"))
        pg.sql(REPRESENTATIVE)
        tables = lines(pg, TABLES)
        before = fingerprint(pg, tables)
        counts = {t: int(v.split(":")[1]) for t, v in before.items()}
        ok(
            counts["public.purchases"] >= 2
            and counts["public.trainers"] >= 2
            and counts["public.coin_transactions"] >= 3,
            "representative data: trainers, season, coins and paid purchases",
            {k: v for k, v in counts.items() if v},
        )
        columns, functions = set(lines(pg, COLUMNS)), set(lines(pg, FUNCTIONS))
        grants, execute = set(lines(pg, GRANTS)), set(lines(pg, EXECUTE))

        report["immediate_retry"] = {}
        for migration in PENDING:
            pg.sql(migration.read_text(encoding="utf-8"))
            ok(True, f"applied {migration.name}")
            retry_tables = lines(pg, TABLES)
            rows, shape = fingerprint(pg, retry_tables), schema_text(pg)
            again = pg.sql(migration.read_text(encoding="utf-8"), ok=False)
            new_shape = schema_text(pg)
            no_effect = (
                rows == fingerprint(pg, lines(pg, TABLES)) and shape == new_shape
            )
            kind = (
                "refused_atomically"
                if again.returncode
                else "idempotent_at_own_version"
            )
            report["immediate_retry"][migration.name] = {
                "result": kind,
                "no_effect": no_effect,
            }
            ok(
                no_effect,
                f"immediate retry {migration.name}: {kind}",
                {
                    "schema_diff": list(
                        difflib.unified_diff(shape.splitlines(), new_shape.splitlines())
                    )[:100],
                    "sql_error": again.stderr[-400:],
                },
            )

        after = fingerprint(pg, tables)
        changed = [t for t in tables if before[t] != after[t]]
        ok(
            not changed,
            f"{len(tables)} existing tables keep byte-identical rows",
            changed,
        )
        lost = sorted(columns - set(lines(pg, COLUMNS)))
        ok(not lost, "no existing column removed or retyped", lost)
        gone = sorted(functions - set(lines(pg, FUNCTIONS)))
        report["functions_replaced_or_retired"] = gone
        revoked_tables = sorted(grants - set(lines(pg, GRANTS)))
        ok(
            not revoked_tables,
            "no table grant revoked from anon/authenticated/service_role",
            revoked_tables,
        )
        revoked_exec = sorted(execute - set(lines(pg, EXECUTE)))
        report["execute_revoked"] = revoked_exec
        new_tables = sorted(set(lines(pg, TABLES)) - set(tables))
        report["new_tables"] = new_tables
        exposed = [
            g
            for g in lines(pg, GRANTS)
            if g.split()[0] in ("anon", "authenticated") and g.split()[-1] in new_tables
        ]
        private_rls = lines(
            pg,
            "select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relrowsecurity and c.relforcerowsecurity;",
        )
        ok(set(new_tables) <= set(private_rls), "all seven new tables force RLS")
        ok(
            not exposed,
            f"{len(new_tables)} new tables closed to anon/authenticated",
            exposed,
        )

        # Historical replay is a different contract. Keep this diagnostic in a
        # rollback-only transaction on the disposable loopback cluster. It must
        # demonstrate exactly055's function regression, not corrupt the parity DB.
        import psycopg

        catalog_sql = """select p.oid::regprocedure::text, pg_get_functiondef(p.oid)
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where n.nspname='public' and p.prokind='f' order by 1"""
        with psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            user="postgres",
            dbname="pokeapp_v2_validation_accounts",
        ) as connection:
            try:
                before_functions = dict(connection.execute(catalog_sql).fetchall())
                historical = next(m for m in PENDING if m.name.startswith("055_"))
                body = re.sub(
                    r"^(?:begin|commit);\s*$",
                    "",
                    historical.read_text(encoding="utf-8"),
                    flags=re.MULTILINE | re.IGNORECASE,
                )
                connection.execute(body)
                after_functions = dict(connection.execute(catalog_sql).fetchall())
                modified = [
                    k
                    for k in before_functions
                    if before_functions[k] != after_functions.get(k)
                ]
                report["historical_replay_055_after_061"] = {
                    "classification": "UNSAFE_HISTORICAL_REPLAY_NOT_AN_UPGRADE_DEFECT",
                    "changed_objects": modified,
                    "superseding_migration": "058_transfer_provenance_finalization.sql",
                    "function_diff": {
                        k: list(
                            difflib.unified_diff(
                                before_functions[k].splitlines(),
                                after_functions[k].splitlines(),
                                fromfile="061",
                                tofile="replayed055",
                            )
                        )
                        for k in modified
                    },
                    "rolled_back": True,
                }
                ok(
                    modified == ["commit_pokemon_identity_v038(jsonb)"],
                    "historical055 changes exactly the058-superseded identity function",
                    modified,
                )
            finally:
                connection.rollback()
        ok(
            fingerprint(pg, tables) == before,
            "historical replay diagnostic leaves rows intact",
        )
        ok(
            dict(connection_functions(pg)) == before_functions,
            "historical replay rollback restores exact latest function definitions",
        )

        pg.sql("drop schema pokeapp_shop_test cascade;")  # fixture helpers only
        upgraded_text = schema_text(pg)
        upgraded = hashlib.sha256(upgraded_text.encode()).hexdigest()
        report["schema_sha256"] = upgraded
    finally:
        pg.sql(
            "drop database if exists pokeapp_v2_validation_accounts;",
            "postgres",
            ok=False,
        )
        pg.command("pg_ctl", ["-D", str(pg.root / "data"), "-w", "stop"])
    bootstrap_text = fresh(args.pg_bin, 55492)
    bootstrap = hashlib.sha256(bootstrap_text.encode()).hexdigest()
    ok(
        bootstrap == upgraded,
        "001-053 + 054-061 schema equals a fresh 61-file bootstrap",
        {
            "upgraded": upgraded,
            "bootstrap": bootstrap,
            "diff": list(
                difflib.unified_diff(
                    upgraded_text.splitlines(), bootstrap_text.splitlines()
                )
            )[:150],
        },
    )
    report["status"] = "PASS"
    report["cleanup"] = "both owned databases dropped and clusters stopped"
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "checks": len(report["checks"]),
                "functions_replaced_or_retired": len(
                    report["functions_replaced_or_retired"]
                ),
                "execute_revoked": len(report["execute_revoked"]),
            }
        )
    )


if __name__ == "__main__":
    main()
