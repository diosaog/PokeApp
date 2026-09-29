"""Focused GENERAL checks against an already-built disposable LOCAL PostgreSQL."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from tools.validate_supabase_v2_schema import _psql_text, _safe_database_name

ROOT = Path(__file__).resolve().parents[1]


def validate(args):
    _safe_database_name(args.database)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Local PostgreSQL only; no staging fixtures")
    command = [
        args.psql,
        "-X",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.user,
        "-d",
        args.database,
        "-qAt",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    env = dict(os.environ, PGPASSWORD=args.password)

    def sql(text):
        return subprocess.run(
            command,
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=True,
        ).stdout.strip()

    def baseline():
        tables = sql(
            "select tablename from pg_tables where schemaname='public' order by tablename;"
        ).splitlines()
        return {
            name: sql(
                "select count(*)::text||':'||md5(coalesce(string_agg(row_to_json(t)::text,'' order by row_to_json(t)::text),'')) from public.\""
                + name
                + '" t;'
            )
            for name in tables
        }

    before = baseline()
    _psql_text(
        args, (ROOT / "tests/sql/league_general_checks.sql").read_text(encoding="utf-8")
    )
    # Two separate sessions: uncommitted change cannot leak half a wallet/roster update.
    sid, tid, pid = [str(uuid4()) for _ in range(3)]
    sql(
        f"insert into public.trainers(id,display_name,slug) values('{tid}','MVCC before','phase10_5b_{tid.replace('-', '')}');"
        f"insert into public.seasons(id,name) values('{sid}','phase10_5b_mvcc');"
        f"insert into public.season_players(id,season_id,trainer_id) values('{pid}','{sid}','{tid}');"
    )
    writer = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        writer.stdin.write(
            f"begin; update public.trainers set display_name='MVCC after' where id='{tid}';\n"
            f"insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type) values('{sid}','{tid}','{pid}',17,'admin_adjustment');\n"
            "select 'WRITER_READY';\n"
        )
        writer.stdin.flush()
        assert writer.stdout.readline().strip() == "WRITER_READY", (
            "writer failed before concurrent read"
        )

        def read():
            return json.loads(
                sql(
                    f"set role service_role; select public.league_general_read('{sid}');"
                )
            )["rows"][0]

        row = read()
        assert (row["display_name"], row["coin_balance"]) == ("MVCC before", "0")
        writer.stdin.write("commit;\n\\q\n")
        writer.stdin.flush()
        writer.wait(timeout=10)
        assert writer.returncode == 0, writer.stderr.read()
        row = read()
        assert (row["display_name"], row["coin_balance"]) == ("MVCC after", "17")
        print("PASS separate-session read isolation before/after commit")
    finally:
        if writer.poll() is None:
            writer.terminate()
            writer.wait(timeout=10)
        # Local disposable fixture only; never targets owner/staging records.
        sql(
            f"delete from public.coin_transactions where season_id='{sid}';"
            f"delete from public.season_players where season_id='{sid}';"
            f"delete from public.seasons where id='{sid}';delete from public.trainers where id='{tid}';"
        )
    assert baseline() == before, "public table drift after fixtures"
    print(
        f"PASS exact baseline restoration: {len(before)} public tables; GENERAL local SQL complete"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--database", default="pokeapp_v2_validation_phase10_5b")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    validate(p.parse_args())
