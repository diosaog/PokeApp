"""LOCAL ONLY: exact final points, certified title, audited BO3 and frozen Hall."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate(args, sql):
    client = LocalClient(args)
    ids = {role: str(uuid4()) for role in ("admin", "other", "owner")}
    readers = {
        role: LocalClient(args, "authenticated", uid) for role, uid in ids.items()
    }
    readers["anon"] = LocalClient(args, "anon")
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        pieces = [
            "select "
            + literal(t)
            + " as name,coalesce(jsonb_agg(to_jsonb(t) "
            + "order by to_jsonb(t)::text),'[]') as rows from public.\""
            + t
            + '" t'
            for t in tables
        ]
        return client.execute(
            "select jsonb_object_agg(name,rows) from ("
            + " union all ".join(pieces)
            + ") s"
        ).data

    baseline = snapshot()
    f = SeasonLifecycleFixtures(client, readers, ids, "phase10_5f_" + uuid4().hex)

    def review(sid):
        value = f.championship(sid)
        require(
            value["finalist_status"] == "OWNER_DECISION_REQUIRED", "Invented finalist"
        )
        return value

    def finish_body(sid):
        value = review(sid)
        return dict(
            expected_revision=value["setup_revision"], input_hash=value["input_hash"]
        )

    def bo3_body(sid, winner=None):
        value = review(sid)
        return dict(
            expected_revision=value["setup_revision"],
            input_hash=value["input_hash"],
            winner_season_player_id=winner or value["tied_player_ids"][-1],
            reason="Externally played BO3, recorded by the fixture administrator",
        )

    def reject_unchanged(action, *codes):
        before = snapshot()
        f.reject(action, *codes)
        require(
            snapshot() == before, "Rejected championship command changed public rows"
        )

    def season(*, total=1, targets=None, wipes=None, scores=(10, 9, 8, 1)):
        # Deactivate only this runner's already-completed synthetic seasons.
        for old in f.seasons:
            if f.rows("seasons", id=old)[0]["status"] == "active":
                client.table("seasons").update({"status": "draft"}).eq(
                    "id", old
                ).execute()
        sid = f.roster()
        cfg = f.config(sid)
        cfg.update(
            total_matchdays=total,
            movement_count=0,
            scoring={str(i): score for i, score in enumerate(scores, 1)},
            coin_rewards={str(i): i for i in range(1, 5)},
            rules=dict(team_lock_required=True, last_b_gets_steal=False),
        )
        cid = f.call("create_config", sid, cfg)["resource_id"]
        f.call("initial_divisions", sid, f.divisions_body(sid, cid))
        f.call(
            "prepare", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]}
        )
        f.call(
            "activate", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]}
        )
        players = f.players(sid)
        for i, player in enumerate(players):
            count = (wipes or [0] * 4)[i]
            if count:
                client.table("season_player_stats").update(
                    {"revived_after_wipe": count}
                ).eq("season_player_id", player["id"]).execute()
            if targets is not None:
                deduction = (
                    Decimal(scores[i])
                    - Decimal("0.4") * count
                    - Decimal(str(targets[i]))
                )
                require(
                    deduction >= 0, "Fixture target needs unapproved positive bonus"
                )
                if deduction:
                    f.insert(
                        "penalties",
                        dict(
                            season_id=sid,
                            trainer_id=player["trainer_id"],
                            penalty_type="points_reduction",
                            amount=0,
                            points_amount=str(deduction),
                        ),
                    )
        return sid, f.state(sid)["current_matchday_id"], players

    def close(sid, did, reverse=False):
        f.open(sid, did)
        state = f.ds(sid, did)
        results = [
            dict(
                match_id=m["id"],
                winner_season_player_id=(max if reverse else min)(
                    m["player_a_id"], m["player_b_id"]
                ),
            )
            for m in state["matches"]
        ]
        if results:
            f.md(
                "results",
                sid,
                did,
                dict(
                    expected_results_revision=state["results_revision"],
                    results=results,
                ),
            )
        f.close(sid, did)

    def completed(**kwargs):
        sid, did, players = season(**kwargs)
        close(sid, did)
        return sid, did, players

    def assert_points(sid, value):
        authoritative = {
            row["season_player_id"]: Decimal(str(row["sanctioned_points"]))
            for row in f.rows("public_sanctioned_points", season_id=sid)
        }
        for player in value["players"]:
            require(
                isinstance(player["total_points"], str),
                "Points crossed JSON as a float",
            )
            require(
                Decimal(player["total_points"])
                == authoritative[player["season_player_id"]],
                "Championship disagrees with official accumulated points",
            )

    def archive(sid):
        f.life("finish", sid, finish_body(sid))
        certificate = deepcopy(f.rows("league_finalizations", season_id=sid)[0])
        f.life("archive", sid)
        hall = f.rows("hall_of_fame_entries", season_id=sid)
        require(len(hall) == 1, "League Hall not exactly once")
        require(
            hall[0]["champion_trainer_id"]
            == certificate["title"]["champion_trainer_id"],
            "Hall champion differs from frozen certificate",
        )
        require(hall[0]["finalist_trainer_id"] is None, "Hall fabricated finalist")
        return certificate, hall[0]

    def inject(op, sid, body, table):
        before = snapshot()
        column = "id" if table == "seasons" else "season_id"
        sql(
            args,
            "create function public.phase10_5f_fail() returns trigger language plpgsql as $$ begin "
            + f"if new.{column}={literal(sid)}::uuid then raise exception 'local F injected' using errcode='P0001'; "
            + "end if; return new; end $$; "
            + f"create trigger phase10_5f_fail after insert or update on public.{table} "
            + "for each row execute function public.phase10_5f_fail();",
        )
        try:
            try:
                f.life(op, sid, dict(body))
            except PersistenceError as exc:
                require(
                    getattr(exc.__cause__, "code", None) == "P0001",
                    "Wrong injected error",
                )
            else:
                raise AssertionError(
                    "Injected failure did not abort " + op + "/" + table
                )
            require(snapshot() == before, "Partial commit after " + op + "/" + table)
        finally:
            sql(
                args,
                f"drop trigger phase10_5f_fail on public.{table}; drop function public.phase10_5f_fail();",
            )
        print("PASS F rollback " + op + "/" + table, flush=True)

    def invalid_frozen_source(sid, expression, *, missing_deaths=False):
        # Corrupt only this synthetic source inside a transaction that always
        # rolls back. The superuser-only local setting permits a negative test
        # of imported/corrupt historical data, never a product write bypass.
        before = snapshot()
        if missing_deaths:
            check = (
                "v=public.championship_context(" + literal(sid) + "::uuid); "
                "if v->>'state'<>'owner_decision_required' "
                "or v->>'champion_trainer_id' is not null "
                "or v->>'blocking_reason'<>'championship_deaths_unavailable' then "
                "raise exception 'Missing frozen deaths fabricated title'; end if;"
            )
        else:
            check = (
                "begin perform public.championship_context("
                + literal(sid)
                + "::uuid); "
                "raise exception 'Malformed frozen source accepted'; "
                "exception when sqlstate 'PT409' then "
                "if sqlerrm<>'historical_source_invalid' then raise; end if; end;"
            )
        sql(
            args,
            "begin; set local session_replication_role=replica; "
            "update public.matchday_snapshots set snapshot="
            + expression
            + " where season_id="
            + literal(sid)
            + "::uuid; "
            "update public.matchday_snapshot_revisions set snapshot="
            + expression
            + " where season_id="
            + literal(sid)
            + "::uuid; "
            "do $$ declare v jsonb; begin " + check + " end $$; rollback;",
        )
        require(
            snapshot() == before,
            "Negative corrupt-source transaction did not restore rows",
        )

    def missing_initial_history(sid):
        before = snapshot()
        sql(
            args,
            "begin; update public.seasons set metadata=metadata||"
            '\'{"initial_assignment_rule":"observed_deaths_v1"}\'::jsonb where id='
            + literal(sid)
            + "::uuid; do $$ begin begin perform public.championship_context("
            + literal(sid)
            + "::uuid); raise exception 'Modern initial history missing but accepted'; "
            "exception when sqlstate 'PT409' then if sqlerrm<>'historical_source_invalid' then raise; "
            "end if; end; end $$; rollback;",
        )
        require(
            snapshot() == before,
            "Missing-initial-history negative fixture changed rows",
        )

    try:
        f.setup()
        sid, did, players = season(total=2, scores=(10, 5, 3, 0))
        value = review(sid)
        require(
            value["state"] == "incomplete" and value["champion_trainer_id"] is None,
            "Incomplete competition fabricated title",
        )
        reject_unchanged(lambda: f.life("finish", sid), "COMPETITION_INCOMPLETE")
        cfg = f.config(sid)
        cfg.update(
            effective_from_matchday=2,
            total_matchdays=2,
            movement_count=0,
            scoring={"1": 6, "2": 5, "3": 3, "4": 0},
            rules=dict(team_lock_required=True, last_b_gets_steal=False),
        )
        f.call("create_config", sid, cfg)
        close(sid, did)
        did = f.state(sid)["current_matchday_id"]
        close(sid, did, reverse=True)
        value = review(sid)
        assert_points(sid, value)
        require(
            value["state"] == "ready"
            and value["resolution_type"] == "unique_points"
            and value["champion_trainer_id"] == players[0]["trainer_id"],
            "Final daily winner replaced accumulated champion",
        )
        daily = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"][
            "standings"
        ]
        require(
            min(daily, key=lambda r: r["position"])["trainer_id"] == players[1]["id"],
            "Fixture did not distinguish final-day leader",
        )
        missing_initial_history(sid)
        certificate, hall = archive(sid)
        require(
            hall["team_snapshot"] == [] and hall["source_team_lock_id"] is None,
            "Missing champion Team Lock fabricated",
        )
        require(
            certificate["title"]["champion_trainer_id"] == players[0]["trainer_id"],
            "Accumulated championship changed at finish",
        )
        f.passed(
            "F01 accumulated champion differs from final daily order; distinct close/finish/archive; no fabricated team/finalist"
        )

        sid, did, players = season(
            total=2, targets=("-0.25", "-1.50", "-2.00", "-3.00"), wipes=(2, 1, 0, 0)
        )
        close(sid, did)
        did = f.state(sid)["current_matchday_id"]
        close(sid, did)
        value = review(sid)
        assert_points(sid, value)
        totals = {
            p["season_player_id"]: Decimal(p["total_points"]) for p in value["players"]
        }
        require(
            totals[players[0]["id"]] == Decimal("9.75"),
            "Repeated death or sanction deduction",
        )
        frozen = deepcopy(value)
        client.table("season_player_stats").update({"revived_after_wipe": 999}).eq(
            "season_player_id", players[0]["id"]
        ).execute()
        client.table("penalties").update({"points_amount": "9999.99"}).eq(
            "season_id", sid
        ).execute()
        require(review(sid) == frozen, "Current deaths/sanctions rewrote frozen review")
        archive(sid)
        sid, did, players = completed(targets=("-0.01", "-0.10", "-0.20", "-0.30"))
        value = review(sid)
        assert_points(sid, value)
        require(
            Decimal(value["players"][0]["total_points"]) < 0, "Negative leader lost"
        )
        archive(sid)
        f.passed(
            "F02 exact fractional/negative totals, cumulative penalties once and live facts cannot rewrite frozen points/deaths"
        )

        sid, did, players = completed(targets=(5, "5.00", 3, 0))
        value = review(sid)
        require(
            value["state"] == "bo3_required"
            and value["champion_trainer_id"] is None
            and set(value["tied_player_ids"]) == {p["id"] for p in players[:2]},
            "Two-way title tie not explicit",
        )
        reject_unchanged(
            lambda: f.life("finish", sid, finish_body(sid)),
            "CHAMPIONSHIP_BO3_REQUIRED",
            "CHAMPIONSHIP_UNRESOLVED",
        )
        body = bo3_body(sid, players[1]["id"])
        reject_unchanged(
            lambda: f.life("championship_bo3", sid, dict(body, reason=" ")),
            "INVALID_REQUEST",
        )
        reject_unchanged(
            lambda: f.life(
                "championship_bo3",
                sid,
                dict(body, winner_season_player_id=players[2]["id"]),
            ),
            "INVALID_CHAMPIONSHIP_WINNER",
        )
        reject_unchanged(
            lambda: f.life("championship_bo3", sid, body, actor=f.owner["id"]),
            "ADMIN_REQUIRED",
        )
        reject_unchanged(
            lambda: f.life("championship_bo3", sid, dict(body, expected_revision=0)),
            "STALE_REVISION",
        )
        key = uuid4().hex
        results = f.race(
            lambda: f.life("championship_bo3", sid, body, key),
            lambda: f.life("championship_bo3", sid, body, key),
        )
        require(
            results[0]["operation_id"] == results[1]["operation_id"],
            "BO3 replay duplicated",
        )
        require(
            len(f.rows("league_championship_resolutions", season_id=sid)) == 1,
            "Multiple BO3 resolutions",
        )
        reject_unchanged(
            lambda: f.life("championship_bo3", sid, dict(body, reason="Changed"), key),
            "IDEMPOTENCY_CONFLICT",
        )
        value = review(sid)
        require(
            value["state"] == "ready"
            and value["resolution_type"] == "championship_bo3"
            and value["champion_trainer_id"] == players[1]["trainer_id"],
            "BO3 winner not authoritative",
        )
        certificate, _ = archive(sid)
        require(
            f.life("championship_bo3", sid, body, key)["replayed"],
            "BO3 safe replay after archive failed",
        )
        f.passed(
            "F03 exact two-way equality, exceptional BO3 reason/authority/membership/CAS and exact replay across archive"
        )

        sid, did, players = completed(targets=(5, 5, 5, 0), wipes=(2, 1, 0, 0))
        value = review(sid)
        require(
            value["state"] == "ready"
            and value["resolution_type"] == "triple_adjusted_deaths"
            and value["champion_trainer_id"] == players[2]["trainer_id"],
            "Triple tie ignored frozen adjusted deaths",
        )
        invalid_frozen_source(
            sid, "snapshot #- '{inputs,players,0,dead_count}'", missing_deaths=True
        )
        invalid_frozen_source(
            sid, "snapshot #- '{standings,0,penalties,points_reduction}'"
        )
        invalid_frozen_source(
            sid, "jsonb_set(snapshot,'{standings,0,points_awarded}','\"NaN\"')"
        )
        invalid_frozen_source(
            sid,
            "jsonb_set(snapshot,'{inputs,season_id}',to_jsonb('"
            + str(uuid4())
            + "'::text))",
        )
        archive(sid)
        for targets, wipes in (
            ((5, 5, 5, 0), (1, 0, 0, 0)),
            ((0, 0, 0, 0), (0, 0, 0, 0)),
        ):
            sid, did, players = completed(targets=targets, wipes=wipes)
            value = review(sid)
            require(
                value["state"] == "owner_decision_required"
                and value["champion_trainer_id"] is None,
                "Undefined title tie silently resolved",
            )
            reject_unchanged(
                lambda: f.life("finish", sid, finish_body(sid)),
                "CHAMPIONSHIP_UNRESOLVED",
            )
            reject_unchanged(
                lambda: f.life("championship_bo3", sid, bo3_body(sid)),
                "CHAMPIONSHIP_BO3_NOT_REQUIRED",
            )
        f.passed(
            "F04 triple tie minimum frozen deaths; residual triple and four-way fail closed without technical fallback"
        )

        sid, did, players = completed(targets=(5, 5, 3, 0))
        body = bo3_body(sid)
        old_hash = body["input_hash"]
        f.md("correct", sid, did, f.correction(sid, did))
        require(
            review(sid)["input_hash"] != old_hash,
            "Correction failed to invalidate review",
        )
        reject_unchanged(
            lambda: f.life("championship_bo3", sid, body), "CHAMPIONSHIP_REVIEW_STALE"
        )
        reject_unchanged(
            lambda: f.life(
                "finish",
                sid,
                {
                    "expected_revision": f.state(sid)["setup_revision"],
                    "input_hash": old_hash,
                },
            ),
            "CHAMPIONSHIP_REVIEW_STALE",
        )
        archive(sid)
        sid, did, players = completed(targets=(5, 5, 3, 0))
        body = bo3_body(sid)
        other = dict(
            body,
            winner_season_player_id=next(
                p["id"]
                for p in players[:2]
                if p["id"] != body["winner_season_player_id"]
            ),
        )
        race = f.race(
            lambda: f.life("championship_bo3", sid, body),
            lambda: f.life("championship_bo3", sid, other, actor=f.admin2["id"]),
        )
        f.one_winner(race, "STALE_REVISION", "CHAMPIONSHIP_BO3_NOT_REQUIRED")
        require(
            len(f.rows("league_championship_resolutions", season_id=sid)) == 1,
            "Competing BO3 winners both committed",
        )
        sid, did, players = completed(targets=(5, 5, 3, 0))
        body = bo3_body(sid, players[0]["id"])
        correction = f.correction(sid, did)
        race = f.race(
            lambda: f.life("championship_bo3", sid, body),
            lambda: f.md("correct", sid, did, correction),
        )
        require(
            isinstance(race[1], dict)
            and (isinstance(race[0], dict) or race[0] == "CHAMPIONSHIP_REVIEW_STALE"),
            "Unsafe BO3/correction race",
        )
        value = review(sid)
        require(
            value["resolution_type"] == "unique_points"
            and value["champion_trainer_id"] == players[3]["trainer_id"],
            "Stale BO3 resolution survived corrected totals",
        )
        archive(sid)
        f.passed(
            "F05 correction stales reviewed facts and competing BO3 decisions have one authoritative effect"
        )

        sid, did, players = completed()
        body = finish_body(sid)
        key = uuid4().hex
        before = f.preserved(sid)
        race = f.race(
            lambda: f.life("finish", sid, body, key),
            lambda: f.life("finish", sid, body, key),
        )
        require(
            race[0]["operation_id"] == race[1]["operation_id"]
            and len(f.rows("league_finalizations", season_id=sid)) == 1,
            "Finish replay duplicated certificate",
        )
        require(
            f.preserved(sid) == before,
            "Finish created extra rewards/penalties or changed history",
        )
        frozen_certificate = deepcopy(f.rows("league_finalizations", season_id=sid)[0])
        client.table("season_player_stats").update({"revived_after_wipe": 1000}).eq(
            "season_player_id", players[0]["id"]
        ).execute()
        body = dict(expected_revision=f.state(sid)["setup_revision"], label="Frozen F")
        key = uuid4().hex
        race = f.race(
            lambda: f.life("archive", sid, body, key),
            lambda: f.life("archive", sid, body, key),
        )
        require(
            race[0]["archive_id"] == race[1]["archive_id"], "Archive retry duplicated"
        )
        require(
            f.rows("league_finalizations", season_id=sid)[0] == frozen_certificate,
            "Archive rewrote certificate",
        )
        require(
            len(f.rows("hall_of_fame_entries", season_id=sid)) == 1,
            "Hall replay duplicated",
        )
        for table in ("league_finalizations", "league_championship_resolutions"):
            rows = f.rows(table)
            require(rows, "Missing immutable fixture " + table)
            try:
                client.table(table).update({"created_at": "2026-01-01T00:00:00Z"}).eq(
                    "id", rows[0]["id"]
                ).execute()
            except Exception as exc:
                require(
                    getattr(exc, "message", None) == "historical_artifact_immutable"
                    or str(getattr(exc, "code", "")) == "42501",
                    "Wrong immutable rejection",
                )
            else:
                raise AssertionError("Mutable championship history " + table)
        sid, did, players = completed()
        body = finish_body(sid)
        f.one_winner(
            f.race(
                lambda: f.life("finish", sid, body),
                lambda: f.life("finish", sid, body, actor=f.admin2["id"]),
            ),
            "SEASON_NOT_ACTIVE",
            "STALE_REVISION",
        )
        body = dict(expected_revision=f.state(sid)["setup_revision"], label=None)
        f.one_winner(
            f.race(
                lambda: f.life("archive", sid, body),
                lambda: f.life("archive", sid, body, actor=f.admin2["id"]),
            ),
            "SEASON_NOT_FINISHED",
            "STALE_REVISION",
        )
        sid, did, players = completed()
        body = finish_body(sid)
        correction = f.correction(sid, did)
        race = f.race(
            lambda: f.life("finish", sid, body),
            lambda: f.md("correct", sid, did, correction),
        )
        f.one_winner(race, "SEASON_NOT_ACTIVE", "CHAMPIONSHIP_REVIEW_STALE")
        if not isinstance(race[0], dict):
            f.life("finish", sid, finish_body(sid))
        match = f.rows("matches", matchday_id=did)[0]
        reject_unchanged(
            lambda: f.md(
                "results",
                sid,
                did,
                dict(
                    expected_results_revision=f.ds(sid, did)["results_revision"],
                    results=[
                        dict(
                            match_id=match["id"],
                            winner_season_player_id=match["winner_id"],
                        )
                    ],
                ),
            ),
            "SEASON_NOT_ACTIVE",
        )
        f.life("archive", sid)
        sid, did, players = completed()
        body = finish_body(sid)
        match = f.rows("matches", matchday_id=did)[0]
        result_body = dict(
            expected_results_revision=f.ds(sid, did)["results_revision"],
            results=[
                dict(match_id=match["id"], winner_season_player_id=match["winner_id"])
            ],
        )
        race = f.race(
            lambda: f.life("finish", sid, body),
            lambda: f.md("results", sid, did, result_body),
        )
        require(
            isinstance(race[0], dict)
            and race[1] in ("SEASON_NOT_ACTIVE", "MATCHDAY_NOT_OPEN", "ALREADY_CLOSED"),
            "Ordinary result mutation raced past final close",
        )
        f.life("archive", sid)
        sid, did, players = completed()
        body = finish_body(sid)
        archive_body = dict(expected_revision=body["expected_revision"], label=None)
        before = f.preserved(sid)
        race = f.race(
            lambda: f.life("finish", sid, body),
            lambda: f.life("archive", sid, archive_body),
        )
        require(
            isinstance(race[0], dict)
            and race[1] in ("SEASON_NOT_FINISHED", "STALE_REVISION"),
            "Finish/archive race crossed stale lifecycle review",
        )
        require(
            not f.rows("hall_of_fame_entries", season_id=sid)
            and f.preserved(sid) == before,
            "Finish/archive race partially archived or changed competitive facts",
        )
        f.life("archive", sid)
        sid, did, players = completed()
        body = finish_body(sid)
        before = f.preserved(sid)
        dq_body = dict(
            reason="Late disqualification fixture",
            expected_roster_revision=f.state(sid)["roster_revision"],
        )
        race = f.race(
            lambda: f.life("finish", sid, body),
            lambda: f.change(sid, players[0]["id"], "disqualify", dq_body),
        )
        require(
            isinstance(race[0], dict)
            and race[1] in ("SEASON_NOT_ACTIVE", "MATCHDAY_NOT_SCHEDULED"),
            "Final-closed eligibility mutation raced past finish",
        )
        require(
            f.preserved(sid) == before, "Finish/DQ rewrote eligibility or competition"
        )
        f.life("archive", sid)
        f.passed(
            "F06 finish/archive same and distinct keys, immutable certificates, correction serialization and post-finish result denial"
        )

        sid, did, players = completed(targets=(5, 5, 3, 0))
        body = bo3_body(sid)
        for table in (
            "league_championship_resolutions",
            "season_admin_state",
            "activity_events",
            "admin_operation_receipts",
        ):
            inject("championship_bo3", sid, body, table)
        f.life("championship_bo3", sid, body)
        body = finish_body(sid)
        for table in (
            "league_finalizations",
            "seasons",
            "season_admin_state",
            "activity_events",
            "admin_operation_receipts",
        ):
            inject("finish", sid, body, table)
        f.life("finish", sid, body)
        body = dict(expected_revision=f.state(sid)["setup_revision"], label=None)
        for table in (
            "seasons",
            "season_archive_snapshots",
            "hall_of_fame_entries",
            "season_admin_state",
            "activity_events",
            "admin_operation_receipts",
        ):
            inject("archive", sid, body, table)
        f.life("archive", sid, body)
        f.passed(
            "F07 fifteen all-public-table exact rollback boundaries across BO3/finish/archive"
        )

        sid, did, players = completed()
        legacy_request = dict(
            f.request(
                "finish", sid, dict(expected_revision=f.state(sid)["setup_revision"])
            ),
            operation="finish",
        )
        reject_unchanged(
            lambda: f.rpc("api_admin_season_lifecycle", {"p_request": legacy_request}),
            "INVALID_REQUEST",
        )
        # Generate an actual old finish receipt using the retained 029 source,
        # isolated in this PostgreSQL session's temporary namespace. This does
        # not change any installed public function or replay a migration.
        old_source = (
            Path(__file__).resolve().parents[1]
            / "supabase/v2/migrations/029_season_finalization_archive_hall.sql"
        ).read_text(encoding="utf-8")
        header = "create function public.api_admin_season_lifecycle(p_request jsonb) returns jsonb"
        old_function = old_source[old_source.index(header) :]
        old_function = old_function[: old_function.index("end $$;") + len("end $$;")]
        old_function = old_function.replace(
            header,
            "create function pg_temp.phase10_5f_old_finish(p_request jsonb) returns jsonb",
            1,
        )
        sql(
            args,
            old_function
            + " select pg_temp.phase10_5f_old_finish("
            + literal(json.dumps(legacy_request))
            + "::jsonb);",
        )
        require(
            not f.rows("league_finalizations", season_id=sid),
            "Legacy fixture fabricated modern certificate",
        )
        before = snapshot()
        replay = f.rpc("api_admin_season_lifecycle", {"p_request": legacy_request})
        require(
            replay["replayed"] and replay["state"] == "finished",
            "Pre-F hashless finish receipt cannot replay",
        )
        require(snapshot() == before, "Historical finish replay changed rows")
        # A pre-F FINISHED season has no proof of a certified title. Do not invent one.
        require(
            review(sid)["state"] == "legacy",
            "Uncertified historical title presented as modern",
        )
        reject_unchanged(lambda: f.life("archive", sid), "LEGACY_TITLE_UNCERTIFIED")
        for role in ("anon", "owner", "admin"):
            for name in ("api_admin_championship_read", "api_admin_season_lifecycle"):
                try:
                    readers[role].rpc(
                        name,
                        {
                            "p_request": dict(
                                actor_trainer_id=f.admin["id"], season_id=sid
                            )
                        },
                    ).execute()
                except Exception as exc:
                    require(str(getattr(exc, "code", "")) == "42501", "Unsafe RPC ACL")
                else:
                    raise AssertionError("Browser can invoke " + name)
            for table in ("league_finalizations", "league_championship_resolutions"):
                for method in ("insert", "update", "delete"):
                    query = readers[role].table(table)
                    query = (
                        query.delete()
                        if method == "delete"
                        else getattr(query, method)({"season_id": sid})
                    )
                    if method != "insert":
                        query = query.eq("season_id", sid)
                    try:
                        query.execute()
                    except Exception as exc:
                        require(
                            str(getattr(exc, "code", "")) == "42501",
                            "Unsafe title table ACL",
                        )
                    else:
                        raise AssertionError("Browser can mutate " + table)
        catalog = client.execute(
            "select jsonb_agg(jsonb_build_object('name',proname,'definer',prosecdef,'path',proconfig,"
            "'browser',has_function_privilege('authenticated',p.oid,'execute') or has_function_privilege('anon',p.oid,'execute'),"
            "'service',has_function_privilege('service_role',p.oid,'execute'))) "
            "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' "
            "and (p.proname like 'championship_%' or p.proname in ('api_admin_championship_read','api_admin_season_lifecycle'))"
        ).data
        require(
            catalog
            and all(
                not r["definer"]
                and not r["browser"]
                and r["service"]
                and r["path"] == ["search_path=pg_catalog, public"]
                for r in catalog
            ),
            "Unsafe championship function catalog",
        )
        for table in ("league_finalizations", "league_championship_resolutions"):
            require(
                client.execute(
                    "select to_jsonb(relrowsecurity) from pg_class where oid="
                    + literal("public." + table)
                    + "::regclass"
                ).data,
                "Missing title RLS",
            )
        f.passed(
            "F08 pre-F uncertified finish fails closed; browser table/RPC denial, RLS and helper security catalog"
        )
    finally:
        f.cleanup()
    require(snapshot() == baseline, "F fixture residue or public baseline drift")
    print(
        f"PASS F exact cleanup: {len(tables)} public tables; groups={len(f.checks)}",
        flush=True,
    )


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="55439")
    parser.add_argument("--database", default="pokeapp_v2_validation_phase10_5f")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    validate(parser.parse_args(), _psql_text)
