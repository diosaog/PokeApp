"""078 on a disposable PostgreSQL: public Pokepast.es columns of the outbox.

Applies every migration up to 078 and checks, on synthetic rows that are
always rolled back: the service role can record a paste for a team_locked
announcement; invalid URLs, links for other kinds, links ahead of the
announcement revision or half-recorded links are refused; a replaced lock
(the 067 trigger) raises the revision, so the stored link stops matching.
No remote connections, real saves or Team Lock writes.

    python -m tools.validate_phase078_public_pastes --port <free port>
"""

from pathlib import Path
from uuid import uuid4
import argparse
import os

import psycopg


class _Rollback(Exception):
    pass


def refused(conn, sql, args=()):
    try:
        with conn.transaction():
            conn.execute(sql, args)
    except psycopg.errors.CheckViolation:
        return True
    raise AssertionError(f"accepted: {sql}")


def validate(pg):
    checks = []
    with psycopg.connect(host="127.0.0.1", port=pg.port, user="supabase_admin", dbname=pg.database) as conn:
        try:
            columns = {
                r[0]
                for r in conn.execute(
                    "select column_name from information_schema.columns"
                    " where table_schema='public' and table_name='discord_announcements'"
                )
            }
            assert {
                "public_paste_url", "public_paste_revision", "public_paste_attempt_revision",
                "public_paste_attempts", "public_paste_error",
            } <= columns, columns
            lock, other = str(uuid4()), str(uuid4())
            conn.execute(
                "insert into public.discord_announcements(id,event_key,kind,subject)"
                " values(%s,%s,'team_locked',jsonb_build_object('lock_id',%s::text)),"
                " (%s,%s,'season_started','{}'::jsonb)",
                (lock, f"team_locked:{lock}", lock, other, f"season:{other}"),
            )
            conn.execute("set local role service_role")
            conn.execute(
                "update public.discord_announcements set public_paste_url=%s,"
                " public_paste_revision=1, public_paste_error=null where id=%s",
                ("https://pokepast.es/0123456789abcdef", lock),
            )
            conn.execute(
                "update public.discord_announcements set public_paste_attempt_revision=1,"
                " public_paste_attempts=2, public_paste_error='pokepaste_http_503' where id=%s",
                (lock,),
            )
            checks.append("service_role records link and bounded attempts")
            for sql, args in (
                ("update public.discord_announcements set public_paste_url=%s where id=%s",
                 ("https://evil.example/0123456789abcdef", lock)),
                ("update public.discord_announcements set public_paste_url=%s where id=%s",
                 ("https://pokepast.es/0123456789ABCDEF", lock)),
                ("update public.discord_announcements set public_paste_revision=2 where id=%s", (lock,)),
                ("update public.discord_announcements set public_paste_url=null where id=%s", (lock,)),
                ("update public.discord_announcements set public_paste_attempts=11 where id=%s", (lock,)),
                ("update public.discord_announcements set public_paste_error='Bad Code' where id=%s", (lock,)),
                ("update public.discord_announcements set public_paste_url=%s, public_paste_revision=1 where id=%s",
                 ("https://pokepast.es/0123456789abcdef", other)),
                ("update public.discord_announcements set public_paste_attempts=1 where id=%s", (other,)),
            ):
                refused(conn, sql, args)
            checks.append("8 invalid states refused (url host/case, ahead, half, bounds, code, other kinds)")
            for role in ("anon", "authenticated"):
                try:
                    with conn.transaction():
                        conn.execute(f"set local role {role}")
                        conn.execute("select public_paste_url from public.discord_announcements")
                    raise AssertionError(f"{role} can read the outbox")
                except psycopg.errors.InsufficientPrivilege:
                    pass
            checks.append("anon/authenticated cannot read the outbox")
            conn.execute("reset role")
            conn.execute(
                "update public.discord_announcements set revision=revision+1 where id=%s", (lock,)
            )
            stale = conn.execute(
                "select public_paste_revision < revision from public.discord_announcements where id=%s",
                (lock,),
            ).fetchone()[0]
            assert stale is True
            checks.append("a newer revision leaves the old link stale (never reused)")
        finally:
            conn.rollback()
    return "PASS: " + "; ".join(checks)


def main():
    from tools.phase30_release_audit import SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pg-bin", type=Path,
        default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin",
    )
    parser.add_argument("--port", type=int, default=55612)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in sorted(
            (Path(__file__).resolve().parents[1] / "supabase/v2/migrations").glob("*.sql")
        ):
            if int(migration.name[:3]) <= 78:
                pg.sql(migration.read_text(encoding="utf-8"))
        print(validate(pg))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
