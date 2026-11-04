"""Focused 083 acceptance (one announcement per «Fijar Equipo»); always rolls back.

Disposable loopback PostgreSQL only: no production transport, Team Lock,
Pokepast.es or Discord request. Checks, on the real RPCs and triggers:

* a first confirmation records one immutable confirmation and one outbox row;
  an automatic retry with the same Idempotency-Key replays without either;
* a different team and the same team again (new keys) are two more records
  and two more rows; the earlier row (sent, with its message ID) and the
  earlier snapshot are untouched; every row keeps its own trainer and matchday;
* reusing a key for another request is refused; confirmations are immutable;
* the legacy 10-argument call still queues its first-lock row but a
  replacement no longer edits it; a closed matchday still refuses a lock;
* browser roles reach neither the new table nor the new RPC.

    python -m tools.validate_phase083_team_lock_announcements --port <free port>
"""

from psycopg.types.json import Jsonb

from tools.validate_phase079_all_vs_all import (
    as_owner,
    connect,
    initialize,
    observe,
    prepare,
    value,
)
from tools.validate_phase080_enrollment import close_day, open_day, results
from tools.validate_player_matchdays import rejected


def validate(pg):
    checks = []

    def ok(condition, label):
        assert condition, label
        checks.append(label)

    with connect(pg) as conn:
        try:
            v = initialize(conn)
            for index in range(5):
                observe(conn, v, index, [], 2)
            day = prepare(conn, v, v["trainers"][0])["matchday_id"]

            def source(index):
                return conn.execute(
                    "select f.id,f.sha256,ps.id,ps.payload from public.season_players sp join public.save_files f"
                    " on f.id=sp.current_save_file_id join public.parsed_saves ps on ps.save_file_id=f.id where sp.id=%s",
                    (v["players"][index],)).fetchone()

            def args(index, team, matchday=None):
                save, digest, parsed, payload = source(index)
                return (v["sid"], matchday or day, v["trainers"][index], v["players"][index], save, digest, parsed,
                        Jsonb(payload), Jsonb(team), Jsonb(team))

            def confirm(index, team, key, matchday=None):
                return str(value(conn, "select id from public.api_confirm_team_lock(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                 args(index, team, matchday) + (key,)))

            def legacy(index, team):
                return str(value(conn, "select id from public.api_upsert_team_lock(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                 args(index, team)))

            def rows(lock):
                return conn.execute(
                    "select a.event_key,a.status,a.revision,a.discord_message_id,a.subject,c.public_team_snapshot,"
                    "c.trainer_id,c.matchday_id,c.is_replacement from public.discord_announcements a"
                    " left join public.team_lock_confirmations c on c.id=(a.subject->>'confirmation_id')::uuid"
                    " where a.kind='team_locked' and a.subject->>'lock_id'=%s order by c.confirmed_at nulls first,a.event_key",
                    (lock,)).fetchall()

            team = [{"species": s["pokemon"]["species"]} for s in source(0)[3]["party"]]
            lock = confirm(0, team, "083-first")
            first = rows(lock)
            ok(len(first) == 1 and first[0][0].startswith("team_lock_confirmation:") and first[0][1] == "pending"
               and first[0][5] == team and first[0][8] is False
               and not value(conn, "select exists(select 1 from public.discord_announcements where event_key=%s)",
                             ("team_locked:" + lock,)),
               "first «Fijar Equipo»: one immutable confirmation and one announcement, no legacy row")
            ok(confirm(0, team, "083-first") == lock and len(rows(lock)) == 1
               and value(conn, "select count(*) from public.team_lock_confirmations where team_lock_id=%s", (lock,)) == 1,
               "automatic retry with the same key replays: no second record or announcement")

            as_owner(conn, "update public.discord_announcements set status='sent',sent_at=now(),delivered_revision=1,"
                     "discord_message_id='111' where event_key=%s", (first[0][0],))
            other = [dict(m) for m in team]
            other[0] = {"species": "Pokémon #1"}
            ok(confirm(0, other, "083-other") == lock, "a different valid team replaces the same Team Lock")
            again = confirm(0, other, "083-again")
            after = rows(lock)
            ok(again == lock and len(after) == 3 and [r[5] for r in after] == [team, other, other]
               and after[0][1:4] == ("sent", 1, "111") and all(r[1:4] == ("pending", 1, None) for r in after[1:])
               and all(r[8] for r in after[1:]),
               "a different team and the same team again are two new announcements; the sent one is never edited")
            ok(all(str(r[6]) == v["trainers"][0] and str(r[7]) == day for r in after),
               "every announcement keeps its own trainer and matchday")
            ok(value(conn, "select public_team_snapshot from public.team_locks where id=%s", (lock,)) == other,
               "the Team Lock itself holds the latest confirmed team")

            observe(conn, v, 0, [], 2)  # a newer save for the same trainer
            rejected(conn, lambda: confirm(0, other, "083-first"), "idempotency_conflict")
            ok(len(rows(lock)) == 3, "reusing a key for a different request is refused without effects")
            rejected(conn, lambda: as_owner(conn, "update public.team_lock_confirmations set is_replacement=true"),
                     "historical_artifact_immutable")
            rejected(conn, lambda: as_owner(conn, "delete from public.team_lock_confirmations"),
                     "historical_artifact_immutable")
            ok(True, "confirmations cannot be updated or deleted")

            legacy_lock = legacy(1, team)
            legacy(1, other)
            ok(conn.execute("select count(*),max(revision) from public.discord_announcements where event_key=%s",
                            ("team_locked:" + legacy_lock,)).fetchone() == (1, 1),
               "legacy call: one first-lock row; a replacement no longer edits it")

            open_day(conn, v, day)
            results(conn, v, day)
            close_day(conn, v, day)
            rejected(conn, lambda: confirm(2, team, "083-closed"), "matchday_not_lockable")
            ok(value(conn, "select count(*) from public.team_lock_confirmations where trainer_id=%s",
                     (v["trainers"][2],)) == 0,
               "a closed matchday still refuses a Team Lock and records nothing")

            ok(not any(value(conn, f"select has_table_privilege('{role}','public.team_lock_confirmations','select')")
                       for role in ("anon", "authenticated"))
               and not any(value(conn, "select has_function_privilege(%s,'public.api_confirm_team_lock("
                                 "uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb,text)','execute')", (role,))
                           for role in ("anon", "authenticated")),
               "browser roles cannot read confirmations or call the confirmation RPC")
        finally:
            conn.rollback()
    return checks


def main():
    import argparse
    import json
    import os
    from pathlib import Path

    from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55643)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            pg.sql(migration.read_text(encoding="utf-8"))
        checks = validate(pg)
        report = {"result": "PASS", "checks": checks, "production_modified": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
