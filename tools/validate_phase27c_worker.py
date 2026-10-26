"""27C runner startup/security smoke; disposable PG and fictional settings only.

Existing27A jobs/retry/settlement evidence is retained; this tests CLI wiring,
the default-off boundary and the actual restricted database connection.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import psycopg

from app.repositories.item_verifier_pg import ItemVerifierPG
from tools.run_item_use_verifier import transfer_once, verify_one
from tools.validate_accounts_local import LocalPG

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = {"checks": [], "status": "RUNNING"}

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

    clean = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith(("POKEAPP", "SUPABASE", "PG"))
    }
    pg = LocalPG(args.pg_bin, 55493)
    started = False
    try:
        for label, settings, expected in (
            ("CLI disabled without credentials", {}, (0, "DISABLED")),
            (
                "transfer flag alone cannot enable runner",
                {"POKEAPP_TRANSFER_VERIFIER_ENABLED": "true"},
                (0, "DISABLED"),
            ),
            (
                "missing configuration fails closed and redacted",
                {"POKEAPP_ITEM_VERIFIER_ENABLED": "true"},
                (1, "VERIFIER_UNAVAILABLE"),
            ),
            (
                "insecure DSN refused before connection, no secret echo",
                {
                    "POKEAPP_ITEM_VERIFIER_ENABLED": "true",
                    "POKEAPP_ITEM_VERIFIER_DATABASE_URL": "host=never-connect.invalid password=fictional-secret sslmode=require",
                },
                (1, "VERIFIER_UNAVAILABLE"),
            ),
        ):
            result = subprocess.run(
                [sys.executable, "-m", "tools.run_item_use_verifier"],
                cwd=ROOT,
                env={**clean, **settings},
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
            assert (result.returncode, result.stdout.strip()) == expected, label
            assert not result.stderr, label
            passed(label)

        pg.start()
        started = True
        pg.sql("""create role phase27c_worker login nosuperuser nocreatedb
          nocreaterole nobypassrls; grant pokeapp_item_verifier to phase27c_worker;""")
        with psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            user="phase27c_worker",
            dbname="pokeapp_v2_validation_accounts",
            autocommit=True,
        ) as conn:
            reader, parser, native, storage = Mock(), Mock(), Mock(), Mock()
            for _ in range(2):
                assert (
                    verify_one(ItemVerifierPG(conn), reader, parser, native) == "IDLE"
                )
                assert transfer_once(conn, storage, reader, parser, native) == []
            for unused in (reader, parser, native, storage):
                assert not unused.mock_calls
            passed(
                "real restricted connection: item and transfer runner idle/replay, no artifact access"
            )
            executable = conn.execute("""select proname from pg_proc p
              join pg_namespace n on n.oid=p.pronamespace
              where n.nspname='public' and p.prosecdef
              and p.prorettype<>'trigger'::regtype
              and has_function_privilege(current_user,p.oid,'EXECUTE') order by 1""").fetchall()
            assert executable == [("item_verifier_job",), ("transfer_verifier",)]
            passed("restricted security-definer RPC allowlist is exactly two functions")
            for query in (
                "select * from public.item_use_verifications",
                "delete from public.item_use_transfer_legs where false",
                "select public.transfer_leg_view(null::uuid,'source')",
            ):
                try:
                    conn.execute(query)
                except psycopg.errors.InsufficientPrivilege:
                    continue
                raise AssertionError(
                    "restricted worker unexpectedly allowed direct access"
                )
            passed("direct table reads/DML and internal projection denied")
        with psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            user="postgres",
            dbname="pokeapp_v2_validation_accounts",
            autocommit=True,
        ) as conn:
            try:
                ItemVerifierPG(conn)
            except ValueError:
                pass
            else:
                raise AssertionError("superuser accepted as verifier")
        passed("privileged database identity refused by runner adapter")
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error_type"] = type(error).__name__
        raise
    finally:
        if started:
            pg.stop()
            report["cleanup"] = "Owned database dropped; cluster stopped"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
