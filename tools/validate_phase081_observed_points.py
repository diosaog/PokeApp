"""Focused 081 acceptance on a disposable loopback DB; always rolls back.

The database must already contain 001-081. No production transport or saves.
"""

from decimal import Decimal

from tools.validate_phase079_all_vs_all import (
    as_owner,
    connect,
    death,
    initialize,
    observe,
    prepare,
    readiness,
    value,
    wipe,
)
from tools.validate_phase080_enrollment import (
    attach_entities,
    enroll,
    entrant,
    open_day,
)


def validate(pg):
    checks = []

    def ok(condition, label):
        assert condition, label
        checks.append(label)

    with connect(pg) as conn:
        try:
            v = initialize(conn)
            for index in range(5):
                observe(conn, v, index, [1, 2, 3] if index == 0 else [], 2)
            players = v["players"]

            def totals(pid):
                return value(conn, "select public.league_death_totals(%s)", (pid,))

            def points(pid):
                rows = value(conn, "select public.league_general_read(%s)", (v["sid"],))["rows"]
                return next(row["total_points"] for row in rows if row["season_player_id"] == pid)

            tables = (
                "league_death_history", "league_death_events", "league_death_resolutions",
                "coin_transactions", "save_files", "season_players", "season_player_stats",
            )

            def fingerprints():
                return {
                    table: value(conn, "select md5(coalesce(jsonb_agg(to_jsonb(t) "
                                 f"order by to_jsonb(t)::text)::text,'')) from public.{table} t")
                    for table in tables
                }

            before = fingerprints()
            ok(Decimal(points(players[2])) == 0 and Decimal(points(players[0])) == Decimal("-0.3"),
               "automatic NET 0/-0.3 from valid observed sources, without confirmation")
            ok(fingerprints() == before, "automatic reads leave all seven relevant tables unchanged")
            states = [death(conn, v, v["trainers"][index]) for index in (0, 2)]
            ok(all(s["known"] and not s["can_confirm"] and s["confirmed_at"] is None for s in states),
               "known API state with no player confirmation or fabricated timestamp")
            ready = readiness(conn, v, v["trainers"][0])
            ok(ready["can_open"] and all(not p["self_confirmable"] for p in ready["participants"]),
               "complete official sources make J1 ready without a confirmation gate")
            day = prepare(conn, v, v["trainers"][0])["matchday_id"]
            open_day(conn, v, day)
            ok(value(conn, "select count(*) from public.matchday_death_snapshots where matchday_id=%s",
                     (day,)) == 5,
               "normal participant opening freezes five observed death snapshots without manual baselines")
            as_owner(conn, "update public.league_death_history set actual_offset=2 where season_player_id=%s",
                     (players[1],))
            ok(Decimal(points(players[1])) == Decimal("-0.2"), "existing audited historical offset retained")
            observe(conn, v, 0, [1, 2, 3, 4], 2)
            observe(conn, v, 0, [1, 2, 3, 4], 2)
            ok(totals(players[0])["actual_deaths"] == 4 and Decimal(points(players[0])) == Decimal("-0.4"),
               "later observed death counted once across repeated complete observations")
            wipe(conn, v, 0, 1, "081-wipe")
            ok(totals(players[0])["known"] and Decimal(points(players[0])) == Decimal("-0.5"),
               "current authoritative wipe counter applies without another confirmation")
            trainer = entrant(conn)
            new_player, _, _ = enroll(conn, v, trainer)
            attach_entities(conn, v, new_player)
            players.append(new_player)
            v["trainers"].append(trainer)
            observe(conn, v, 5, [1, 2], 1)
            ok(totals(new_player)["known"] and Decimal(points(new_player)) == 0,
               "080 enrollment still starts at zero and excludes its initial death evidence")
            as_owner(conn, "update public.season_players set current_save_file_id=null where id=%s", (players[2],))
            ok(not totals(players[2])["known"] and points(players[2]) is None,
               "missing official source remains unknown, never an invented zero")
            as_owner(conn, "update public.league_death_history set blocking_reason='death_history_observation_gap' "
                     "where season_player_id=%s", (players[1],))
            ok(not totals(players[1])["known"] and points(players[1]) is None,
               "real observation gap remains blocked")
            as_owner(conn, "update public.season_player_stats set revived_after_wipe=99 where season_player_id=%s",
                     (players[0],))
            ok(totals(players[0])["blocking_reason"] == "death_history_inconsistent",
               "inconsistent wipe/death counters remain unknown")
            ok(not value(conn, "select has_function_privilege('authenticated',"
                         "'public.league_death_totals(uuid)','execute')"),
               "private read function keeps its existing service-only privileges")
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
    parser.add_argument("--port", type=int, default=55641)
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
