"""Rollback-only final-title acceptance on isolated PostgreSQL fixtures.

No remote connection, owner save, real purchase, or matchday scoring change.
validate_concurrency() additionally commits synthetic fixture data and therefore
must run only on a dedicated disposable cluster, never a production backup.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier

import psycopg
from psycopg.types.json import Jsonb

from tools.validate_phase075_league import (
    connect, initialize, open_and_results, prepare_close, rpc, value,
)


def review(conn, v):
    return value(conn, "select public.championship_context(%s)", (v["sid"],))


def lifecycle(conn, request):
    return value(conn, "select public.api_admin_season_lifecycle(%s::jsonb)", (Jsonb(request),))


def decision(conn, v, method="total_actual_deaths", key="076-confirm", **extra):
    current = review(conn, v)
    return dict(
        operation="championship_tiebreak", actor_trainer_id=v["tid"],
        season_id=v["sid"], idempotency_key=key,
        body=dict(expected_revision=current["setup_revision"], input_hash=current["input_hash"],
                  method=method, confirmation=True,
                  reason="Explicit administrator confirmation from isolated championship evidence", **extra),
    )


def battle(a, b, winner):
    return dict(player_a_id=a, player_b_id=b, winner_id=winner,
                played_at=(datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat(),
                evidence="Synthetic recorded championship-only 1v1 outcome; not a normal League match")


def confirm_counts(conn, v, index, actual, wipes=0):
    if wipes:
        conn.execute("""update public.season_player_stats set revived_after_wipe=%s,
                     metadata='{"wipe_revision":1}'::jsonb where season_player_id=%s""",
                     (wipes, v["players"][index]))
    return value(conn, f"select pg_temp.confirm_{index}(%s,%s,%s)", (actual, wipes, actual))


def closed_fixture(conn, *, wins=(3, 3, 2, 1, 1), actual=(0, 0, 0, 0, 0), wipes=(0, 0, 0, 0, 0)):
    v = initialize(conn, total=1)
    for index, count in enumerate(actual):
        confirm_counts(conn, v, index, count, wipes[index])
    open_and_results(conn, v, v["day1"], 1, list(wins))
    rpc(conn, "api_admin_matchday", prepare_close(conn, v, v["day1"], "076-close-fixture"))
    return v


def sporting_footprint(conn, v):
    """Every fact a title-only decision must leave exactly unchanged."""
    return value(conn, """select jsonb_build_object(
      'coins',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.coin_transactions x where x.season_id=%s),
      'purchases',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.purchases x where x.season_id=%s),
      'matches',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.matches x where x.season_id=%s),
      'snapshots',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.matchday_snapshots x where x.season_id=%s),
      'revisions',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.matchday_snapshot_revisions x where x.season_id=%s),
      'death_events',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.league_death_events x join public.season_players p on p.id=x.season_player_id where p.season_id=%s),
      'death_resolutions',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.league_death_resolutions x join public.season_players p on p.id=x.season_player_id where p.season_id=%s),
      'death_snapshots',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.matchday_death_snapshots x where x.season_id=%s),
      'points',(select coalesce(jsonb_agg(to_jsonb(x) order by x.season_player_id),'[]') from public.public_sanctioned_points x where x.season_id=%s))""",
      (v["sid"],) * 9)


def decision_footprint(conn, v):
    return value(conn, """select jsonb_build_object(
      'resolutions',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.league_championship_resolutions x where x.season_id=%s),
      'receipts',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.admin_operation_receipts x where x.season_id=%s),
      'events',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.activity_events x where x.season_id=%s),
      'setup',(select to_jsonb(x) from public.season_admin_state x where x.season_id=%s),
      'final',(select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]') from public.league_finalizations x where x.season_id=%s))""",
      (v["sid"],) * 5)


def rejected(conn, v, action, *, statuses=("PT409",), messages=None):
    before = sporting_footprint(conn, v), decision_footprint(conn, v)
    try:
        with conn.transaction():
            action()
    except psycopg.Error as exc:
        assert exc.sqlstate in statuses, (exc.sqlstate, str(exc))
        if messages is not None:
            assert str(exc).splitlines()[0] in messages, str(exc)
    else:
        raise AssertionError("Unsafe title decision was accepted")
    assert (sporting_footprint(conn, v), decision_footprint(conn, v)) == before, "Failed title operation had partial effects"


def resolution_rows(conn, v):
    return conn.execute("select resolution_type,outcome,winner_season_player_id,actor_trainer_id,decision_json "
                        "from public.league_championship_resolutions where season_id=%s order by created_at,id", (v["sid"],)).fetchall()


def revival_case(conn):
    v = initialize(conn, total=1)
    value(conn, "select pg_temp.observe_0(%s::integer[])", ([1, 2, 3],))
    confirm_counts(conn, v, 0, 3)
    for entity in v["entities"][:3]:
        value(conn, "select pg_temp.normal_revive(%s::uuid)", (entity,))
    value(conn, "select pg_temp.observe_0('{}'::integer[])")
    value(conn, "select pg_temp.observe_1(%s::integer[])", ([1, 2, 3],))
    for index in range(1, 5): confirm_counts(conn, v, index, 3 if index == 1 else 0)
    assert value(conn, "select public.league_death_totals(%s)->>'actual_deaths'", (v["players"][0],)) == "3"
    open_and_results(conn, v, v["day1"], 1, [3, 3, 2, 1, 1])
    rpc(conn, "api_admin_matchday", prepare_close(conn, v, v["day1"], "076-comodin-close"))
    current = review(conn, v)
    players = {p["season_player_id"]: p for p in current["players"]}
    assert players[v["players"][0]]["actual_deaths"] == players[v["players"][1]]["actual_deaths"] == 3
    assert Decimal(players[v["players"][0]]["total_points"]) == Decimal("2.7")
    before = sporting_footprint(conn, v)
    lifecycle(conn, decision(conn, v, key="076-comodin-confirm"))
    current = review(conn, v)
    assert current["state"] == "battle_required" and current["champion_trainer_id"] is None
    assert set(current["tied_player_ids"]) == set(v["players"][:2])
    assert sporting_footprint(conn, v) == before
    return "Three actual comodin revivals leave3historicaldeaths: emptycurrentbox cannot defeat equal3deaths still in the other box; recordedbattle required"


def validate(pg):
    checks = []
    # Same adjusted units (10) and NET points, different actual history (5 vs10).
    with connect(pg) as conn:
        try:
            v = closed_fixture(conn, actual=(5, 10, 10, 0, 0), wipes=(5, 0, 0, 0, 0))
            initial = review(conn, v)
            assert initial["state"] == "tiebreak_required" and initial["champion_trainer_id"] is None, initial
            assert set(initial["tied_player_ids"]) == set(v["players"][:2])
            players = {p["season_player_id"]: p for p in initial["players"]}
            assert players[v["players"][0]]["actual_deaths"] == 5
            assert players[v["players"][1]]["actual_deaths"] == 10
            assert Decimal(players[v["players"][0]]["total_points"]) == Decimal("2")
            # A newer current box/ledger cannot alter the official closing's history.
            value(conn, "select pg_temp.observe_0(%s::integer[])", ([1, 2, 3],))
            latest = value(conn, "select public.league_death_totals(%s)", (v["players"][0],))
            assert latest["actual_deaths"] == 8
            assert next(p for p in review(conn, v)["players"] if p["season_player_id"] == v["players"][0])["actual_deaths"] == 5
            before = sporting_footprint(conn, v)
            req = decision(conn, v)
            missing = deepcopy(req); missing["body"]["confirmation"] = False
            rejected(conn, v, lambda: lifecycle(conn, missing), statuses=("PT422", "PT409"))
            stale = deepcopy(req); stale["body"]["input_hash"] = "0" * 64
            rejected(conn, v, lambda: lifecycle(conn, stale))
            stale = deepcopy(req); stale["body"]["expected_revision"] += 1
            rejected(conn, v, lambda: lifecycle(conn, stale))
            trainer = deepcopy(req); trainer["actor_trainer_id"] = v["trainers"][1]
            rejected(conn, v, lambda: lifecycle(conn, trainer), statuses=("PT403",), messages={"admin_required"})
            def disabled_actor():
                conn.execute("reset role")
                conn.execute("update public.trainers set globally_enabled=false where id=%s", (v["tid"],))
                conn.execute("set local role service_role")
                lifecycle(conn, req)
            rejected(conn, v, disabled_actor, statuses=("PT403",), messages={"trainer_disabled"})
            receipt = lifecycle(conn, req)
            assert receipt["operation"] == "championship_tiebreak" and receipt["state"] == "active"
            assert receipt["actor_trainer_id"] == v["tid"] and receipt["replayed"] is False
            assert lifecycle(conn, req)["replayed"] is True
            assert sporting_footprint(conn, v) == before
            resolved = review(conn, v)
            assert resolved["state"] == "ready" and resolved["champion_trainer_id"] == v["trainers"][0], resolved
            assert resolved["resolution_type"] == "total_actual_deaths"
            rows = resolution_rows(conn, v)
            assert len(rows) == 1 and rows[0][0:2] == ("total_actual_deaths", "resolved")
            assert str(rows[0][2]) == v["players"][0] and str(rows[0][3]) == v["tid"]
            facts = rows[0][4]
            assert facts["method"] == "total_actual_deaths" and facts["source_snapshot_revision_id"]
            assert set(facts["candidate_player_ids"]) <= set(initial["tied_player_ids"])
            assert {p["season_player_id"] for p in facts["participants"]} >= set(initial["tied_player_ids"])
            changed = deepcopy(req); changed["body"]["reason"] += " changed"
            rejected(conn, v, lambda: lifecycle(conn, changed), messages={"idempotency_conflict"})
            # Finalization freezes method and champion; later confirmation cannot reopen it.
            finish = dict(operation="finish", actor_trainer_id=v["tid"], season_id=v["sid"], idempotency_key="076-finish",
                          body=dict(expected_revision=resolved["setup_revision"], input_hash=resolved["input_hash"]))
            lifecycle(conn, finish)
            frozen = review(conn, v)
            assert frozen["state"] == "frozen" and frozen["resolution_type"] == "total_actual_deaths"
            assert frozen["champion_trainer_id"] == v["trainers"][0]
            assert lifecycle(conn, req)["replayed"] is True
            different = deepcopy(req); different["idempotency_key"] = "076-after-finish"
            rejected(conn, v, lambda: lifecycle(conn, different))
            assert review(conn, v) == frozen and sporting_footprint(conn, v) == before
            checks.append("Actual075 history selects5wipe deaths over10ordinary despite equal10penaltyunits; explicit/admin/auth/stale/CAS/idempotency/frozen protections; points/wins/deaths/rewards unchanged")
        finally:
            conn.rollback()

    # Three NET leaders, two with the same lowest actual history; no invented champion.
    with connect(pg) as conn:
        try:
            v = closed_fixture(conn, wins=(3, 3, 3, 1, 0), actual=(5, 5, 10, 0, 0), wipes=(5, 5, 0, 0, 0))
            initial = review(conn, v)
            assert set(initial["tied_player_ids"]) == set(v["players"][:3])
            before = sporting_footprint(conn, v)
            req = decision(conn, v, key="076-equal-deaths")
            receipt = lifecycle(conn, req)
            assert receipt["state"] == "active" and lifecycle(conn, req)["replayed"] is True
            pending = review(conn, v)
            assert pending["state"] == "battle_required" and pending["champion_trainer_id"] is None, pending
            assert pending["tiebreak_method"] == "total_actual_deaths"
            assert set(pending["tied_player_ids"]) == set(v["players"][:2])
            rows = resolution_rows(conn, v)
            assert len(rows) == 1 and rows[0][0:3] == ("total_actual_deaths", "battle_required", None)
            assert sporting_footprint(conn, v) == before
            wrong = decision(conn, v, "championship_1v1", key="076-excluded-contender",
                             winner_season_player_id=v["players"][2], battles=[battle(v["players"][0], v["players"][2], v["players"][2])])
            rejected(conn, v, lambda: lifecycle(conn, wrong))
            req = decision(conn, v, "championship_1v1", key="076-recorded-battle",
                           winner_season_player_id=v["players"][1], battles=[battle(v["players"][0], v["players"][1], v["players"][1])])
            lifecycle(conn, req)
            assert lifecycle(conn, req)["replayed"] is True
            resolved = review(conn, v)
            assert resolved["state"] == "ready" and resolved["champion_trainer_id"] == v["trainers"][1]
            assert resolved["resolution_type"] == "championship_1v1" and len(resolution_rows(conn, v)) == 2
            assert sporting_footprint(conn, v) == before
            checks.append("ThreewayNET tie -> confirmedactualdeaths narrows to2 -> recorded1v1 only; unresolvedchoice audited, no arbitrary rank or extra sporting effects")
        finally:
            conn.rollback()

    # Direct battle selection for three tied leaders: only unambiguous recorded evidence.
    with connect(pg) as conn:
        try:
            v = closed_fixture(conn, wins=(3, 3, 3, 1, 0))
            a, b, c = v["players"][:3]
            assert set(review(conn, v)["tied_player_ids"]) == {a, b, c}
            before = sporting_footprint(conn, v)
            bad = [
                [battle(a, b, a)],
                [battle(a, b, a), battle(b, c, b), battle(c, a, c)],
                [battle(a, b, a), battle(c, b, c)],
                [battle(a, b, a), battle(b, a, b), battle(b, c, b)],
                [battle(a, b, a), battle(a, v["players"][3], a)],
            ]
            for index, recorded in enumerate(bad):
                req = decision(conn, v, "championship_1v1", key=f"076-ambiguous-{index}", winner_season_player_id=a, battles=recorded)
                rejected(conn, v, lambda: lifecycle(conn, req), statuses=("PT409", "PT422"))
            # Direct helper guard: a unique undefeated root must not conceal a
            # cycle among the other contenders (A>B, B>C, C>D, D>B).
            d = v["players"][3]
            loser_cycle = [battle(a, b, a), battle(b, c, b), battle(c, d, c), battle(d, b, d)]
            rejected(conn, v, lambda: value(conn,
                "select public.championship_verify_battles(%s::jsonb,%s,%s::jsonb)",
                (Jsonb([a, b, c, d]), a, Jsonb(loser_cycle))), messages={"championship_battle_ambiguous"})
            recorded = [battle(a, b, a), battle(b, c, b)]
            req = decision(conn, v, "championship_1v1", key="076-direct-multiway", winner_season_player_id=a, battles=recorded)
            lifecycle(conn, req)
            resolved = review(conn, v)
            assert resolved["champion_trainer_id"] == v["trainers"][0] and resolved["resolution_type"] == "championship_1v1"
            assert sporting_footprint(conn, v) == before
            assert resolution_rows(conn, v)[0][4]["battles"]
            checks.append("Multiwayactual1v1 proof accepted only for a unique undefeated winner covering all candidates; incomplete/cyclic/disconnected/repeated/foreign results rejected atomically")
        finally:
            conn.rollback()

    # A unique NET winner has no title decision, and unfinished competition has none.
    with connect(pg) as conn:
        try:
            checks.append(revival_case(conn))
        finally:
            conn.rollback()
    with connect(pg) as conn:
        try:
            v = closed_fixture(conn, wins=(4, 3, 2, 1, 0))
            current = review(conn, v)
            assert current["state"] == "ready" and current["resolution_type"] == "unique_points"
            rejected(conn, v, lambda: lifecycle(conn, decision(conn, v)))
            assert not value(conn, "select has_function_privilege('anon','public.api_admin_season_lifecycle(jsonb)','execute')")
            assert not value(conn, "select has_function_privilege('authenticated','public.api_admin_season_lifecycle(jsonb)','execute')")
            checks.append("UniqueNET title never offers or accepts a tiebreak; browser roles cannot execute lifecycle RPC directly")
        finally:
            conn.rollback()
    with connect(pg) as conn:
        try:
            v = initialize(conn, total=1)
            for index in range(5): confirm_counts(conn, v, index, 0)
            open_and_results(conn, v, v["day1"], 1, [3, 3, 3, 1, 0])
            current = review(conn, v)
            assert current["state"] == "incomplete"
            req = decision(conn, v); req["body"]["input_hash"] = "0" * 64
            rejected(conn, v, lambda: lifecycle(conn, req), statuses=("PT409", "PT422"))
            checks.append("Completednormalmatches without official finalclosure cannot decide the championship")
        finally:
            conn.rollback()
    return "PASS: " + "; ".join(checks)


def validate_concurrency(pg):
    """Dedicated disposable cluster only: commits a synthetic fixture for two clients."""
    with connect(pg) as conn:
        v = closed_fixture(conn, actual=(5, 10, 10, 0, 0), wipes=(5, 0, 0, 0, 0))
        req = decision(conn, v, key="076-concurrent-title")
        before = sporting_footprint(conn, v)
    barrier = Barrier(2)
    def run():
        with connect(pg) as conn:
            conn.execute("set local role service_role")
            barrier.wait(timeout=15)
            return lifecycle(conn, req)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    assert len({r["operation_id"] for r in results}) == len({r["event_id"] for r in results}) == 1
    with connect(pg) as conn:
        conn.execute("set local role service_role")
        assert len(resolution_rows(conn, v)) == 1
        assert sporting_footprint(conn, v) == before
        assert review(conn, v)["champion_trainer_id"] == v["trainers"][0]
    return "PASS: 2 simultaneous same-key confirmations -> one audited decision/one receipt replay; all sporting facts unchanged"
