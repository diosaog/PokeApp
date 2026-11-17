"""086 jornada order by direct match (owner rule of 2026-11-17), on the real RPCs.

validate(pg) (rolled back, any database with 086 applied):

* two level on wins: the direct match decides, even against fewer deaths;
* three level on wins: fewer stretch deaths; a pair still level: direct match;
* three level on wins and deaths for the podium: extra 1v1 battles, accepted;
* SQL refuses a plan ordered by the previous rule or with a forged order;
* an audited correction is re-planned with the new rule;
* the provisional order of an open jornada follows the same rule.

validate_087(pg) (read-only): robberies no longer issue «Blindaje por Robo»,
a steal receipt is valid without a gift, and no voucher stays usable.

validate_retroactive(pg_bin, port) (own disposable cluster, commits):

* J1 closed with migrations <=085 gives «Blindar Pokémon» to the trainer who
  lost the direct match (fewer deaths); J2 closes with unique wins;
* with that reward marked as used, 086 aborts and changes nothing;
* with it unused, 086 writes J1 revision 2 (rule v3), cancels the old reward,
  issues it to the direct-match winner, queues «Jornada corregida», keeps
  results, points, coins and J2 untouched; J3 then closes under the new rule.

    python -m tools.validate_phase086_h2h_tiebreak --port <free port>
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
import argparse
import os

import psycopg
from psycopg.types.json import Jsonb

from app.api.read_models import StandingRead
from app.application.frontend_reads import public_daily_standing
from tools.validate_phase075_league import (
    confirm,
    connect,
    initialize,
    prepare_close,
    request,
    rpc,
    value,
)

RULE = "wins_h2h_deaths_v3"
MIGRATIONS = Path(__file__).resolve().parents[1] / "supabase/v2/migrations"
# p0 and p1 on three wins, p0 won their match; p3 and p4 on one, p3 won theirs.
J1_BEATS = {0: [1, 2, 3], 1: [2, 3, 4], 2: [3, 4], 3: [4], 4: [0]}
# Cycle p0>p1>p2>p0, all three beat p3 and p4; p3 beats p4.
CYCLE_BEATS = {0: [1, 3, 4], 1: [2, 3, 4], 2: [0, 3, 4], 3: [4], 4: []}
UNIQUE_BEATS = {0: [1, 2, 3, 4], 1: [2, 3, 4], 2: [3, 4], 3: [4], 4: []}


class _Rollback(Exception):
    pass


def refused(conn, call):
    try:
        with conn.transaction():
            try:
                call()
            except psycopg.Error as exc:
                raise _Rollback(exc.diag.message_primary) from exc
    except _Rollback as exc:
        return str(exc)
    raise AssertionError("accepted")


def current_day(conn, v):
    return str(value(conn, "select current_matchday_id from public.seasons where id=%s", (v["sid"],)))


def deaths(conn, totals, segment):
    """Confirm each trainer's cumulative deaths before a jornada opens."""
    for index, delta in enumerate(segment):
        totals[index] += delta
        confirm(conn, index, totals[index], delta)


def open_day(conn, v, day, key):
    revision = value(conn, "select revision from public.matchdays where id=%s", (day,))
    return rpc(conn, "api_admin_matchday", dict(operation="open",
               request=request(v, day, f"{key}-open", dict(expected_revision=revision))))


def record(conn, v, day, key, beats, pairs=None):
    """Record winners from a beats relation (player indexes); optionally only some pairs."""
    index = {pid: i for i, pid in enumerate(v["players"])}
    results = []
    for mid, a, b in conn.execute(
            "select id,player_a_id,player_b_id from public.matches where matchday_id=%s order by id", (day,)).fetchall():
        i, j = index[str(a)], index[str(b)]
        if pairs is not None and frozenset((i, j)) not in pairs:
            continue
        winner = i if j in beats[i] else j
        assert (j in beats[i]) != (i in beats[j]), (i, j)
        results.append(dict(match_id=str(mid), winner_season_player_id=v["players"][winner]))
    revision = value(conn, "select results_revision from public.matchdays where id=%s", (day,))
    rpc(conn, "api_admin_matchday", dict(operation="results", request=request(
        v, day, f"{key}-results", dict(expected_results_revision=revision, results=results))))


def close(conn, v, day, key):
    envelope = prepare_close(conn, v, day, key)
    receipt = rpc(conn, "api_admin_matchday", envelope)
    assert receipt["state"] == "closed", receipt
    return envelope


def snapshot(conn, day):
    return value(conn, "select snapshot from public.matchday_snapshots where matchday_id=%s", (day,))


def order(v, snap):
    index = {pid: i for i, pid in enumerate(v["players"])}
    rows = sorted(snap["standings"], key=lambda r: r["metadata"]["allocation_position"])
    return [index[r["trainer_id"]] for r in rows]


def rows_by_index(v, snap):
    index = {pid: i for i, pid in enumerate(v["players"])}
    return {index[r["trainer_id"]]: r for r in snap["standings"]}


def prizes(conn, v, day):
    """[(item code, player index, status)] of the jornada's reward purchases."""
    index = {pid: i for i, pid in enumerate(v["players"])}
    return sorted((code, index[str(pid)], status) for pid, status, code in conn.execute(
        "select p.season_player_id,p.status,i.code from public.purchases p join public.shop_items i"
        " on i.id=p.shop_item_id where p.origin_matchday_id=%s", (day,)).fetchall())


def public_rows(snap):
    for row in snap["standings"]:
        StandingRead.model_validate(public_daily_standing(snap, row))


def validate(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            totals = [0] * 5

            # J1: same wins, p0 won the direct match but died more.
            deaths(conn, totals, [2, 0, 0, 0, 1])
            day = current_day(conn, v)
            open_day(conn, v, day, "086-j1")
            record(conn, v, day, "086-j1", J1_BEATS)
            envelope = prepare_close(conn, v, day, "086-j1-close")
            assert envelope["plan"]["ranking"]["rule"] == RULE
            old = deepcopy(envelope)
            # A plan ordered by the previous rule is refused.
            from app.application.matchdays import plan_close
            context = rpc(conn, "api_admin_matchday_context", dict(operation="close", request=envelope["request"]))
            assert context["context"]["ranking_rule"] == RULE
            legacy = dict(context["context"], ranking_rule="wins_segment_deaths_v2")
            old["plan"] = plan_close(legacy)
            message = refused(conn, lambda: rpc(conn, "api_admin_matchday", old))
            assert message == "invalid_results", message
            # A forged v3 order (fewer deaths first) is refused.
            forged = deepcopy(envelope)
            rows = {r["trainer_id"]: r for r in forged["plan"]["standings"]}
            a, b = rows[v["players"][0]], rows[v["players"][1]]
            for key in ("position", "division_position"):
                a[key], b[key] = b[key], a[key]
            for key in ("allocation_position", "position_end", "placement_rewards"):
                a["metadata"][key], b["metadata"][key] = b["metadata"][key], a["metadata"][key]
            forged["plan"]["single_league_rewards"][0]["season_player_id"] = v["players"][1]
            message = refused(conn, lambda: rpc(conn, "api_admin_matchday", forged))
            assert message == "invalid_results", message
            receipt = rpc(conn, "api_admin_matchday", envelope)
            assert receipt["state"] == "closed"
            snap = snapshot(conn, day)
            assert order(v, snap) == [0, 1, 2, 3, 4], order(v, snap)
            rows = rows_by_index(v, snap)
            assert rows[0]["metadata"]["tiebreak"] == rows[1]["metadata"]["tiebreak"] == "head_to_head"
            assert rows[2]["metadata"]["tiebreak"] is None
            assert snap["inputs"]["ranking"]["rule"] == RULE
            assert prizes(conn, v, day) == [("blindar_pokemon", 0, "pending"), ("robar_pokemon", 4, "pending")]
            public_rows(snap)
            checks.append("J1 2-level on wins: direct match beats fewer deaths; v2-ordered and forged plans refused; Blindar p0/Robar p4")

            # Audited correction before J2 opens: p0 now also beats p4.
            match = conn.execute("select id from public.matches where matchday_id=%s and %s in (player_a_id,player_b_id)"
                                 " and %s in (player_a_id,player_b_id)", (day, v["players"][0], v["players"][4])).fetchone()[0]
            corrected = prepare_close(conn, v, day, "086-j1-correct",
                                      [dict(match_id=str(match), winner_season_player_id=v["players"][0])])
            assert corrected["plan"]["ranking"]["rule"] == RULE
            rpc(conn, "api_admin_matchday", corrected)
            snap = snapshot(conn, day)
            assert order(v, snap) == [0, 1, 2, 3, 4]
            rows = rows_by_index(v, snap)
            assert rows[0]["metadata"]["tiebreak"] is None and rows[3]["metadata"]["tiebreak"] is None
            assert rows[3]["metadata"]["wins"] == 1 and rows[4]["metadata"]["wins"] == 0
            assert value(conn, "select revision from public.matchday_snapshots where matchday_id=%s", (day,)) == 2
            checks.append("audited correction re-planned with v3 (revision 2)")

            # J2: cycle on three wins; p2 died least, p0/p1 level on deaths -> p0 beat p1.
            deaths(conn, totals, [1, 1, 0, 0, 0])
            day = current_day(conn, v)
            open_day(conn, v, day, "086-j2")
            # Provisional order mid-jornada, after p0>p1, p1>p2 and p3>p4: p0, p1
            # and p3 on one win -> p3 died least; p0/p1 level on deaths and
            # their match is played -> p0. p2 and p4 on zero wins, level on
            # deaths and their match not played yet -> they share 4th.
            record(conn, v, day, "086-j2-partial", CYCLE_BEATS,
                   {frozenset((0, 1)), frozenset((1, 2)), frozenset((3, 4))})
            live = value(conn, "select public.league_live_matchday_scores(%s,%s)", (v["sid"], day))[0]["standings"]
            index = {pid: i for i, pid in enumerate(v["players"])}
            live = {index[r["season_player_id"]]: r for r in live}
            assert (live[3]["position"], live[3]["tiebreak"]) == (1, "segment_deaths"), live[3]
            assert (live[0]["position"], live[0]["tiebreak"]) == (2, "head_to_head"), live[0]
            assert (live[1]["position"], live[1]["tiebreak"]) == (3, "head_to_head"), live[1]
            assert [(live[i]["position"], live[i]["tiebreak"]) for i in (2, 4)] == [(4, None), (4, None)], live
            record(conn, v, day, "086-j2", CYCLE_BEATS)
            close(conn, v, day, "086-j2-close")
            snap = snapshot(conn, day)
            assert order(v, snap) == [2, 0, 1, 3, 4], order(v, snap)
            rows = rows_by_index(v, snap)
            assert rows[2]["metadata"]["tiebreak"] == "segment_deaths"
            assert rows[0]["metadata"]["tiebreak"] == rows[1]["metadata"]["tiebreak"] == "head_to_head"
            assert prizes(conn, v, day) == [("blindar_pokemon", 2, "pending"), ("robar_pokemon", 4, "pending")]
            public_rows(snap)
            checks.append("J2 3-level: fewer deaths, remaining pair by direct match; live order uses direct match")

            # J3: cycle with equal deaths for the podium -> recorded extra 1v1 battles.
            deaths(conn, totals, [0, 0, 0, 0, 0])
            day = current_day(conn, v)
            open_day(conn, v, day, "086-j3")
            record(conn, v, day, "086-j3", CYCLE_BEATS)
            envelope = close(conn, v, day, "086-j3-close")
            orders = envelope["request"]["body"]["tie_resolution"]["orders"]
            assert len(orders) == 1 and sorted(orders[0]["player_ids"]) == sorted(v["players"][:3])
            snap = snapshot(conn, day)
            rows = rows_by_index(v, snap)
            assert {rows[i]["metadata"]["tie_status"] for i in range(3)} == {"externally_resolved"}
            assert order(v, snap)[3:] == [3, 4]
            public_rows(snap)
            checks.append("J3 3-level on wins and deaths for the podium: extra 1v1 battles accepted")
        finally:
            conn.rollback()
    return "PASS (rolled back): " + "; ".join(checks)


def validate_retroactive(pg_bin, port):
    """Own cluster: commits a <=085 fixture, then applies 086 twice (abort, success)."""
    from tools.phase30_release_audit import SupabaseLikePG

    pg = SupabaseLikePG(pg_bin, port)
    checks = []
    try:
        pg.start()
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            if int(migration.name[:3]) <= 85:
                pg.sql(migration.read_text(encoding="utf-8"))
        h2h = (MIGRATIONS / "086_matchday_head_to_head.sql").read_text(encoding="utf-8")
        with connect(pg) as conn:
            v = initialize(conn)
            totals = [0] * 5
            deaths(conn, totals, [2, 0, 0, 0, 1])
            j1 = current_day(conn, v)
            open_day(conn, v, j1, "086r-j1")
            record(conn, v, j1, "086r-j1", J1_BEATS)
            close(conn, v, j1, "086r-j1-close")
            before = snapshot(conn, j1)
            assert before["inputs"]["ranking"]["rule"] == "wins_segment_deaths_v2"
            assert order(v, before) == [1, 0, 2, 3, 4], order(v, before)
            assert prizes(conn, v, j1) == [("blindar_pokemon", 1, "pending"), ("robar_pokemon", 4, "pending")]
            deaths(conn, totals, [0, 0, 0, 0, 0])
            j2 = current_day(conn, v)
            open_day(conn, v, j2, "086r-j2")
            record(conn, v, j2, "086r-j2", UNIQUE_BEATS)
            close(conn, v, j2, "086r-j2-close")
            j2_before = snapshot(conn, j2)
            general = value(conn, "select public.league_general_read(%s)->'rows'", (v["sid"],))
            coins = value(conn, "select count(*)||':'||sum(amount) from public.coin_transactions where season_id=%s", (v["sid"],))
            results = conn.execute("select id,winner_id from public.matches m join public.matchdays d on d.id=m.matchday_id"
                                   " where d.season_id=%s order by id", (v["sid"],)).fetchall()
            conn.commit()
            checks.append("<=085: J1 v2 gives Blindar to p1 (fewer deaths, lost to p0); J2 unique")

            reward = conn.execute("select p.id from public.purchases p join public.shop_items i on i.id=p.shop_item_id"
                                  " where p.origin_matchday_id=%s and i.code='blindar_pokemon'", (j1,)).fetchone()[0]
            conn.execute("alter table public.purchases disable trigger user")
            conn.execute("update public.purchases set status='used' where id=%s", (reward,))
            conn.execute("alter table public.purchases enable trigger user")
            conn.commit()
            run = pg.sql(h2h, "postgres", ok=False)
            assert run.returncode and "already in use" in run.err, run.err[-600:]
            assert value(conn, "select revision from public.matchday_snapshots where matchday_id=%s", (j1,)) == 1
            assert to_regprocedure(conn, "public.league_h2h_order(jsonb,jsonb)") is None
            conn.rollback()
            checks.append("used reward: 086 aborts atomically (J1 revision 1, no new function)")

            conn.execute("alter table public.purchases disable trigger user")
            conn.execute("update public.purchases set status='pending' where id=%s", (reward,))
            conn.execute("alter table public.purchases enable trigger user")
            conn.commit()
            run = pg.sql(h2h, "postgres", ok=False)
            assert not run.returncode, run.err[-600:]
            after = snapshot(conn, j1)
            assert after["revision"] == 2 and after["inputs"]["ranking"]["rule"] == RULE
            assert after["correction"] == dict(kind="h2h_tiebreak_rule", previous_revision=1)
            assert order(v, after) == [0, 1, 2, 3, 4], order(v, after)
            rows = rows_by_index(v, after)
            assert rows[0]["metadata"]["placement_rewards"] == ["blindar_pokemon"]
            assert rows[1]["metadata"]["placement_rewards"] == []
            assert rows[0]["metadata"]["tiebreak"] == "head_to_head"
            assert [rows[i]["points_awarded"] for i in range(5)] == [before_row["points_awarded"] for before_row in
                    sorted(before["standings"], key=lambda r: v["players"].index(r["trainer_id"]))]
            assert prizes(conn, v, j1) == [("blindar_pokemon", 0, "pending"), ("blindar_pokemon", 1, "cancelled"),
                                           ("robar_pokemon", 4, "pending")], prizes(conn, v, j1)
            assert value(conn, "select revision from public.matchday_snapshot_revisions where matchday_id=%s and revision=1",
                         (j1,)) == 1
            event = conn.execute("select type,payload->>'source' from public.activity_events where dedupe_key=%s",
                                 (f"matchday-h2h-086:{j1}:2",)).fetchone()
            assert event == ("MATCHDAY_ADMIN_CORRECT", "086_h2h_tiebreak"), event
            outbox = conn.execute("select kind from public.discord_announcements where event_key=%s",
                                  (f"matchday:{j1}:2",)).fetchone()
            assert outbox == ("matchday_corrected",), outbox
            assert snapshot(conn, j2) == j2_before
            assert value(conn, "select public.league_general_read(%s)->'rows'", (v["sid"],)) == general
            assert value(conn, "select count(*)||':'||sum(amount) from public.coin_transactions where season_id=%s",
                         (v["sid"],)) == coins
            assert conn.execute("select id,winner_id from public.matches m join public.matchdays d on d.id=m.matchday_id"
                                " where d.season_id=%s order by id", (v["sid"],)).fetchall() == results
            assert to_regprocedure(conn, "public.league_h2h_rerank_closed(uuid,uuid,text)") is None
            public_rows(after)
            conn.rollback()
            run = pg.sql((MIGRATIONS / "087_retire_robbery_shield_voucher.sql").read_text(encoding="utf-8"),
                         "postgres", ok=False)
            assert not run.returncode, run.err[-600:]
            checks.append(validate_087(pg))
            checks.append("086: J1 rev2 v3, Blindar p1 cancelled -> p0 pending, Robar kept, «Jornada corregida» queued;"
                          " J2/results/points/coins unchanged")

            conn.execute("set role service_role")
            deaths(conn, totals, [0, 0, 1, 0, 0])
            j3 = current_day(conn, v)
            open_day(conn, v, j3, "086r-j3")
            record(conn, v, j3, "086r-j3", CYCLE_BEATS)
            close(conn, v, j3, "086r-j3-close")
            assert order(v, snapshot(conn, j3)) == [0, 1, 2, 3, 4]
            conn.rollback()
            checks.append("J3 closes under v3 after 086")
    finally:
        pg.stop(remove=True)
    return "PASS: " + "; ".join(checks)


def validate_087(pg):
    """Any database with 087: robberies issue no voucher; none stays usable."""
    with connect(pg) as conn:
        try:
            definition = value(conn, "select pg_get_functiondef("
                               "'public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure)")
            assert "v_voucher,1,0" not in definition and "v_gift:=gen_random_uuid()" not in definition
            assert "when 'robbery_shield_voucher' then 'robbery_shield'" in definition
            assert "insert into public.pokemon_entity_flags" in definition and "'robado'" in definition
            constraint = value(conn, "select pg_get_constraintdef(oid) from pg_constraint where"
                               " conname='redemption_boundary_chk' and conrelid='public.redemptions'::regclass")
            steal = constraint[constraint.index("'steal'"):]
            assert "gift_purchase_id IS NOT NULL" not in steal, constraint
            assert "robbery_cycle_number IS NOT NULL" in steal, constraint
            pending = value(conn, "select count(*) from public.purchases p join public.shop_items i on i.id=p.shop_item_id"
                                  " where i.code='robbery_shield_voucher' and p.status='pending'")
            assert pending == 0, pending
            retired = value(conn, "select count(*) from public.purchases where metadata->>'cancelled_by_migration'='087'")
        finally:
            conn.rollback()
    return (f"PASS (read-only): robbery issues no «Blindaje por Robo»; steal receipts valid without gift;"
            f" 0 usable vouchers ({retired} retired)")


def to_regprocedure(conn, signature):
    return value(conn, "select to_regprocedure(%s)::text", (signature,))


def main():
    from tools.phase30_release_audit import SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path,
                        default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55861)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            if int(migration.name[:3]) <= 87:
                pg.sql(migration.read_text(encoding="utf-8"))
        print(validate(pg))
        print(validate_087(pg))
    finally:
        pg.stop(remove=True)
    print(validate_retroactive(args.pg_bin, args.port + 1))


if __name__ == "__main__":
    main()
