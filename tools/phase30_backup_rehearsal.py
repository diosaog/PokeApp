"""Phase 30: verified logical backup of production and a 054-064 rehearsal on it.

``capture``  opens ONE read-only REPEATABLE READ transaction on production,
             exports its snapshot, runs pg_dump on that snapshot and, in the same
             transaction, records per-table count+hash and the catalog. The dump
             and the fingerprints therefore describe exactly the same instant.
             The connection comes from the Supabase CLI (``db dump --dry-run``:
             its short-lived platform login role); the password stays in memory.
``rehearse`` restores the dump into a disposable Supabase-shaped loopback
             cluster, proves the restore exact (rows and catalog), then applies
             054-064 one by one as the non-superuser ``postgres`` role, as the
             platform would, and proves rows, reads, privileges and the final
             schema.

Nothing is written to production. Backups go to an owner-only folder outside the
repository; the repository only receives the sanitized summary.

Run: python -m tools.phase30_backup_rehearsal capture|rehearse --pg-bin <dir> --dir <private dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

from tools.phase30_release_audit import (
    CATALOG,
    DEPLOYED,
    MIGRATIONS,
    PENDING,
    WINDOW,
    SupabaseLikePG,
    catalog_local,
    compare,
)
from tools.production_readonly import SUPABASE_REF

ROOT = Path(__file__).resolve().parents[1]
DUMPED_SCHEMAS = ["public", "auth", "storage", "v1_shadow", "supabase_migrations"]
# Live credentials of signed-in sessions: never copied. Restoring them would be
# wrong anyway; after a restore people sign in again.
EPHEMERAL = [
    "auth.sessions",
    "auth.refresh_tokens",
    "auth.mfa_amr_claims",
    "auth.mfa_challenges",
    "auth.one_time_tokens",
    "auth.flow_state",
]
TABLES = """select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where c.relkind in ('r','p') and n.nspname in ({schemas}) order by 1"""


def fingerprint_sql(table: str) -> str:
    quoted = ".".join(f'"{p}"' for p in table.split("."))
    return (
        f"select '{table}', count(*), coalesce(md5(string_agg(t::text, E'\\n' order by t::text)), '-') "
        f"from {quoted} t"
    )


def connection_env() -> dict[str, str]:
    """PG* variables for a short-lived platform login, kept in memory only."""
    result = subprocess.run(
        [shutil.which("npx.cmd"), "--yes", "supabase@2.122.0", "db", "dump",
         "--linked", "--project-ref", SUPABASE_REF, "--dry-run"],
        cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
    )  # fmt: skip
    if result.returncode:
        raise SystemExit("Supabase CLI could not prepare the read-only connection")
    env = {}
    for line in result.stdout.splitlines():
        if line.startswith("export PG"):
            parts = shlex.split(line)
            key, value = parts[1].split("=", 1)
            if key in ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"):
                env[key] = value
    if not {"PGHOST", "PGUSER", "PGPASSWORD"} <= set(env):
        raise SystemExit("Supabase CLI returned no usable connection")
    return env


def capture(args) -> dict:
    import psycopg

    out = args.dir
    dump = out / f"pre-release-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.dump"
    assert not dump.exists(), "a retained backup is never overwritten"
    env = connection_env()
    connection = psycopg.connect(
        host=env["PGHOST"],
        port=int(env.get("PGPORT", "5432")),
        user=env["PGUSER"],
        password=env["PGPASSWORD"],
        dbname=env.get("PGDATABASE", "postgres"),
        sslmode="require",
        connect_timeout=20,
        options="-c default_transaction_read_only=on",
        autocommit=True,  # the explicit BEGIN below opens the only transaction
    )
    try:
        connection.execute("set role postgres")
        connection.execute("begin isolation level repeatable read read only")
        snapshot = connection.execute("select pg_export_snapshot()").fetchone()[0]
        child_env = {
            k: v
            for k, v in __import__("os").environ.items()
            if not k.upper().startswith(("PG", "SUPABASE"))
        }
        child_env.update(env, PGSSLMODE="require", PGCONNECT_TIMEOUT="20")
        command = [str(args.pg_bin / "pg_dump.exe"), "-Fc", "--role=postgres",
                   f"--snapshot={snapshot}", "--file", str(dump)]  # fmt: skip
        command += [f"--schema={s}" for s in DUMPED_SCHEMAS]
        command += [f"--exclude-table-data={t}" for t in EPHEMERAL]
        # The snapshot lives while this transaction is open: dump concurrently.
        outcome = {}
        worker = threading.Thread(
            target=lambda: outcome.update(
                result=subprocess.run(
                    command,
                    env=child_env,
                    capture_output=True,
                    timeout=600,
                    check=False,
                )
            )
        )
        worker.start()
        schemas = ",".join(f"'{s}'" for s in DUMPED_SCHEMAS)
        tables = [
            r[0] for r in connection.execute(TABLES.format(schemas=schemas)).fetchall()
        ]
        counted = [t for t in tables if t not in EPHEMERAL]
        rows = {}
        for table in counted:
            name, count, digest = connection.execute(fingerprint_sql(table)).fetchone()
            rows[name] = f"{count}:{digest}"
        production_catalog = {
            name: sorted(r[0] for r in connection.execute(sql).fetchall())
            for name, sql in CATALOG.items()
        }
        history = [
            r[0]
            for r in connection.execute(
                "select name from supabase_migrations.schema_migrations order by version"
            ).fetchall()
        ]
        worker.join()
        result = outcome["result"]
        if result.returncode:
            (out / "pg-dump-private-error.log").write_bytes(result.stderr)
            raise SystemExit("pg_dump failed; see the private error log")
        connection.execute("rollback")
    finally:
        connection.close()
    listing = subprocess.run(
        [str(args.pg_bin / "pg_restore.exe"), "--list", str(dump)],
        capture_output=True,
        check=True,
    ).stdout
    dump.with_suffix(".toc.txt").write_bytes(listing)
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    manifest = {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "archive": dump.name,
        "bytes": dump.stat().st_size,
        "sha256": digest,
        "schemas": DUMPED_SCHEMAS,
        "excluded_data": EPHEMERAL,
        "table_data_entries": listing.count(b"TABLE DATA"),
        "tables_fingerprinted": len(rows),
        "migration_history": history,
        "fingerprints": rows,
        "catalog": production_catalog,
    }
    dump.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    return {k: v for k, v in manifest.items() if k not in ("fingerprints", "catalog")}


ROUND_TRIP = [
    "owner-only ACL: explicit {owner}=<all>/{owner} after revokes equals the NULL default pg_restore leaves",
    "CHECK text: an IN list is stored as nested ORs; dump text re-parses flat. Compared without parentheses",
    "USAGE on schema public for PUBLIC is a built-in default pg_dump omits; the restore procedure re-grants it",
]


def equivalent(catalog: dict[str, list[str]]) -> dict[str, list[str]]:
    """Fold only the pg_dump round-trip representations listed in ROUND_TRIP."""

    def fold(line: str) -> str:
        line = re.sub(r" acl=(\w+)=arwdDxtm/\1$", " acl=-", line)
        line = re.sub(r" acl=(\w+)=UC/\1$", " acl=-", line)
        if line.startswith("con "):
            head, _, definition = line.partition(" CHECK ")
            if definition:
                line = head + " CHECK " + re.sub(r"[()\s]", "", definition)
        return line

    return {name: sorted(fold(x) for x in lines) for name, lines in catalog.items()}


def local_fingerprints(pg: SupabaseLikePG, tables: list[str]) -> dict[str, str]:
    result = {}
    for chunk in range(0, len(tables), 30):
        sql = " union all ".join(fingerprint_sql(t) for t in tables[chunk : chunk + 30])
        for line in pg.lines(sql, "supabase_admin"):
            name, count, digest = line.split("|")
            result[name] = f"{count}:{digest}"
    return result


def players_without_dead_box(pg: SupabaseLikePG) -> dict[str, tuple[str, str]]:
    """Each season_players row as (hash without 070's column and updated_at,
    updated_at). The trigger bumps updated_at on the row set to Box 7, so the
    caller proves which rows it moved instead of hashing it."""
    rows = pg.lines(
        "select p.id||'|'||md5((to_jsonb(p)-'dead_box_number'-'updated_at')::text)||'|'||p.updated_at"
        " from public.season_players p order by p.id",
        "supabase_admin",
    )
    return {
        line.split("|")[0]: (line.split("|")[1], line.split("|")[2]) for line in rows
    }


def reads(pg: SupabaseLikePG) -> dict[str, str]:
    """API reads as service_role, each inside a rolled-back transaction."""
    seasons = pg.lines("select id from public.seasons order by id", "supabase_admin")
    trainers = pg.lines("select id from public.trainers order by id", "supabase_admin")
    views = pg.lines(
        "select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace"
        " where n.nspname='public' and c.relkind='v' order by 1",
        "supabase_admin",
    )
    calls = {
        f"view {v}": f"select md5(coalesce(string_agg(t::text,E'\\n' order by t::text),'-'))||':'||count(*) from {v} t"
        for v in views
    }
    # The League read is compared in two parts: the official rows without the
    # live figures 069/070 add (always identical), and the live figures of the
    # active season (070: one total and the participant's dead box).
    added = ("array['provisional_matchday_number','provisional_dead_count','provisional_points_reduction',"
             "'provisional_points','official_points','dead_box_number']")
    live = "array['total_points','dead_count','dead_count_source','dead_count_observed_at']"
    for s in seasons:
        calls[f"league_general_read {s}"] = (
            f"select md5((select jsonb_set(r,'{{rows}}',coalesce((select jsonb_agg(x-{added}-{live}"
            f" order by x->>'season_player_id') from jsonb_array_elements(r->'rows') x),'[]'::jsonb))"
            f" from (select public.league_general_read('{s}') r) q)::text)"
        )
        calls[f"league_live {s}"] = (
            f"select md5((select coalesce(jsonb_agg(jsonb_build_object('p',x->'season_player_id','t',"
            f"coalesce(x->'official_points',x->'total_points'),'d',x->'dead_count') order by x->>'season_player_id'),'[]')"
            f" from jsonb_array_elements(public.league_general_read('{s}')->'rows') x)::text)"
        )
        calls[f"initial_assignment_observations {s}"] = (
            f"select md5(public.initial_assignment_observations('{s}')::text)"
        )
        calls[f"api_resolve_current_matchday {s}"] = (
            f"select md5(public.api_resolve_current_matchday('{s}')::text)"
        )
        for t in trainers:
            calls[f"observed_progress_read {s} {t}"] = (
                f"select md5(public.observed_progress_read('{s}','{t}')::text)"
            )
    result = {}
    for label, sql in calls.items():
        run = pg.sql(
            f"begin; set local role service_role; {sql}; rollback;",
            "postgres",
            ok=False,
        )
        # A business refusal (e.g. no current matchday in a draft) is a result too.
        first = next(
            (x for x in run.err.splitlines() if x.startswith(("ERROR", "psql:"))),
            run.err,
        )
        result[label] = (
            run.out.strip() if not run.returncode else "ERROR " + first[:200]
        )
    return result


def privileges(pg: SupabaseLikePG) -> list[str]:
    """Every privilege anon/authenticated hold on public objects, as text."""
    return sorted(
        pg.lines(
            """select r.rolname||' '||p.privilege_type||' '||c.relname
            from pg_class c join pg_namespace n on n.oid=c.relnamespace
            cross join pg_roles r cross join (values ('SELECT'),('INSERT'),('UPDATE'),('DELETE')) p(privilege_type)
            where n.nspname='public' and c.relkind in ('r','v','m','p') and r.rolname in ('anon','authenticated')
            and has_table_privilege(r.oid,c.oid,p.privilege_type)
            union all
            select r.rolname||' EXECUTE '||f.oid::regprocedure::text from pg_proc f join pg_namespace n on n.oid=f.pronamespace
            cross join pg_roles r where n.nspname='public' and r.rolname in ('anon','authenticated')
            and has_function_privilege(r.oid,f.oid,'EXECUTE')""",
            "supabase_admin",
        )
    )


def rehearse(args) -> dict:
    dump = args.dump
    manifest = json.loads(
        dump.with_suffix(".manifest.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(dump.read_bytes()).hexdigest() == manifest["sha256"], (
        "archive changed"
    )
    report = {"archive": dump.name, "archive_sha256": manifest["sha256"], "checks": []}

    def ok(condition, label, detail=None):
        report["checks"].append(
            {
                "check": label,
                "pass": bool(condition),
                **({"detail": detail} if detail else {}),
            }
        )
        print("PASS" if condition else "FAIL", label, flush=True)
        if not condition:
            if args.output:
                args.output.write_text(
                    json.dumps(report, indent=2, default=str), encoding="utf-8"
                )
            raise SystemExit(f"FAIL {label}")

    pg = SupabaseLikePG(args.pg_bin, args.port, args.dir)
    try:
        pg.start(storage_mock=False)
        # Roles are cluster-wide, outside the archive: the ones production's
        # grants name since 056, created as 056 creates them (no login here).
        pg.sql(
            "create role pokeapp_item_verifier nologin nosuperuser nocreatedb nocreaterole noinherit nobypassrls;",
            "supabase_admin",
        )
        # The archive recreates public with production's owner, ACL and defaults.
        pg.sql("drop schema public cascade;", "supabase_admin")
        restore = pg.run(
            "pg_restore",
            ["-h", "127.0.0.1", "-p", str(pg.port), "-U", "supabase_admin", "-d", pg.database,
             "--exit-on-error", str(dump)],
            ok=False,
        )  # fmt: skip
        ok(not restore.returncode, "backup restores into an isolated cluster with owners and grants",
           restore.stderr.decode("utf-8", "replace")[-1500:] if restore.returncode else None)  # fmt: skip
        pg.sql(
            "grant usage on schema public to public;", "supabase_admin"
        )  # ROUND_TRIP[2]
        tables = sorted(manifest["fingerprints"])
        restored = local_fingerprints(pg, tables)
        different = [
            t for t in tables if restored.get(t) != manifest["fingerprints"][t]
        ]
        ok(
            not different,
            f"restored rows identical to production: {len(tables)} tables (count + hash)",
            different,
        )
        catalog = catalog_local(pg)
        diff = compare(equivalent(manifest["catalog"]), equivalent(catalog))
        report["round_trip_equivalences"] = ROUND_TRIP
        drift = {
            k: v
            for k, v in diff.items()
            if v["only_production"] or v["only_repository"]
        }
        ok(
            not drift,
            "restored catalog identical to production (objects, definitions, owners, ACLs)",
            drift,
        )
        history = pg.lines(
            "select name from supabase_migrations.schema_migrations order by version",
            "supabase_admin",
        )
        ok(history == manifest["migration_history"] and not any(m.stem in history for m in PENDING),
           f"migration history restored: {WINDOW} not recorded")  # fmt: skip

        reads_before, privileges_before = reads(pg), privileges(pg)
        broken = {
            k: v
            for k, v in reads_before.items()
            if v.startswith("ERROR")
            and ("permission denied" in v or "does not exist" in v)
        }
        report["reads_refused_by_rule"] = {
            k: v for k, v in reads_before.items() if v.startswith("ERROR")
        }
        ok(
            not broken,
            f"{len(reads_before)} API reads run on the restored copy (no privilege or missing-object error)",
            broken,
        )
        public_tables = [
            t for t in tables if t.startswith(("public.", "v1_shadow.", "storage."))
        ]
        rows_before = local_fingerprints(pg, public_tables)
        players_before = players_without_dead_box(pg)

        report["applied"] = {}
        # Production's supautils.policy_grants lets postgres manage policies on
        # storage.objects (read from pg_settings). Vanilla PostgreSQL has no
        # supautils: emulate exactly that, only while the migration with a
        # storage policy runs, then take it back.
        storage_policy = "create policy item_artifacts_no_browser on storage.objects"
        report["supautils_emulation"] = (
            "postgres temporarily member of supabase_storage_admin while 056 runs"
        )
        for migration in PENDING:
            text = migration.read_text(encoding="utf-8")
            emulate = storage_policy in text
            if emulate:
                pg.sql("grant supabase_storage_admin to postgres;", "supabase_admin")
            run = pg.sql(text, "postgres", ok=False)
            if emulate:
                pg.sql("revoke supabase_storage_admin from postgres;", "supabase_admin")
            report["applied"][migration.name] = (
                "applied" if not run.returncode else run.err[-600:]
            )
            ok(
                not run.returncode,
                f"{migration.name} applies once as non-superuser postgres",
            )
            pg.sql(
                "insert into supabase_migrations.schema_migrations(version,name,statements) "
                f"values ('{datetime.now(UTC):%Y%m%d%H%M%S}{migration.name[:3]}','{migration.stem}','{{}}');",
                "supabase_admin",
            )

        rows_after = local_fingerprints(pg, public_tables)
        # 070 adds season_players.dead_box_number (default 8) and sets Box 7 for
        # one participation (Anto, active season). Every other row of every
        # table stays byte-identical; season_players is compared without the
        # new column.
        changed = [t for t in public_tables if rows_before[t] != rows_after[t]]
        ok(
            not [t for t in changed if t != "public.season_players"],
            f"{len(public_tables) - 1} existing tables keep byte-identical rows (seasons, saves, history, purchases, coins)",
            changed,
        )
        players_after = players_without_dead_box(pg)
        moved = sorted(k for k in players_before if players_before[k][1] != players_after.get(k, ("", ""))[1])
        boxed = sorted(pg.lines("select id from public.season_players where dead_box_number<>8", "supabase_admin"))
        ok(
            players_before.keys() == players_after.keys()
            and all(players_before[k][0] == players_after[k][0] for k in players_before)
            and moved == boxed,
            "season_players rows identical apart from the new dead box column (updated_at only on the row set)",
            {"updated_at_moved": moved, "dead_box_not_8": boxed},
        )
        boxes = pg.lines(
            "select s.name||'|'||s.status||'|'||t.display_name||'|'||p.dead_box_number from public.season_players p"
            " join public.seasons s on s.id=p.season_id join public.trainers t on t.id=p.trainer_id"
            " where p.dead_box_number<>8 order by 1",
            "supabase_admin",
        )
        report["dead_boxes_not_8"] = boxes
        ok(
            len(boxes) <= 1 and all(b.split("|")[1] == "active" and b.split("|")[2].lower() == "anto"
                                    and b.endswith("|7") for b in boxes),
            "Box 7 only for Anto's participation in the active season; everyone else keeps Box 8",
            boxes,
        )  # fmt: skip
        reads_after = reads(pg)
        active = set(pg.lines("select id from public.seasons where status='active'", "supabase_admin"))
        moved = {
            k: [reads_before[k], reads_after.get(k)]
            for k in reads_before
            if reads_before[k] != reads_after.get(k)
        }
        # The active season's League (one live total, its dead boxes) and its
        # initial-assignment inputs may move; so may public_season_players, an
        # explicit projection (without the new column) that shows updated_at,
        # already proven above to move only on the row set to Box 7.
        unexplained = {
            k: v for k, v in moved.items()
            if not (k.split(" ")[0] in ("league_live", "initial_assignment_observations")
                    and k.split(" ")[-1] in active)
            and not (k == "view public.public_season_players" and boxed)
        }  # fmt: skip
        report["reads_moved_in_active_season"] = sorted(set(moved) - set(unexplained))
        report["league_live"] = pg.lines(
            "select s.name||'|'||(r->>'display_name')||'|official='||(r->>'official_points')||'|total='||(r->>'total_points')"
            "||'|dead_box='||(r->>'dead_box_number')||'|dead='||coalesce(r->>'dead_count','unknown')"
            "||'|provisional='||(r ? 'provisional_points')::text"
            " from public.seasons s cross join lateral jsonb_array_elements(public.league_general_read(s.id)->'rows') r"
            " where s.status='active' order by 1",
            "supabase_admin",
        )
        ok(
            all(line.endswith("|provisional=false") for line in report["league_live"]),
            "active League rows show one total (no provisional line) and each dead box",
            report["league_live"],
        )
        ok(
            not unexplained,
            f"{len(reads_before)} API reads return identical results after {WINDOW} (active-season League aside)",
            unexplained,
        )
        privileges_after = privileges(pg)
        lost = sorted(set(privileges_before) - set(privileges_after))
        gained = sorted(set(privileges_after) - set(privileges_before))
        ok(not lost, "no browser privilege removed from existing objects", lost)
        ok(
            not gained,
            "no new privilege for anon/authenticated (tables, views or functions)",
            gained,
        )
        new_tables = pg.lines(
            """select c.relname||' rls='||c.relrowsecurity||' force='||c.relforcerowsecurity
            from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'
            and c.relname in ('item_use_authorizations','item_use_verifications','item_use_artifacts','item_use_transfers',
            'item_use_transfer_legs','transfer_provenance','transfer_commit_permits','admin_incident_commands','discord_announcements') order by 1""",
            "supabase_admin",
        )
        ok(len(new_tables) == 9 and all(t.endswith("rls=true force=true") for t in new_tables),
           "9 private operational tables exist and force RLS", new_tables)  # fmt: skip
        verifier = pg.lines(
            "select rolcanlogin::text||rolsuper::text||rolbypassrls::text from pg_roles where rolname='pokeapp_item_verifier'",
            "supabase_admin",
        )
        ok(
            verifier == ["falsefalsefalse"],
            "verifier role created without login, superuser or RLS bypass",
        )
        from tools.validate_phase070_pg import validate
        report["phase070"] = validate(pg)
        ok(local_fingerprints(pg, public_tables) == rows_after, "focused fixtures rolled back exactly")
        upgraded = catalog_local(pg)
    finally:
        pg.stop(remove=True)

    fresh = SupabaseLikePG(args.pg_bin, args.port + 1, args.dir)
    try:
        fresh.start(storage_mock=True)
        for migration in MIGRATIONS:
            fresh.sql(migration.read_text(encoding="utf-8"))
        bootstrap = catalog_local(fresh)
    finally:
        fresh.stop(remove=True)
    diff = compare(equivalent(upgraded), equivalent(bootstrap))
    drift = {
        k: v for k, v in diff.items() if v["only_production"] or v["only_repository"]
    }
    # Storage policies come from the real storage schema on one side and the
    # policy-only mock on the other; compare our policies, not the platform's.
    ok(
        not drift,
        f"upgraded copy equals a fresh 001-{MIGRATIONS[-1].name[:3]} build (Supabase-shaped)",
        drift,
    )
    report["result"] = "PASS"
    report["deployed_before"] = len(DEPLOYED)
    report["pending"] = [m.name for m in PENDING]
    report["pending_sha256"] = {
        m.name: hashlib.sha256(m.read_bytes()).hexdigest() for m in PENDING
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["capture", "rehearse"])
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument(
        "--dir", type=Path, required=True, help="owner-only private folder"
    )
    parser.add_argument("--dump", type=Path)
    parser.add_argument("--port", type=int, default=55540)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = capture(args) if args.command == "capture" else rehearse(args)
    text = json.dumps(report, indent=2, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text[:3000])


if __name__ == "__main__":
    main()
