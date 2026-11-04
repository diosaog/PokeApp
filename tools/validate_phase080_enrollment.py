"""Synthetic enrollment acceptance on a disposable loopback PostgreSQL only.

No production configuration, credentials, save files or network publications.
Each timing scenario rolls back; concurrency uses its own committed fixture.
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from tools.phase30_release_audit import SupabaseLikePG
from tools.validate_phase075_league import prepare_close
from tools.validate_phase079_all_vs_all import (
    as_owner,
    call,
    confirm_body,
    connect,
    death,
    initialize,
    observe,
    prepare,
    seed,
    value,
    wipe,
)
from tools.validate_player_matchdays import envelope, participant, rejected


def enrollment(conn, v, operation="preview", body=None, key=None, actor=None):
    request = {"actor_trainer_id": actor or v["admin"], "season_id": v["sid"]}
    if body is not None:
        request["body"] = body
    if key is not None:
        request["idempotency_key"] = key
    return call(
        conn,
        "api_admin_league_enrollment",
        {"operation": operation, "request": request},
    )


def entrant(conn):
    trainer = str(uuid4())
    as_owner(
        conn,
        "insert into public.trainers(id,display_name,slug,auth_user_id) values(%s,%s,%s,gen_random_uuid())",
        (trainer, "080 entrant " + trainer[:8], "080-" + trainer),
    )
    return trainer


def enroll(conn, v, trainer, key="enroll", preview=None):
    preview = preview or enrollment(conn, v)
    body = {"trainer_id": trainer, "preview_hash": preview["preview_hash"]}
    receipt = enrollment(conn, v, "confirm", body, key)
    assert enrollment(conn, v, "confirm", body, key)["replayed"]
    return str(receipt["resource_id"]), preview, body


def attach_entities(conn, v, pid):
    ids = [str(uuid4()) for _ in range(6)]
    for i, entity in enumerate(ids):
        as_owner(
            conn,
            "insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,identity_schema_version,candidate_key,initial_evidence)"
            " select %s,season_id,trainer_id,'unambiguous',1,%s,%s::jsonb from public.season_players where id=%s",
            (entity, str(i).ljust(64, "0"), json.dumps({"fixture": i}), pid),
        )
    as_owner(
        conn, "update public.season_players set dead_box_number=7 where id=%s", (pid,)
    )
    return ids


def baseline_originals(conn, v):
    for i, trainer in enumerate(v["trainers"]):
        observe(conn, v, i, [], 2)
        state = death(conn, v, trainer)
        death(conn, v, trainer, "confirm", confirm_body(state), "original-" + str(i))


def open_day(conn, v, day):
    revision = value(conn, "select revision from public.matchdays where id=%s", (day,))
    return call(
        conn,
        "api_admin_matchday",
        {
            "operation": "open",
            "request": envelope(
                v["trainers"][0], v, day, str(uuid4()), {"expected_revision": revision}
            ),
        },
    )


def results(conn, v, day, limit=None):
    matches = conn.execute(
        "select id,player_a_id,player_b_id from public.matches where matchday_id=%s and status='scheduled' order by player_a_id,player_b_id",
        (day,),
    ).fetchall()
    matches = matches if limit is None else matches[:limit]
    # A transitive tournament has distinct win counts and needs no tie fixtures.
    revision = value(
        conn, "select results_revision from public.matchdays where id=%s", (day,)
    )
    body = {
        "expected_results_revision": revision,
        "results": [
            {"match_id": str(m), "winner_season_player_id": str(min(a, b))}
            for m, a, b in matches
        ],
    }
    return call(
        conn,
        "api_admin_matchday",
        {
            "operation": "results",
            "request": envelope(v["admin"], v, day, str(uuid4()), body),
        },
    )


def close_day(conn, v, day):
    compatible = dict(v, tid=v["admin"])
    request = prepare_close(conn, compatible, day, str(uuid4()))
    return call(conn, "api_admin_matchday", request)


def balance(conn, pid):
    return value(
        conn,
        "select coalesce(sum(amount),0) from public.coin_transactions where season_player_id=%s",
        (pid,),
    )


def history(conn, v):
    # Structural equality, not counts: protects previous results, coins,
    # snapshots, original progress and death evidence across enrollment.
    return {
        table: value(
            conn,
            f"select coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),'[]'::jsonb) from public.{table} x where {where}",
            (v["sid"],),
        )
        for table, where in (
            ("matches", "season_id=%s"),
            ("matchday_snapshots", "season_id=%s"),
            ("matchday_death_snapshots", "season_id=%s"),
            ("team_locks", "season_id=%s"),
            ("coin_transactions", "season_id=%s"),
            (
                "league_death_events",
                "season_player_id in (select id from public.season_players where season_id=%s)",
            ),
        )
    }


def validate(pg):
    checks = []
    for timing in (
        "before-j1",
        "prepared-j1",
        "during-j1",
        "after-j1",
        "during-j2",
        "after-j2",
    ):
        with connect(pg) as conn:
            try:
                v = initialize(conn)
                # Three days allow an entrant after two closed days, before finality.
                as_owner(
                    conn,
                    "update public.season_config_versions set total_matchdays=3 where id=%s",
                    (v["config"],),
                )
                baseline_originals(conn, v)
                current = None
                if timing != "before-j1":
                    current = prepare(conn, v, v["trainers"][0])["matchday_id"]
                if timing in ("during-j1", "after-j1", "during-j2", "after-j2"):
                    open_day(conn, v, current)
                if timing in ("after-j1", "during-j2", "after-j2"):
                    results(conn, v, current)
                    close_day(conn, v, current)
                    current = str(
                        value(
                            conn,
                            "select current_matchday_id from public.seasons where id=%s",
                            (v["sid"],),
                        )
                    )
                if timing in ("during-j2", "after-j2"):
                    open_day(conn, v, current)
                    results(
                        conn, v, current, limit=3 if timing == "during-j2" else None
                    )
                if timing == "after-j2":
                    close_day(conn, v, current)
                    current = str(
                        value(
                            conn,
                            "select current_matchday_id from public.seasons where id=%s",
                            (v["sid"],),
                        )
                    )
                trainer = entrant(conn)
                previous = history(conn, v)
                preview = enrollment(conn, v)
                closed = {
                    "before-j1": 0,
                    "prepared-j1": 0,
                    "during-j1": 0,
                    "after-j1": 1,
                    "during-j2": 1,
                    "after-j2": 2,
                }[timing]
                assert (
                    preview["closed_matchdays"] == closed
                    and preview["initial_coins"] == closed * 10
                ), preview
                assert preview["initial_points"] == "0" and preview["new_matchups"] == 5
                pid, _, body = enroll(conn, v, trainer, preview=preview)
                assert balance(conn, pid) == closed * 10
                official = value(
                    conn, "select public.league_general_read(%s)", (v["sid"],)
                )
                assert (
                    next(r for r in official["rows"] if r["season_player_id"] == pid)[
                        "official_points"
                    ]
                    == "0"
                )
                assert not value(
                    conn, "select is_admin from public.trainers where id=%s", (trainer,)
                )
                after = history(conn, v)
                for table, rows in previous.items():
                    assert all(r in after[table] for r in rows), (
                        timing,
                        table,
                        "historical row rewritten",
                    )
                assert (
                    value(
                        conn,
                        "select count(*) from public.league_enrollments where season_id=%s",
                        (v["sid"],),
                    )
                    == 1
                )
                rejected(
                    conn,
                    lambda v=v, body=body: enrollment(
                        conn, v, "confirm", body, "another-key"
                    ),
                    "participant_exists",
                )
                attach_entities(conn, v, pid)
                as_owner(conn, "select pg_temp.observe(%s,'{}'::integer[],2)", (pid,))
                assert balance(conn, pid) == closed * 10, (
                    "initial badges must not pay 8 extra"
                )
                assert (
                    value(
                        conn,
                        "select count(*) from public.progress_reward_claims where season_player_id=%s and amount=0",
                        (pid,),
                    )
                    == 2
                )
                totals = value(conn, "select public.league_death_totals(%s)", (pid,))
                assert totals["known"] and totals["actual_deaths"] == 0, totals
                general = value(
                    conn, "select public.league_general_read(%s)", (v["sid"],)
                )
                assert (
                    Decimal(
                        next(
                            r for r in general["rows"] if r["season_player_id"] == pid
                        )["total_points"]
                    )
                    == 0
                )
                if current is None:
                    current = prepare(conn, v, trainer)["matchday_id"]
                assert (
                    value(
                        conn,
                        "select count(*) from public.matches where matchday_id=%s",
                        (current,),
                    )
                    == 15
                )
                if timing not in ("during-j1", "during-j2"):
                    open_day(conn, v, current)
                # New entrants need no preceding participation or historical day.
                assert (
                    value(
                        conn,
                        "select count(*) from public.matchday_death_snapshots where matchday_id=%s",
                        (current,),
                    )
                    == 6
                )
                rejected(
                    conn,
                    lambda v=v, current=current: close_day(conn, v, current),
                    "results_incomplete",
                )
                results(conn, v, current)
                close_day(conn, v, current)
                assert balance(conn, pid) == (closed + 1) * 10
                snapshot = value(
                    conn,
                    "select snapshot from public.matchday_snapshots where matchday_id=%s",
                    (current,),
                )
                assert len(snapshot["standings"]) == 6
                assert {p["code"] for p in snapshot["single_league_rewards"]} == {
                    "blindar_pokemon",
                    "robar_pokemon",
                }
                assert all(int(x["coins_awarded"]) == 10 for x in snapshot["standings"])
                checks.append(
                    timing
                    + ": exact coins, six-player pairs, preserved history, baseline, ordinary close/rewards"
                )
            finally:
                conn.rollback()
    return checks


def validate_boundaries(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            baseline_originals(conn, v)
            day = prepare(conn, v, v["trainers"][0])["matchday_id"]
            open_day(conn, v, day)
            trainer = entrant(conn)
            preview = enrollment(conn, v)
            body = {"trainer_id": trainer, "preview_hash": preview["preview_hash"]}
            for operation in ("preview", "confirm"):
                rejected(
                    conn,
                    lambda operation=operation: enrollment(
                        conn, v, operation, body, "bad-admin", v["trainers"][0]
                    ),
                    "admin_required",
                )
            rejected(
                conn,
                lambda: enrollment(
                    conn, v, "confirm", dict(body, initial_coins=999), "forged"
                ),
                "invalid_request",
            )
            no_login = str(uuid4())
            as_owner(
                conn,
                "insert into public.trainers(id,display_name,slug) values(%s,'No login',%s)",
                (no_login, no_login),
            )
            rejected(
                conn,
                lambda: enrollment(
                    conn, v, "confirm", dict(body, trainer_id=no_login), "no-login"
                ),
                "trainer_unavailable",
            )
            # A new result invalidates the preview even though reward counts stay equal.
            results(conn, v, day, 1)
            rejected(
                conn,
                lambda: enrollment(conn, v, "confirm", body, "stale"),
                "enrollment_preview_stale",
            )
            # Rollback proves that no membership, money, pair or event escapes a failure.
            before = history(conn, v)
            as_owner(
                conn,
                """create function pg_temp.fail_enrollment() returns trigger language plpgsql as $$
              begin if new.type='SEASON_ADMIN_ENROLL_PARTICIPANT' then raise exception '080 injected'; end if;return new;end $$;
              create trigger enrollment_failure before insert on public.activity_events for each row execute function pg_temp.fail_enrollment();""",
            )
            try:
                with conn.transaction():
                    enroll(conn, v, trainer, key="rollback")
            except psycopg.Error as exc:
                assert exc.diag.message_primary == "080 injected"
            else:
                raise AssertionError("failure injection not reached")
            assert history(conn, v) == before
            assert (
                value(
                    conn,
                    "select count(*) from public.league_enrollments where season_id=%s",
                    (v["sid"],),
                )
                == 0
            )
            as_owner(conn, "drop trigger enrollment_failure on public.activity_events")
            pid, _, original_body = enroll(conn, v, trainer)
            rejected(
                conn,
                lambda: enrollment(
                    conn,
                    v,
                    "confirm",
                    dict(original_body, trainer_id=v["outsider"]),
                    "enroll",
                ),
                "idempotency_conflict",
            )
            attach_entities(conn, v, pid)
            as_owner(conn, "select pg_temp.observe(%s,array[1,2],2)", (pid,))
            first = value(conn, "select public.league_death_totals(%s)", (pid,))
            assert (
                first["known"]
                and first["actual_deaths"] == 0
                and first["raw_recorded_deaths"] == 2
            ), first
            frozen = value(
                conn,
                "select to_jsonb(s) from public.matchday_death_snapshots s where matchday_id=%s and season_player_id=%s",
                (day, pid),
            )
            assert frozen["segment_deaths"] == 0
            for dead, badges, expected in (
                ([1, 2], 2, 0),
                ([1, 2, 3], 3, 1),
                ([1, 2, 3, 4], 3, 2),
                ([2, 3, 4], 3, 2),
                ([1, 2, 3, 4], 3, 2),
            ):
                as_owner(conn, "select pg_temp.observe(%s,%s,%s)", (pid, dead, badges))
                now = value(conn, "select public.league_death_totals(%s)", (pid,))
                assert now["known"] and now["actual_deaths"] == expected, now
            assert balance(conn, pid) == 4, "only the genuinely new third badge pays"
            assert (
                value(
                    conn,
                    "select to_jsonb(s) from public.matchday_death_snapshots s where matchday_id=%s and season_player_id=%s",
                    (day, pid),
                )
                == frozen
            )
            # One real wipe replaces one ordinary -0.1 by -0.2, never double charged.
            extended = dict(v, players=[pid], trainers=[trainer])
            wipe(conn, extended, 0, 1, "entrant-wipe")
            own = death(conn, v, trainer)
            assert own["can_confirm"] and own["proposed"]["actual_deaths"] == 2, own
            death(
                conn, v, trainer, "confirm", confirm_body(own), "entrant-wipe-confirm"
            )
            assert (
                value(
                    conn,
                    "select public.league_death_totals(%s)->>'death_penalty_tenths'",
                    (pid,),
                )
                == "3"
            )
            # Administrative historical review must also respect the explicit
            # enrollment baseline instead of charging its old occupants again.
            admin_request = {
                "actor_trainer_id": v["admin"],
                "season_id": v["sid"],
                "resource_id": pid,
            }
            state = call(
                conn,
                "api_admin_death_history",
                {"operation": "state", "request": admin_request},
            )
            call(
                conn,
                "api_admin_death_history",
                {
                    "operation": "reconcile",
                    "request": {
                        **admin_request,
                        "idempotency_key": "enrollment-admin-audit",
                        "body": {
                            "actual_deaths": 2,
                            "wipe_deaths": 1,
                            "segment_deaths": 0,
                            "expected_revision": state["revision"],
                            "source_sha256": state["source_sha256"],
                            "revived_entity_ids": [],
                            "reason": "Synthetic enrollment history review",
                            "evidence": "Two pre-baseline occupants retained, two later actual deaths.",
                        },
                    },
                },
            )
            # Exact same source events still exist; the baseline is explicit audit data.
            assert (
                value(
                    conn,
                    "select cardinality(baseline_event_ids) from public.league_enrollments where season_player_id=%s",
                    (pid,),
                )
                == 2
            )
            assert (
                value(
                    conn,
                    "select count(*) from public.activity_events where season_id=%s and type='LEAGUE_ENROLLMENT_DEATH_BASELINE'",
                    (v["sid"],),
                )
                == 1
            )
            # The current day supports a normal Team Lock and the existing one-row outbox.
            source = conn.execute(
                "select f.id,f.sha256,ps.id,ps.payload from public.season_players sp join public.save_files f on f.id=sp.current_save_file_id join public.parsed_saves ps on ps.save_file_id=f.id where sp.id=%s",
                (pid,),
            ).fetchone()
            team = [{"species": s["pokemon"]["species"]} for s in source[3]["party"]]

            def lock():
                return value(
                    conn,
                    "select id from public.api_upsert_team_lock(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        v["sid"],
                        day,
                        trainer,
                        pid,
                        source[0],
                        source[1],
                        source[2],
                        Jsonb(source[3]),
                        Jsonb(team),
                        Jsonb(team),
                    ),
                )

            locked = str(lock())
            team[0] = {"species": "Pokémon #1"}
            assert str(lock()) == locked
            assert (
                value(
                    conn,
                    "select count(*) from public.discord_announcements where event_key=%s",
                    ("team_locked:" + locked,),
                )
                == 1
            )
            assert (
                value(
                    conn,
                    "select revision from public.discord_announcements where event_key=%s",
                    ("team_locked:" + locked,),
                )
                == 2
            )
            match = str(
                value(
                    conn,
                    "select id from public.matches where matchday_id=%s and %s in(player_a_id,player_b_id) and status='scheduled' order by id limit 1",
                    (day, pid),
                )
            )
            revision = value(
                conn,
                "select results_revision from public.matchdays where id=%s",
                (day,),
            )
            participant(
                conn,
                "results",
                envelope(
                    trainer,
                    v,
                    day,
                    "entrant-real-result",
                    {
                        "expected_results_revision": revision,
                        "results": [
                            {"match_id": match, "winner_season_player_id": pid}
                        ],
                    },
                ),
            )
            general = value(conn, "select public.league_general_read(%s)", (v["sid"],))
            live_row = next(
                row for row in general["rows"] if row["season_player_id"] == pid
            )
            assert live_row["normal_wins"] == 1 and Decimal(
                live_row["total_points"]
            ) == Decimal("0.7"), live_row
            checks.extend(
                [
                    "admin/ownership/strict body/stale preview/idempotency guards",
                    "atomic rollback of the whole enrollment",
                    "audited initial dead observations preserved; future actual deaths and event deduplication",
                    "first two badges pay zero, third badge pays four once",
                    "wipe = ordinary + replacement rate, unchanged frozen progression",
                    "entrant Team Lock on active day: one outbox row, replacement edits",
                    "entrant records a normal victory as a participant: +1 minus 0.3 actual/wipe penalties = 0.7 NET",
                ]
            )
        finally:
            conn.rollback()
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            # A different common reward is authoritative, never a universal 10.
            as_owner(
                conn,
                "update public.season_config_versions set coin_rewards_json=(select jsonb_object_agg(i::text,17) from generate_series(1,5) i) where id=%s",
                (v["config"],),
            )
            baseline_originals(conn, v)
            day = prepare(conn, v, v["trainers"][0])["matchday_id"]
            open_day(conn, v, day)
            results(conn, v, day)
            close_day(conn, v, day)
            trainer = entrant(conn)
            pid, preview, _ = enroll(conn, v, trainer)
            assert preview["initial_coins"] == 17 and balance(conn, pid) == 17
            assert (
                value(
                    conn,
                    "select count(*) from public.participant_memberships_at(%s,1) where season_player_id=%s",
                    (v["sid"], pid),
                )
                == 0
            )
            rejected(
                conn,
                lambda: participant(
                    conn, "state", envelope(trainer, v, day, "old-day", {})
                ),
                "participant_ineligible",
            )
            attach_entities(conn, v, pid)
            as_owner(conn, "select pg_temp.observe(%s,'{}'::integer[],2)", (pid,))
            current = str(
                value(
                    conn,
                    "select current_matchday_id from public.seasons where id=%s",
                    (v["sid"],),
                )
            )
            open_day(conn, v, current)
            results(conn, v, current)
            close_day(conn, v, current)
            rejected(
                conn, lambda: enrollment(conn, v), "enrollment_championship_closed"
            )
            as_owner(
                conn,
                "update public.seasons set status='finished',finished_at=clock_timestamp() where id=%s",
                (v["sid"],),
            )
            rejected(conn, lambda: enrollment(conn, v), "season_not_active")
            checks.append(
                "configurable 17-coin reward; no retroactive eligibility; final championship/finished season refused"
            )
        finally:
            conn.rollback()
    with connect(pg) as conn:
        # Browser roles cannot access commands, enrollment sources or new helpers.
        for role in ("anon", "authenticated"):
            assert not value(
                conn,
                "select has_function_privilege(%s,'public.api_admin_league_enrollment(jsonb)','execute')",
                (role,),
            )
            assert not value(
                conn,
                "select has_table_privilege(%s,'public.league_enrollments','select')",
                (role,),
            )
        checks.append("private enrollment table and service-only RPC/helper ACLs")
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            trainer = entrant(conn)
            pid, _, _ = enroll(conn, v, trainer)
            attach_entities(conn, v, pid)
            source, _ = seed()
            observer = source[
                source.index("create or replace function pg_temp.observe") :
            ]
            assert "'champion_defeated',null" in observer
            conn.execute("reset role")
            conn.execute(
                observer.replace("'champion_defeated',null", "'champion_defeated',true")
            )
            conn.execute("select pg_temp.observe(%s,'{}'::integer[],8)", (pid,))
            conn.execute("set local role service_role")
            assert balance(conn, pid) == 0
            assert (
                value(
                    conn,
                    "select count(*) from public.progress_reward_claims where season_player_id=%s and amount=0",
                    (pid,),
                )
                == 9
            )
            conn.execute("reset role")
            conn.execute("select pg_temp.observe(%s,'{}'::integer[],8)", (pid,))
            conn.execute("set local role service_role")
            assert balance(conn, pid) == 0
            checks.append(
                "eight initial badges plus existing championship: nine zero-value claims; repeated sync pays nothing"
            )
        finally:
            conn.rollback()
    return checks


def validate_concurrency(pg):
    checks = []
    with connect(pg) as conn:
        v = initialize(conn)
        as_owner(
            conn,
            "update public.season_config_versions set total_matchdays=3 where id=%s",
            (v["config"],),
        )
        baseline_originals(conn, v)
        first = prepare(conn, v, v["trainers"][0])["matchday_id"]
        open_day(conn, v, first)
        results(conn, v, first)
        close_day(conn, v, first)
        trainer = entrant(conn)
        preview = enrollment(conn, v)
        body = {"trainer_id": trainer, "preview_hash": preview["preview_hash"]}
        conn.commit()

    def race(keys):
        barrier = Barrier(len(keys))

        def run(key):
            with connect(pg) as conn:
                conn.execute("set role service_role")
                barrier.wait(timeout=20)
                try:
                    answer = enrollment(conn, v, "confirm", body, key)
                    conn.commit()
                    return answer
                except psycopg.Error as exc:
                    conn.rollback()
                    return exc.diag.message_primary

        with ThreadPoolExecutor(max_workers=len(keys)) as pool:
            return list(pool.map(run, keys))

    answers = race(["concurrent"] * 3)
    assert all(isinstance(x, dict) for x in answers), answers
    assert sum(not x["replayed"] for x in answers) == 1, answers
    with connect(pg) as conn:
        assert (
            value(
                conn,
                "select count(*) from public.league_enrollments where season_id=%s",
                (v["sid"],),
            )
            == 1
        )
        assert (
            value(
                conn,
                "select count(*) from public.activity_events where season_id=%s and type='SEASON_ADMIN_ENROLL_PARTICIPANT'",
                (v["sid"],),
            )
            == 1
        )
        assert (
            value(
                conn,
                "select count(*) from public.season_players where season_id=%s and trainer_id=%s",
                (v["sid"], trainer),
            )
            == 1
        )
        assert (
            value(
                conn,
                "select count(*) from public.coin_transactions where season_id=%s and transaction_type='enrollment_credit'",
                (v["sid"],),
            )
            == 1
        )
        assert (
            value(
                conn,
                "select sum(amount) from public.coin_transactions where season_id=%s and transaction_type='enrollment_credit'",
                (v["sid"],),
            )
            == 10
        )
        assert (
            value(
                conn,
                "select count(*) from public.matches where matchday_id=(select current_matchday_id from public.seasons where id=%s)",
                (v["sid"],),
            )
            == 15
        )
    checks.append(
        "three concurrent exact retries: one participant, one audit event/receipt, one 10-coin credit, exactly five added pairs"
    )
    # Independent keys must also serialize at the season, not only receipt keys.
    with connect(pg) as conn:
        conn.execute("reset role")
        trainer = entrant(conn)
        preview = enrollment(conn, v)
        body = {"trainer_id": trainer, "preview_hash": preview["preview_hash"]}
        conn.commit()
    answers = race(["independent-1", "independent-2"])
    assert (
        sum(isinstance(x, dict) for x in answers) == 1
        and "participant_exists" in answers
    ), answers
    checks.append("different concurrent keys: one enrollment; duplicate refused")
    # A close and an enrollment share the season lock and cannot both commit
    # previews of the old roster/day. The loser must obtain a fresh preview.
    with connect(pg) as conn:
        conn.execute("set role service_role")
        fresh = v
        source, _ = seed()
        conn.execute("reset role")
        conn.execute(
            source[source.index("create or replace function pg_temp.observe") :]
        )
        conn.execute("set local role service_role")
        for (pid,) in conn.execute(
            "select season_player_id::text from public.league_enrollments where season_id=%s",
            (v["sid"],),
        ).fetchall():
            attach_entities(conn, v, pid)
            as_owner(conn, "select pg_temp.observe(%s,'{}'::integer[],2)", (pid,))
        day = str(
            value(
                conn,
                "select current_matchday_id from public.seasons where id=%s",
                (v["sid"],),
            )
        )
        open_day(conn, fresh, day)
        results(conn, fresh, day)
        trainer = entrant(conn)
        preview = enrollment(conn, fresh)
        close = prepare_close(conn, dict(fresh, tid=fresh["admin"]), day, "close-race")
        conn.commit()
    barrier = Barrier(2)

    def competing(operation):
        with connect(pg) as conn:
            conn.execute("set role service_role")
            barrier.wait(timeout=20)
            try:
                if operation == "close":
                    result = call(conn, "api_admin_matchday", close)
                else:
                    result = enrollment(
                        conn,
                        fresh,
                        "confirm",
                        {
                            "trainer_id": trainer,
                            "preview_hash": preview["preview_hash"],
                        },
                        "enroll-race",
                    )
                conn.commit()
                return result
            except psycopg.Error as exc:
                conn.rollback()
                return exc.diag.message_primary

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(competing, ("close", "enroll")))
    assert sum(isinstance(x, dict) for x in answers) == 1, answers
    assert any(
        x in ("stale_revision", "stale_inputs", "enrollment_preview_stale")
        for x in answers
        if isinstance(x, str)
    ), answers
    checks.append(
        "close vs enrollment: one operation commits; outdated competing preview rejected atomically"
    )
    return checks


def validate_regressions(pg):
    from tools.validate_false_death_corrections import validate as corrections
    from tools.validate_phase075_deaths import validate as deaths
    from tools.validate_phase075_guards import validate as guards
    from tools.validate_phase075_league import validate as league
    from tools.validate_phase075_league import validate_legacy, validate_two_divisions
    from tools.validate_phase076_championship import validate as championship
    from tools.validate_phase078_public_pastes import validate as pastes
    from tools.validate_phase079_all_vs_all import validate as all_vs_all
    from tools.validate_player_matchdays import validate as player_days

    return {
        name: check(pg)
        for name, check in (
            ("deaths_075", deaths),
            ("league_075", league),
            ("two_divisions", validate_two_divisions),
            ("legacy", validate_legacy),
            ("guards", guards),
            ("championship_076", championship),
            ("false_deaths_077", corrections),
            ("pastes_078", pastes),
            ("all_vs_all_079", all_vs_all),
            ("player_matchdays", player_days),
        )
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pg-bin",
        type=Path,
        default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin",
    )
    parser.add_argument("--port", type=int, default=55625)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--regressions", action="store_true")
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in sorted(
            (Path(__file__).resolve().parents[1] / "supabase/v2/migrations").glob(
                "*.sql"
            )
        ):
            if int(migration.name[:3]) <= 80:
                pg.sql(migration.read_text(encoding="utf-8"))
        report = {
            "timing": validate(pg),
            "boundaries": validate_boundaries(pg),
        }
        if args.regressions:
            report["regressions"] = validate_regressions(pg)
        report["concurrency"] = validate_concurrency(pg)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps(report, indent=2))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
