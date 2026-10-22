"""Disposable loopback PostgreSQL account gates. No remote configuration is loaded."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class LocalPG:
    def __init__(self, binary: Path, port: int):
        self.binary, self.port = binary, port
        self.root = Path(tempfile.mkdtemp(prefix="pokeapp-accounts-pg-"))
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.upper().startswith(("PG", "SUPABASE", "POKEAPP_V2_SUPABASE"))
        }

    def command(self, name, args, content=None, ok=True):
        if name == "pg_ctl":
            # The server inherits console pipes on Windows. Never capture those
            # through communicate(): they remain open for the server lifetime.
            with (self.root / "pg_ctl.log").open("a", encoding="utf-8") as output:
                result = subprocess.run(
                    [str(self.binary / (name + ".exe")), *args],
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=output,
                    env=self.env,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=False,
                    timeout=60,
                )
            if result.returncode:
                raise RuntimeError("pg_ctl failed; inspect retained pg_ctl.log")
            return result
        result = subprocess.run(
            [str(self.binary / (name + ".exe")), *args],
            input=content,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=self.env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if ok and result.returncode:
            raise RuntimeError(f"{name} failed: {result.stderr[-2000:]}")
        return result

    def sql(self, value, database="pokeapp_v2_validation_accounts", ok=True):
        return self.command(
            "psql",
            [
                "-h",
                "127.0.0.1",
                "-p",
                str(self.port),
                "-U",
                "postgres",
                "-d",
                database,
                "-X",
                "-qAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                "-",
            ],
            value,
            ok,
        )

    def start(self):
        self.command(
            "initdb",
            [
                "-D",
                str(self.root / "data"),
                "-U",
                "postgres",
                "--auth=trust",
                "--encoding=UTF8",
                "--locale=C",
            ],
        )
        self.command(
            "pg_ctl",
            [
                "-D",
                str(self.root / "data"),
                "-l",
                str(self.root / "server.log"),
                "-o",
                f"-h 127.0.0.1 -p {self.port}",
                "-w",
                "start",
            ],
        )
        self.sql("create database pokeapp_v2_validation_accounts;", "postgres")
        self.sql(
            "create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;"
        )
        self.sql((ROOT / "supabase/v2/bootstrap.sql").read_text(encoding="utf-8"))

    def stop(self):
        self.sql("drop database if exists pokeapp_v2_validation_accounts;", "postgres")
        self.command("pg_ctl", ["-D", str(self.root / "data"), "-w", "stop"])


def p1(pg):
    op = str(uuid4())
    digest = "a" * 64
    reserve = f"select public.account_registration_reserve('{op}','{digest}','New Trainer','new-trainer');"
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda _: json.loads(pg.sql(reserve).stdout), range(4)))
    assert all(r == rows[0] for r in rows)
    row = rows[0]
    tid = row["trainer_id"]
    aid = row["auth_user_id"]
    assert (
        pg.sql(
            f"select globally_enabled or is_admin or auth_user_id is not null from trainers where id='{tid}';"
        ).stdout.strip()
        == "f"
    )
    assert pg.sql("select count(*) from season_players;").stdout.strip() == "0"
    duplicate = pg.sql(
        f"select public.account_registration_reserve('{uuid4()}','{digest}','NEW TRAINER','new-trainer');",
        ok=False,
    )
    assert duplicate.returncode and "account_conflict" in duplicate.stderr
    assert pg.sql(
        f"select public.account_registration_reserve('{op}','{'b' * 64}','New Trainer','new-trainer');",
        ok=False,
    ).returncode
    complete = (
        f"select public.account_registration_complete('{op}','{digest}','{aid}');"
    )
    # Explicit transaction rollback after both writes leaves no partial enablement.
    pg.sql("begin;" + complete + "rollback;")
    assert (
        pg.sql(
            f"select globally_enabled from trainers where id='{tid}';"
        ).stdout.strip()
        == "f"
    )
    with ThreadPoolExecutor(4) as pool:
        result = list(pool.map(lambda _: pg.sql(complete).stdout.strip(), range(4)))
    assert result == [tid] * 4
    pg.sql(f"update trainers set globally_enabled=false where id='{tid}';")
    pg.sql(complete)
    assert (
        pg.sql(
            f"select globally_enabled from trainers where id='{tid}';"
        ).stdout.strip()
        == "f"
    )
    for role in ("anon", "authenticated"):
        for query in (
            reserve,
            complete,
            "select * from account_registrations;",
            "update trainers set is_admin=true;",
            "update public_trainers set display_name='Intruder';",
        ):
            denied = pg.sql(f"set role {role};" + query, ok=False)
            assert denied.returncode and "permission denied" in denied.stderr, (
                denied.stderr
            )
    key = hashlib.sha256(b"rate-test").hexdigest()
    with ThreadPoolExecutor(8) as pool:
        results = list(
            pool.map(
                lambda _: pg.sql(
                    f"select account_rate_check('{key}',3,300);"
                ).stdout.strip(),
                range(8),
            )
        )
    assert results.count("t") == 3 and results.count("f") == 5
    assert pg.sql("select count(*) from season_players;").stdout.strip() == "0"
    assert pg.sql("select count(*) from coin_transactions;").stdout.strip() == "0"
    return {
        "concurrent_reservation": 4,
        "concurrent_complete": 4,
        "rate_attempts": 8,
        "denials": 10,
        "rollback": True,
        "disabled_replay": True,
        "season_and_economy_rows": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55479)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    started = False
    try:
        pg.start()
        started = True
        result = {"status": "PASS", "p1": p1(pg), "cluster": str(pg.root)}
    finally:
        if started:
            pg.stop()
    result["cleanup"] = "database dropped; cluster stopped; logs retained"
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
