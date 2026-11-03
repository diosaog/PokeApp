"""Ordinary matchday operations by non-admin League participants, on real RPCs.

Proves the season-scoped participant contract (041 league_operation_principal,
034 api_participant_matchday, 075 death freeze) that the League tab now uses:
any active participant opens, records results and closes; outsiders, inactive
or disabled trainers cannot; exceptional operations stay administrator-only;
replays and second attempts are safe. Synthetic 075 fixture on a disposable
PostgreSQL; validate() always rolls back. No remote connections or saves.

    python -m tools.validate_player_matchdays --port <free port>
"""

from pathlib import Path
from uuid import uuid4
import argparse
import os

import psycopg
from psycopg.types.json import Jsonb

from app.application.matchdays import plan_close
from tools.validate_phase075_league import (
    confirm,
    connect,
    initialize,
    rpc,
    value,
    winners,
)


class _Rollback(Exception):
    pass


def envelope(actor, v, day, key, body):
    return dict(
        actor_trainer_id=actor,
        season_id=v["sid"],
        resource_id=day,
        idempotency_key=key,
        body=body,
    )


def participant(conn, operation, request):
    return value(
        conn,
        "select public.api_participant_matchday(%s::jsonb)",
        (Jsonb(dict(operation=operation, request=request)),),
    )


def rejected(conn, call, *codes):
    """The call fails with one of `codes`; its effects roll back to a savepoint."""
    try:
        with conn.transaction():
            call()
    except psycopg.Error as exc:
        message = exc.diag.message_primary
        assert message in codes, (codes, exc.sqlstate, message)
        return message
    raise AssertionError(f"accepted, expected {codes}")


def close_request(conn, actor, v, day, key):
    revision = value(
        conn, "select results_revision from public.matchdays where id=%s", (day,)
    )
    request = envelope(actor, v, day, key, dict(expected_results_revision=revision))
    context = rpc(
        conn,
        "api_admin_matchday_context",
        dict(operation="close", request=request),
    )
    if "receipt" in context:
        return dict(operation="close", request=request), context["receipt"]
    plan = plan_close(context["context"], None)
    return (
        dict(
            operation="close",
            request=request,
            input_hash=context["input_hash"],
            plan=plan,
        ),
        None,
    )


def validate(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = initialize(conn, total=2)
            admin, players = v["tid"], v["trainers"]
            p1, p2, p3, p4 = players[1:5]
            assert not any(
                value(conn, "select is_admin from public.trainers where id=%s", (t,))
                for t in (p1, p2, p3, p4)
            )
            assert value(
                conn, "select is_admin from public.trainers where id=%s", (admin,)
            )
            conn.execute("reset role")
            outsider = str(uuid4())
            conn.execute(
                "insert into public.trainers(id,display_name,slug,is_admin,auth_user_id)"
                " values(%s,'Outsider','outsider-'||%s,false,gen_random_uuid())",
                (outsider, outsider),
            )
            conn.execute("set local role service_role")
            for index in range(5):
                confirm(conn, index, 0, 0)
            day = str(
                value(
                    conn,
                    "select current_matchday_id from public.seasons where id=%s",
                    (v["sid"],),
                )
            )
            revision = value(
                conn, "select revision from public.matchdays where id=%s", (day,)
            )
            open_body = dict(expected_revision=revision)

            def open_as(actor, key):
                return rpc(
                    conn,
                    "api_admin_matchday",
                    dict(
                        operation="open",
                        request=envelope(actor, v, day, key, open_body),
                    ),
                )

            rejected(conn, lambda: open_as(outsider, "pm-open-out"), "participant_required")
            # An inactive participant and a disabled account: same refusal
            # paths the API maps to 403.
            try:
                with conn.transaction():
                    conn.execute("reset role")
                    conn.execute(
                        "update public.season_players set status='retired' where id=%s",
                        (v["players"][4],),
                    )
                    conn.execute("set local role service_role")
                    rejected(conn, lambda: open_as(p4, "pm-open-retired"), "participant_inactive")
                    raise _Rollback()
            except _Rollback:
                pass
            try:
                with conn.transaction():
                    conn.execute("reset role")
                    conn.execute(
                        "update public.trainers set globally_enabled=false where id=%s",
                        (p4,),
                    )
                    conn.execute("set local role service_role")
                    rejected(conn, lambda: open_as(p4, "pm-open-disabled"), "trainer_disabled")
                    raise _Rollback()
            except _Rollback:
                pass
            conn.execute("set local role service_role")
            # Exceptional lifecycle operations are not widened.
            rejected(
                conn,
                lambda: rpc(
                    conn,
                    "api_admin_matchday",
                    dict(
                        operation="cancel",
                        request=envelope(
                            p1, v, day, "pm-cancel", dict(open_body, reason="no")
                        ),
                    ),
                ),
                "admin_required",
            )
            checks.append("outsider/retired/disabled refused; cancel stays admin-only")

            opened = open_as(p1, "pm-open-1")
            assert opened["state"] == "open"
            assert open_as(p1, "pm-open-1")["replayed"] is True
            rejected(conn, lambda: open_as(p2, "pm-open-2"), "matchday_not_scheduled")
            frozen = value(
                conn,
                "select count(*) from public.matchday_death_snapshots where matchday_id=%s",
                (day,),
            )
            assert frozen == 5, frozen
            assert (
                str(value(
                    conn,
                    "select actor_trainer_id from public.activity_events"
                    " where type='MATCHDAY_ADMIN_OPEN' and payload->>'matchday_id'=%s",
                    (day,),
                ))
                == p1
            )
            checks.append("participant opened once (replay safe, 2nd open refused); 5 death snapshots frozen; actor audited")

            matches = conn.execute(
                "select id,player_a_id,player_b_id from public.matches"
                " where matchday_id=%s order by id",
                (day,),
            ).fetchall()
            expected = winners(v["players"], [4, 3, 2, 1, 0])
            results = [
                dict(
                    match_id=str(mid),
                    winner_season_player_id=expected[frozenset((str(a), str(b)))],
                )
                for mid, a, b in matches
            ]
            half = len(results) // 2
            stale = opened["results_revision"]

            def record(actor, key, rows, revision):
                return participant(
                    conn,
                    "results",
                    envelope(
                        actor,
                        v,
                        day,
                        key,
                        dict(expected_results_revision=revision, results=rows),
                    ),
                )

            rejected(
                conn,
                lambda: record(outsider, "pm-res-out", results[:1], stale),
                "participant_required",
            )
            first = record(p2, "pm-res-a", results[:half], stale)
            # A second participant working from the same old revision cannot
            # overwrite what was just recorded.
            contradicting = [
                dict(r, winner_season_player_id=next(
                    str(x) for x in (a, b) if str(x) != r["winner_season_player_id"]))
                for r, (_, a, b) in zip(results[:half], matches[:half])
            ]
            rejected(
                conn,
                lambda: record(p3, "pm-res-b", contradicting, stale),
                "stale_revision",
            )
            record(p3, "pm-res-c", results[half:], first["results_revision"])
            assert value(
                conn,
                "select count(*) from public.matches where matchday_id=%s and winner_id is null",
                (day,),
            ) == 0
            audited = value(
                conn,
                "select count(distinct actor_trainer_id) from public.activity_events"
                " where type='MATCHDAY_PARTICIPANT_RESULTS' and payload->>'matchday_id'=%s",
                (day,),
            )
            assert audited == 2, audited
            checks.append("results by two participants; stale contradicting write refused; each actor audited")

            rejected(
                conn,
                lambda: close_request(conn, outsider, v, day, "pm-close-out"),
                "participant_required",
            )
            rejected(
                conn,
                lambda: rpc(
                    conn,
                    "api_admin_matchday",
                    dict(
                        operation="correct",
                        request=envelope(p4, v, day, "pm-correct", dict(
                            expected_snapshot_revision=1, reason="no", results=results)),
                    ),
                ),
                "admin_required",
            )
            closing, _ = close_request(conn, p4, v, day, "pm-close-1")
            receipt = rpc(conn, "api_admin_matchday", closing)
            assert receipt["state"] == "closed"
            assert rpc(conn, "api_admin_matchday", closing)["replayed"] is True
            # The API's context step answers a replay of the identical request
            # with the stored receipt; reusing the key for other data is refused.
            cached = rpc(
                conn,
                "api_admin_matchday_context",
                dict(operation="close", request=closing["request"]),
            )
            assert cached["receipt"]["replayed"] is True
            rejected(
                conn,
                lambda: close_request(conn, p4, v, day, "pm-close-1"),
                "idempotency_conflict",
            )
            rejected(
                conn,
                lambda: rpc(conn, "api_admin_matchday", close_request(conn, p1, v, day, "pm-close-2")[0]),
                "already_closed",
                "matchday_not_open",
                "matchday_not_current",
                "stale_inputs",
            )
            payouts = value(
                conn,
                "select count(*) from public.coin_transactions where reward_matchday_id=%s",
                (day,),
            )
            assert payouts == 5, payouts
            assert value(
                conn,
                "select count(*) from public.matchday_snapshot_revisions where matchday_id=%s",
                (day,),
            ) == 1
            assert (
                str(value(
                    conn,
                    "select actor_trainer_id from public.activity_events"
                    " where type='MATCHDAY_ADMIN_CLOSE' and payload->>'matchday_id'=%s",
                    (day,),
                ))
                == p4
            )
            general = value(conn, "select public.league_general_read(%s)", (v["sid"],))
            assert len(general["rows"]) == 5
            checks.append("participant closed once (replay safe, 2nd close refused); 5 coin payouts; 1 snapshot; correct stays admin-only")
        finally:
            conn.rollback()
    return "PASS: " + "; ".join(checks)


def main():
    from tools.phase30_release_audit import SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pg-bin",
        type=Path,
        default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin",
    )
    parser.add_argument("--port", type=int, default=55611)
    parser.add_argument("--upto", type=int, default=999)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        migrations = sorted(
            (Path(__file__).resolve().parents[1] / "supabase/v2/migrations").glob(
                "*.sql"
            )
        )
        for migration in migrations:
            if int(migration.name[:3]) <= args.upto:
                pg.sql(migration.read_text(encoding="utf-8"))
        print(validate(pg))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
