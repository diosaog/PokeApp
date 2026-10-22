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
        self.sql("""create schema storage;
        create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
        create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,owner uuid);
        alter table storage.objects enable row level security;
        grant usage on schema storage to authenticated,service_role;
        grant all on storage.objects,storage.buckets to service_role;
        grant select,insert,update,delete on storage.objects to authenticated;
        """)
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


def p2(pg):
    tid = str(uuid4())
    rival = str(uuid4())
    auth = str(uuid4())
    season = str(uuid4())
    pg.sql(f"""insert into trainers(id,display_name,slug,auth_user_id,is_admin) values
    ('{tid}','Profile Owner','profile-owner','{auth}',true),('{rival}','Rival','rival',gen_random_uuid(),false);
    insert into seasons(id,name,created_by_trainer_id) values('{season}','Preserved','{tid}');
    insert into season_players(season_id,trainer_id) values('{season}','{tid}');""")
    baseline = pg.sql(
        "select md5(string_agg(row_to_json(t)::text,'' order by id)) from season_players t;"
    ).stdout
    op = str(uuid4())
    digest = "b" * 64
    rename = f"select account_profile_update('{tid}','{op}','{digest}',0,'New Name','new-name',null);"
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda _: pg.sql(rename).stdout, range(4)))
    assert all(r == rows[0] for r in rows)
    assert (
        pg.sql(
            f"select profile_revision from trainers where id='{tid}';"
        ).stdout.strip()
        == "1"
    )
    assert pg.sql(
        f"select account_profile_update('{tid}','{uuid4()}','{digest}',0,'Stale','stale',null);",
        ok=False,
    ).returncode
    assert pg.sql(
        f"select account_profile_update('{tid}','{uuid4()}','{digest}',1,'Rival','rival',null);",
        ok=False,
    ).returncode
    assert pg.sql(
        f"select account_profile_update('{tid}','{uuid4()}','{digest}',1,null,null,'portraits/{rival}/{'c' * 64}.jpg');",
        ok=False,
    ).returncode
    assert (
        pg.sql(
            "select md5(string_agg(row_to_json(t)::text,'' order by id)) from season_players t;"
        ).stdout
        == baseline
    )
    pg.sql(f"update trainers set display_name='Alias Display' where id='{rival}';")
    collision = pg.sql(
        f"select account_registration_reserve('{uuid4()}','{digest}','Alias Display','alias-display');",
        ok=False,
    )
    assert collision.returncode and "account_conflict" in collision.stderr
    pinop = str(uuid4())
    pg.sql(f"select account_pin_begin('{tid}','{tid}','{pinop}','{digest}');")
    assert (
        pg.sql(f"select account_session_allowed('{auth}',9999999999);").stdout.strip()
        == "f"
    )
    with ThreadPoolExecutor(4) as pool:
        claims = list(
            pool.map(
                lambda _: pg.sql(
                    f"select account_pin_claim('{pinop}','{digest}');"
                ).stdout.strip(),
                range(4),
            )
        )
    assert claims.count("t") == 1 and claims.count("f") == 3
    assert pg.sql(
        f"select account_pin_begin('{tid}','{tid}','{uuid4()}','{digest}');", ok=False
    ).returncode
    pg.sql(f"select account_pin_finish('{pinop}','{digest}');")
    assert (
        pg.sql(
            f"select account_session_allowed('{auth}',1),account_session_allowed('{auth}',9999999999);"
        ).stdout.strip()
        == "f|t"
    )
    for iat, expected in ((1, ""), (9999999999, tid)):
        value = pg.sql(
            f"set role authenticated; set request.jwt.claim.sub='{auth}'; set request.jwt.claims='{{\"iat\":{iat}}}'; select current_trainer_id();"
        ).stdout.strip()
        assert value == expected, (value, expected)
    assert pg.sql(
        f"select account_pin_begin('{rival}','{tid}','{uuid4()}','{digest}');", ok=False
    ).returncode
    for role in ("anon", "authenticated"):
        assert pg.sql(f"set role {role};" + rename, ok=False).returncode
        assert pg.sql(
            f"set role {role}; select * from account_pin_changes;", ok=False
        ).returncode
    # Prove restrictive photo policies defeat even an accidental broad policy.
    pg.sql(
        "create policy broad_test on storage.objects for all to authenticated using(true) with check(true);"
    )
    assert pg.sql(
        "set role authenticated; insert into storage.objects(bucket_id,name) values('trainer-photos','attack.jpg');",
        ok=False,
    ).returncode
    pg.sql(
        "insert into storage.objects(bucket_id,name) values('trainer-photos','retained.jpg');"
    )
    pg.sql(
        "set role authenticated; update storage.objects set name='attack.jpg'; delete from storage.objects;"
    )
    assert pg.sql("select name from storage.objects;").stdout.strip() == "retained.jpg"
    return {
        "concurrent_profile": 4,
        "pin_claims": 4,
        "single_update_authority": True,
        "identity_history_preserved": True,
        "stale_duplicate_foreign_photo_denied": True,
        "old_session_api_rls_denied": True,
        "storage_write_denial": True,
    }


def p3(pg):
    actor, target, season = (str(uuid4()) for _ in range(3))
    op = str(uuid4())
    digest = "d" * 64
    pg.sql(f"""insert into trainers(id,display_name,slug,auth_user_id,is_admin) values
    ('{actor}','Admin','admin',gen_random_uuid(),true),('{target}','Player','player',gen_random_uuid(),false);
    insert into seasons(id,name,created_by_trainer_id) values('{season}','Draft','{actor}');
    insert into season_admin_state(season_id) values('{season}');""")
    add = json.dumps(
        dict(
            actor_trainer_id=actor,
            season_id=season,
            idempotency_key=str(uuid4()),
            body=dict(trainer_id=target, expected_roster_revision=0),
        )
    )
    pg.sql(f"select api_admin_add_participant('{add}'::jsonb);")
    baseline = pg.sql(
        "select md5(string_agg(row_to_json(t)::text,'' order by id)) from season_players t;"
    ).stdout
    request = (
        f"select account_admin_status('{actor}','{target}','{op}','{digest}',0,false);"
    )
    with ThreadPoolExecutor(4) as pool:
        receipts = list(pool.map(lambda _: pg.sql(request).stdout, range(4)))
    assert all(r == receipts[0] for r in receipts)
    assert (
        pg.sql(
            f"select globally_enabled,is_admin,profile_revision from trainers where id='{target}';"
        ).stdout.strip()
        == "f|f|1"
    )
    assert (
        pg.sql(
            "select md5(string_agg(row_to_json(t)::text,'' order by id)) from season_players t;"
        ).stdout
        == baseline
    )
    assert pg.sql(
        f"select account_admin_status('{actor}','{actor}','{uuid4()}','{digest}',0,false);",
        ok=False,
    ).returncode
    assert pg.sql(
        f"select account_admin_status('{actor}','{target}','{uuid4()}','{digest}',0,true);",
        ok=False,
    ).returncode
    pg.sql(
        f"select account_admin_status('{actor}','{target}','{uuid4()}','{digest}',1,true);"
    )
    assert pg.sql(f"select account_admin_list('{target}',0);", ok=False).returncode
    assert pg.sql(
        f"select account_admin_status('{target}','{actor}','{uuid4()}','{digest}',0,false);",
        ok=False,
    ).returncode
    data = json.loads(pg.sql(f"select account_admin_list('{actor}',0);").stdout)
    assert {actor, target} <= {t["trainer_id"] for t in data["items"]} and all(
        "auth_user_id" not in t for t in data["items"]
    )
    pg.sql(f"update seasons set status='active',started_at=now() where id='{season}';")
    add = json.dumps(
        dict(
            actor_trainer_id=actor,
            season_id=season,
            idempotency_key=str(uuid4()),
            body=dict(trainer_id=actor, expected_roster_revision=1),
        )
    )
    denied = pg.sql(f"select api_admin_add_participant('{add}'::jsonb);", ok=False)
    assert denied.returncode and "season_not_draft" in denied.stderr
    assert pg.sql("select count(*) from coin_transactions;").stdout.strip() == "0"
    pin = str(uuid4())
    pg.sql(f"select account_pin_begin('{actor}','{target}','{pin}','{digest}');")
    assert pg.sql(
        f"select account_admin_status('{actor}','{target}','{uuid4()}','{digest}',2,true);",
        ok=False,
    ).returncode
    for role in ("anon", "authenticated"):
        assert pg.sql(f"set role {role};" + request, ok=False).returncode
    return dict(
        concurrent_status=4,
        stable_identity_membership=True,
        self_disable_denied=True,
        nonadmin_denied=True,
        stale_denied=True,
        late_enrollment_denied=True,
        no_rewards=True,
        pending_pin_no_bypass=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55479)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--packet", choices=["p1", "p2", "p3"], default="p1")
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    started = False
    try:
        pg.start()
        started = True
        result = {
            "status": "PASS",
            args.packet: {"p1": p1, "p2": p2, "p3": p3}[args.packet](pg),
            "cluster": str(pg.root),
        }
    finally:
        if started:
            pg.stop()
    result["cleanup"] = "database dropped; cluster stopped; logs retained"
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
