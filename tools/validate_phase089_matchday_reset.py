"""089 «Cancelar jornada» (owner request 2026-11-19), on the real RPCs.

Disposable loopback PostgreSQL only; every check runs in a transaction that is
always rolled back. A synthetic all-vs-all season reaches J2 through the real
open/results/close RPCs (J1 closed with its frozen deaths), then J2 is opened
by mistake: a death and a Team Lock happen in that window and one provisional
result is entered.

* ``reproduce(pg)`` on 001-088: there is no reset; «Cancelar edición» keeps the
  frozen J2 deaths, the window deaths stay battle-phase and reopening reuses
  the old snapshot, so those deaths never count for the J2 segment.
* ``validate(pg)`` after 089: only an administrator, with the current
  revision, on an open matchday; the death snapshots and the immutability of
  events stay closed to any other write (also with the setting of another
  matchday); the reset removes exactly the J2 snapshots, the start evidence,
  the provisional results and the late marks, moves the window deaths to the
  J2 progression, keeps J1 untouched, is audited and replays once; the next
  real opening freezes again from the data at that moment; «Cancelar edición»
  keeps its contract; browser roles gain nothing.
* ``validate_restored(pg)`` (backup rehearsal on a production restore): the
  real current matchday, if open, is reset and reopened by its administrator
  and freezes the same numbers again; rolled back.

    python -m tools.validate_phase089_matchday_reset --pg-bin <bin> --port <free port>
"""

import json

import psycopg
from psycopg.types.json import Jsonb

from tools.validate_phase079_all_vs_all import (
    call,
    connect,
    initialize,
    observe,
    prepare,
    value,
)
from tools.validate_phase080_enrollment import close_day, results
from tools.validate_player_matchdays import envelope, participant, rejected

PERMISSION = "permission denied for table league_death_events"
SNAPSHOT_PERMISSION = "permission denied for table matchday_death_snapshots"


def admin_day(conn, v, op, day, key, body, actor=None):
    return call(conn, "api_admin_matchday", dict(operation=op, request=envelope(
        actor or v["admin"], v, day, key, body)))


def revision(conn, day, column="revision"):
    return value(conn, f"select {column} from public.matchdays where id=%s", (day,))


def lock_team(conn, v, index, day):
    source = conn.execute(
        "select f.id::text,f.sha256,ps.id::text,ps.payload from public.season_players sp"
        " join public.save_files f on f.id=sp.current_save_file_id join public.parsed_saves ps on ps.save_file_id=f.id"
        " where sp.id=%s", (v["players"][index],)).fetchone()
    team = [dict(species=s["pokemon"]["species"]) for s in source[3]["party"]]
    return conn.execute(
        "select id::text from public.api_upsert_team_lock(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (v["sid"], day, v["trainers"][index], v["players"][index], source[0], source[1], source[2],
         Jsonb(source[3]), Jsonb(team), Jsonb(team))).fetchone()[0]


def timing(conn, lock):
    return conn.execute(
        "select f.timing_status,f.first_fixed_at,l.is_late from public.team_lock_first_fixations f"
        " join public.team_locks l on l.id=f.lock_id where f.lock_id=%s", (lock,)).fetchone()


def snapshots(conn, day):
    return conn.execute(
        "select season_player_id::text,starting_actual_deaths,ending_actual_deaths,segment_deaths,wipe_deaths"
        " from public.matchday_death_snapshots where matchday_id=%s order by season_player_id", (day,)).fetchall()


def fingerprint(conn, day):
    return value(conn, "select md5(coalesce(string_agg(to_jsonb(x)::text,'|' order by x.id),''))"
                       " from public.matchday_death_snapshots x where x.matchday_id=%s", (day,))


def phases(conn, pid, day):
    return [row[0] for row in conn.execute(
        "select phase from public.league_death_events where season_player_id=%s and matchday_id=%s"
        " order by recorded_at,id", (pid, day)).fetchall()]


def segment(conn, pid, day):
    return value(conn, "select public.league_death_segment(%s,%s)", (pid, day))


def to_second_matchday(conn):
    """J1 prepared (automatic observed baselines), opened, played and closed: J2 current."""
    v = initialize(conn)
    t, p = v["trainers"], v["players"]
    for i in range(len(p)):
        observe(conn, v, i, [], 2)
    day1 = prepare(conn, v, t[0])["matchday_id"]
    admin_day(conn, v, "open", day1, "089-open-1", dict(expected_revision=revision(conn, day1)))
    results(conn, v, day1)
    assert close_day(conn, v, day1)["state"] == "closed"
    day2 = value(conn, "select current_matchday_id::text from public.seasons where id=%s", (v["sid"],))
    assert day2 != day1 and revision(conn, day2) == 0
    assert len(snapshots(conn, day1)) == len(p)
    return v, day1, day2


def mistaken_opening(conn, v, day2):
    """J2: one progression death, a lock on time, the opening, then the window."""
    t, p = v["trainers"], v["players"]
    observe(conn, v, 0, [1], 8)
    for i in range(1, len(p)):
        observe(conn, v, i, [], 8)
    early = lock_team(conn, v, 1, day2)
    admin_day(conn, v, "open", day2, "089-open-2", dict(expected_revision=revision(conn, day2)))
    assert len(snapshots(conn, day2)) == len(p) and segment(conn, p[0], day2) == 1
    frozen = dict((row[0], row[3]) for row in snapshots(conn, day2))
    assert frozen[p[0]] == 1, frozen
    # The window: a death, a late Team Lock and a provisional result.
    observe(conn, v, 0, [1, 2], 8)
    late = lock_team(conn, v, 2, day2)
    assert timing(conn, late)[0] == "late" and timing(conn, late)[2] is True
    assert timing(conn, early)[0] == "on_time"
    match = conn.execute("select id::text,player_a_id::text from public.matches where matchday_id=%s order by id limit 1",
                         (day2,)).fetchone()
    participant(conn, "results", envelope(t[3], v, day2, "089-results-2", dict(
        expected_results_revision=revision(conn, day2, "results_revision"),
        results=[dict(match_id=match[0], winner_season_player_id=match[1])])))
    assert phases(conn, p[0], day2) == ["progression", "battle"], phases(conn, p[0], day2)
    return early, late, match[0]


def reproduce(pg):
    """On 001-088: no reset; «Cancelar edición» + reopen loses the window deaths."""
    with connect(pg) as conn:
        try:
            v, _, day2 = to_second_matchday(conn)
            p = v["players"]
            mistaken_opening(conn, v, day2)
            refused = rejected(conn, lambda: admin_day(conn, v, "reset", day2, "089-reset-088", dict(
                expected_revision=revision(conn, day2), reason="Abierta por error")), "invalid_request")
            # Results first (the cancel refuses provisional results), then cancel.
            conn.execute("reset role")
            conn.execute("update public.matches set winner_id=null,status='scheduled' where matchday_id=%s", (day2,))
            conn.execute("set local role service_role")
            admin_day(conn, v, "cancel", day2, "089-cancel-088", dict(expected_revision=revision(conn, day2), reason="x"))
            observe(conn, v, 0, [1, 2, 3], 8)   # still progressing after the cancel
            admin_day(conn, v, "open", day2, "089-reopen-088", dict(expected_revision=revision(conn, day2)))
            frozen = dict((row[0], row[3]) for row in snapshots(conn, day2))
            assert frozen[p[0]] == 1 and phases(conn, p[0], day2) == ["progression", "battle", "battle"]
            return dict(reset_refused=refused, j2_segment_after_cancel_and_reopen=frozen[p[0]],
                        deaths_lost_as_battle=2)
        finally:
            conn.rollback()


def validate(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v, day1, day2 = to_second_matchday(conn)
            t, p = v["trainers"], v["players"]
            j1 = fingerprint(conn, day1)
            early, late, provisional = mistaken_opening(conn, v, day2)
            early_before = timing(conn, early)
            started = value(conn, "select first_started_at from public.matchday_start_evidence where matchday_id=%s", (day2,))
            assert started is not None
            rev = revision(conn, day2)
            body = dict(expected_revision=rev, reason="Abierta por error")

            rejected(conn, lambda: admin_day(conn, v, "reset", day2, "089-r-participant", body, actor=t[0]),
                     "admin_required")
            rejected(conn, lambda: admin_day(conn, v, "reset", day2, "089-r-stale", dict(body, expected_revision=rev + 1)),
                     "stale_revision")
            rejected(conn, lambda: admin_day(conn, v, "reset", day1, "089-r-closed", dict(body, expected_revision=revision(conn, day1))),
                     "matchday_not_current")
            checks.append("reset only by an administrator, with the current revision, on the current matchday")

            rejected(conn, lambda: conn.execute("delete from public.matchday_death_snapshots where matchday_id=%s", (day2,)),
                     "historical_artifact_immutable")
            rejected(conn, lambda: conn.execute("update public.matchday_death_snapshots set segment_deaths=0 where matchday_id=%s",
                                                (day2,)), "historical_artifact_immutable", SNAPSHOT_PERMISSION)
            rejected(conn, lambda: conn.execute("update public.league_death_events set phase='progression'"
                                                " where matchday_id=%s and phase='battle'", (day2,)), "historical_artifact_immutable")
            rejected(conn, lambda: conn.execute("delete from public.league_death_events where matchday_id=%s", (day2,)),
                     "historical_artifact_immutable", "permission denied for table league_death_events")

            def scoped(sql, args):
                conn.execute("select set_config('pokeapp.matchday_reset',%s,true)", (day2,))
                conn.execute(sql, args)

            rejected(conn, lambda: scoped("delete from public.matchday_death_snapshots where matchday_id=%s", (day1,)),
                     "historical_artifact_immutable")
            rejected(conn, lambda: scoped("update public.matchday_death_snapshots set segment_deaths=0 where matchday_id=%s", (day2,)),
                     "historical_artifact_immutable", SNAPSHOT_PERMISSION)
            rejected(conn, lambda: scoped("update public.league_death_events set phase='preseason' where matchday_id=%s", (day2,)),
                     "historical_artifact_immutable")
            rejected(conn, lambda: scoped("update public.league_death_events set phase='progression',observed_at=observed_at"
                                          " where matchday_id=%s and phase='battle'", (day2,)), PERMISSION)
            rejected(conn, lambda: scoped("update public.league_death_events set phase='battle' where matchday_id=%s"
                                          " and phase='progression'", (day2,)), "historical_artifact_immutable")
            assert len(snapshots(conn, day2)) == len(p) and fingerprint(conn, day1) == j1
            checks.append("snapshots/events stay immutable for any other write, also with the setting of another matchday")

            reset = admin_day(conn, v, "reset", day2, "089-reset", body)
            assert reset["state"] == "scheduled" and reset["revision"] == rev + 1 and reset["replayed"] is False, reset
            assert reset["snapshot_revision"] == 0 and reset["current_matchday_id"] == day2
            assert value(conn, "select status||':'||coalesce(opened_at::text,'-') from public.matchdays where id=%s", (day2,)) == "scheduled:-"
            assert snapshots(conn, day2) == [] and fingerprint(conn, day1) == j1
            assert conn.execute("select first_started_at from public.matchday_start_evidence where matchday_id=%s",
                                (day2,)).fetchall() == [(None,)]
            assert phases(conn, p[0], day2) == ["progression", "progression"] and segment(conn, p[0], day2) == 2
            assert value(conn, "select count(*) from public.league_death_events e join public.matchdays d on d.id=e.matchday_id"
                               " where d.season_id=%s and e.phase='battle'", (v["sid"],)) == 0
            assert value(conn, "select count(*) from public.matches where matchday_id=%s and (winner_id is not null or status<>'scheduled')",
                         (day2,)) == 0
            assert timing(conn, late)[0] == "on_time" and timing(conn, late)[2] is False
            assert timing(conn, early) == early_before
            checks.append("reset: J2 snapshots, start evidence, provisional result and late mark gone; window death back in the J2 progression (2); J1 untouched")

            event = conn.execute("select actor_trainer_id::text,visibility,payload from public.activity_events"
                                 " where season_id=%s and type='MATCHDAY_ADMIN_RESET'", (v["sid"],)).fetchall()
            assert len(event) == 1 and event[0][0] == v["admin"] and event[0][1] == "admin"
            reverted = event[0][2]["reverted"]
            assert event[0][2]["reason"] == "Abierta por error"
            assert len(reverted["removed_death_snapshots"]) == len(p)
            assert len(reverted["death_events_back_to_progression"]) == 1
            assert reverted["team_locks_back_on_time"] == [late]
            assert [r["match_id"] for r in reverted["discarded_results"]] == [provisional]
            assert reverted["first_started_at"] is not None
            replay = admin_day(conn, v, "reset", day2, "089-reset", body)
            assert replay == dict(reset, replayed=True), replay
            assert value(conn, "select count(*) from public.activity_events where season_id=%s and type='MATCHDAY_ADMIN_RESET'",
                         (v["sid"],)) == 1
            rejected(conn, lambda: admin_day(conn, v, "reset", day2, "089-reset-again", dict(body, expected_revision=rev + 1)),
                     "matchday_not_open")
            checks.append("audited MATCHDAY_ADMIN_RESET (5 snapshots, 1 death, 1 lock, 1 result); same key replays; a scheduled day refuses")

            observe(conn, v, 0, [1, 2, 3], 8)
            assert phases(conn, p[0], day2) == ["progression"] * 3
            again = lock_team(conn, v, 3, day2)
            assert timing(conn, again)[0] == "on_time"
            opened = admin_day(conn, v, "open", day2, "089-open-3", dict(expected_revision=revision(conn, day2)))
            assert opened["state"] == "open"
            frozen = dict((row[0], row) for row in snapshots(conn, day2))
            assert len(frozen) == len(p) and frozen[p[0]][3] == 3 and frozen[p[0]][2] - frozen[p[0]][1] == 3, frozen
            assert value(conn, "select first_started_at from public.matchday_start_evidence where matchday_id=%s", (day2,)) > started
            assert timing(conn, lock_team(conn, v, 4, day2))[0] == "late"
            checks.append("the real opening freezes again from that moment (J2 segment 3) and late fixations count again")

            admin_day(conn, v, "cancel", day2, "089-cancel", dict(expected_revision=revision(conn, day2), reason="x"))
            assert len(snapshots(conn, day2)) == len(p)
            checks.append("«Cancelar edición» keeps its contract (frozen snapshots kept)")

            conn.execute("reset role")
            for role in ("anon", "authenticated"):
                for function in ("public.matchday_reset_opening(uuid,uuid)", "public.api_admin_matchday(jsonb)",
                                 "public.matchday_reset_artifact_guard()"):
                    assert not value(conn, "select has_function_privilege(%s,%s,'execute')", (role, function)), (role, function)
                assert not value(conn, "select has_table_privilege(%s,'public.matchday_death_snapshots','delete')", (role,))
                assert not value(conn, "select has_column_privilege(%s,'public.league_death_events','phase','update')", (role,))
            assert value(conn, "select has_function_privilege('service_role','public.api_admin_matchday(jsonb)','execute')")
            checks.append("browser roles gain nothing; service_role keeps the command")
        finally:
            conn.rollback()
    return "PASS: " + "; ".join(checks)


def validate_restored(pg):
    """The restored current matchday, if open: reset and reopen; rolled back."""
    with connect(pg) as conn:
        try:
            conn.execute("set local role service_role")
            row = conn.execute("select s.id::text,d.id::text,d.number,d.status,d.revision from public.seasons s"
                               " join public.matchdays d on d.id=s.current_matchday_id where s.status='active'").fetchone()
            if row is None or row[3] != "open":
                return f"SKIP: current matchday not open ({row[3] if row else 'none'})"
            sid, day, number, _, rev = row
            v = dict(sid=sid)
            admin = value(conn, "select id::text from public.trainers where is_admin and globally_enabled"
                                " order by created_at limit 1")
            names = dict(conn.execute("select sp.id::text,t.display_name from public.season_players sp"
                                      " join public.trainers t on t.id=sp.trainer_id where sp.season_id=%s", (sid,)).fetchall())
            before = snapshots(conn, day)
            others = value(conn, "select md5(coalesce(string_agg(to_jsonb(x)::text,'|' order by x.id),''))"
                                 " from public.matchday_death_snapshots x where x.matchday_id<>%s", (day,))
            battle = value(conn, "select count(*) from public.league_death_events where matchday_id=%s and phase='battle'", (day,))
            reset = admin_day(conn, v, "reset", day, "089-rehearsal-reset",
                              dict(expected_revision=rev, reason="Rehearsal"), actor=admin)
            assert reset["state"] == "scheduled" and snapshots(conn, day) == []
            assert value(conn, "select count(*) from public.league_death_events where matchday_id=%s and phase='battle'", (day,)) == 0
            assert value(conn, "select md5(coalesce(string_agg(to_jsonb(x)::text,'|' order by x.id),''))"
                               " from public.matchday_death_snapshots x where x.matchday_id<>%s", (day,)) == others
            admin_day(conn, v, "open", day, "089-rehearsal-open", dict(expected_revision=reset["revision"]), actor=admin)
            after = snapshots(conn, day)
            if not battle:
                assert after == before, (before, after)
            shown = {names[r[0]]: f"{r[3]} (de {r[1]} a {r[2]})" for r in after}
            return (f"PASS (rolled back): J{number} reset and reopened by its administrator; window deaths moved {battle};"
                    f" segments frozen again {json.dumps(shown, ensure_ascii=True)}; other matchdays untouched")
        finally:
            conn.rollback()


def main():
    import argparse
    import os
    from pathlib import Path

    from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "PokeAppDev/pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55689)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            if int(migration.name[:3]) <= 88:
                pg.sql(migration.read_text(encoding="utf-8"))
        before = reproduce(pg)
        target = next(m for m in MIGRATIONS if m.name.startswith("089_"))
        run = pg.sql(target.read_text(encoding="utf-8"), "postgres", ok=False)
        assert not run.returncode, run.err[-600:]
        report = {"result": "PASS", "defect_reproduced_on_088": before, "checks": validate(pg),
                  "production_modified": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
