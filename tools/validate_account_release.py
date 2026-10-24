import os, sys, json, hashlib, argparse
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path.cwd()))
from tools.validate_accounts_local import LocalPG
from tools.account_admin_bootstrap import bootstrap_sql

parser = argparse.ArgumentParser(
    description="Rehearse a backed-up V2 release on loopback only; never connects remotely."
)
parser.add_argument("--evidence-dir", type=Path, required=True)
parser.add_argument("--pg-bin", type=Path, required=True)
args = parser.parse_args()
out = args.evidence_dir.resolve()
inv = json.loads((out / "inventory.json").read_text())
baseline = json.loads((out / "before-count-hashes.json").read_text())
tables = sorted(
    t["table"]
    for t in inv["tables"]
    if t["schema"] == "public" and t["table"] not in ("app_settings", "shop_items")
)
triggers = [
    t for t in inv["triggers"] if t["table"] in tables and " DELETE " in t["definition"]
]
pre = []
for r in baseline:
    if not r["name"].startswith("public."):
        continue
    t = r["name"].split(".")[1]
    pre.append(
        f"if (select encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text)::text,'[]'),'UTF8')),'hex') from public.\"{t}\" x)<>'{r['sha256']}' then raise exception 'reset_baseline_changed:{t}'; end if;"
    )
sql = (
    "begin;\nset local lock_timeout='5s';\nset local statement_timeout='90s';\nlock table "
    + ",".join(
        'public."' + t + '"'
        for t in sorted(t["table"] for t in inv["tables"] if t["schema"] == "public")
    )
    + " in access exclusive mode;\ndo $reset$ begin if current_user<>'postgres' then raise exception 'operator_required'; end if;\n"
    + "\n".join(pre)
    + "\nend $reset$;\n"
)
for t in triggers:
    sql += f'alter table public."{t["table"]}" disable trigger "{t["name"]}";\n'
sql += (
    "with "
    + ",\n".join(
        f'd{i} as (delete from public."{t}" returning 1)' for i, t in enumerate(tables)
    )
    + "\nselect "
    + ",".join(f'(select count(*) from d{i}) as "{t}"' for i, t in enumerate(tables))
    + ";\n"
)
for t in triggers:
    sql += f'alter table public."{t["table"]}" enable trigger "{t["name"]}";\n'
sql += "commit;\n"
(out / "reviewed-reset-public.sql").write_text(sql, encoding="utf-8")
pg = LocalPG(args.pg_bin, 55482)
pg.env["PGTZ"] = "UTC0"
pg.start()
db = "pokeapp_accounts_release_restore"
checks = []
try:
    pg.sql(f"create database {db};", "postgres")
    pg.sql("drop schema public;", db)
    r = pg.command(
        "pg_restore",
        [
            "-h",
            "127.0.0.1",
            "-p",
            "55482",
            "-U",
            "postgres",
            "-d",
            db,
            "--no-owner",
            "--no-acl",
            str(out / "pre-reset-v2-postgres.dump"),
        ],
        ok=False,
    )
    assert r.returncode == 0, "restore failed"
    r = pg.sql(sql, db, ok=False)
    (out / "reset-local-private.log").write_text(r.stderr)
    assert r.returncode == 0, "reset proof failed; inspect private log"
    checks.append("explicit_atomic_52_table_reset")
    actual = [
        dict(name=a, count=int(b), sha256=c)
        for a, b, c in (
            line.split("|")
            for line in pg.sql(
                (out / "all-table-count-hashes.sql").read_text(), db
            ).stdout.splitlines()
        )
    ]
    for row in actual:
        if row["name"] in {"public." + t for t in tables}:
            assert row["count"] == 0
        else:
            assert row == next(r for r in baseline if r["name"] == row["name"]), row[
                "name"
            ]
    checks.append("all_53_other_tables_preserved")
    for n in ("050", "051", "052", "053"):
        migration = next(Path("supabase/v2/migrations").glob(n + "*.sql"))
        pg.sql(migration.read_text(encoding="utf-8"), db)
    checks.append("real_49_backup_upgrade_to_53")
    pg.sql(
        "insert into public.account_credential_policy(legacy_deadline) values('2026-10-24T00:00:00Z');",
        db,
    )
    reg = str(uuid4())
    row = json.loads(
        pg.sql(
            f"select public.sec_pin_registration_prepare('{reg}','Bootstrap Fixture','bootstrap-fixture',repeat('a',64),clock_timestamp()+interval '1 hour');",
            db,
        ).stdout
    )
    tid, aid = row["trainer_id"], row["auth_user_id"]
    pg.sql(
        f"insert into auth.users(id) values('{aid}');select public.sec_pin_registration_complete('{reg}',repeat('a',64),'{aid}');",
        db,
    )
    op = str(uuid4())
    statement = bootstrap_sql(
        tid, aid, op, "isolated-test-verification", "2026-10-01T00:00:00Z"
    )
    for role in ("anon", "authenticated", "service_role"):
        assert pg.sql(f"set role {role};" + statement, db, ok=False).returncode != 0
    checks.append("browser_and_service_role_cannot_bootstrap")
    assert (
        pg.sql(
            bootstrap_sql(
                tid, uuid4(), op, "isolated-test-verification", "2026-10-01T00:00:00Z"
            ),
            db,
            ok=False,
        ).returncode
        != 0
    )
    pg.sql(f"update public.trainers set globally_enabled=false where id='{tid}';", db)
    assert pg.sql(statement, db, ok=False).returncode != 0
    pg.sql(f"update public.trainers set globally_enabled=true where id='{tid}';", db)
    checks.append("wrong_auth_and_disabled_denied")
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: pg.sql(statement, db, ok=False), range(4)))
    assert all(r.returncode == 0 for r in results)
    assert (
        pg.sql(
            "select count(*) from public.account_commands where kind='operator_admin_bootstrap';",
            db,
        ).stdout.strip()
        == "1"
    )
    assert (
        pg.sql(
            f"select count(*) from public.trainers where is_admin and id='{tid}' and auth_user_id='{aid}';",
            db,
        ).stdout.strip()
        == "1"
    )
    checks.append("zero_admin_exact_binding_concurrent_idempotent_promotion")
    assert (
        pg.sql(
            bootstrap_sql(
                tid, aid, uuid4(), "different-operation", "2026-10-01T00:00:00Z"
            ),
            db,
            ok=False,
        ).returncode
        != 0
    )
    checks.append("second_promotion_denied")
    print(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "disabled_named_delete_triggers": len(triggers),
                "reset_tables": len(tables),
            }
        )
    )
    (out / "reset-bootstrap-local.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "reset_sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
                "reset_tables": tables,
                "named_delete_triggers": triggers,
            },
            indent=2,
        )
    )
finally:
    pg.sql(f"drop database if exists {db};", "postgres")
    pg.stop()
