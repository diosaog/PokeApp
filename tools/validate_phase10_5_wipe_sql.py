"""Loopback-only G ownership, live wipe count, sporting freezes and rollback."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from app.application.initial_assignment import plan_initial_assignment
from app.application.matchdays import plan_close
from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import (
    LocalClient,
    SqlError,
    identifier,
    literal,
)

MAX_COUNT = 2147483647
MAX_REVISION = 9007199254740991
PARSER = "pokeapp-reader/2;pkhex/24.11.11"
RPC = "api_participant_wipe_revivals"


def validate(args, sql):
    client = LocalClient(args)
    auth = {role: str(uuid4()) for role in ("admin", "other", "owner")}
    readers = {
        role: LocalClient(args, "authenticated", uid) for role, uid in auth.items()
    }
    readers["anon"] = LocalClient(args, "anon")
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        return client.execute(
            "select jsonb_object_agg(name,rows) from ("
            + " union all ".join(
                "select " + literal(t) + " name,coalesce(jsonb_agg(to_jsonb(r) "
                "order by to_jsonb(r)::text),'[]') rows from public."
                + identifier(t)
                + " r"
                for t in tables
            )
            + ") x"
        ).data

    baseline = snapshot()
    f = SeasonLifecycleFixtures(client, readers, auth, "phase10_5g_" + uuid4().hex)
    sources = {}

    def code(exc):
        return exc.message if isinstance(exc, SqlError) else exc.code.lower()

    def reject(action, *codes):
        before = snapshot()
        try:
            action()
        except (SqlError, SeasonAdminRejected) as exc:
            require(
                code(exc) in codes,
                "Unexpected G rejection " + code(exc) + " expected " + str(codes),
            )
        else:
            raise AssertionError("Expected G rejection " + str(codes))
        require(snapshot() == before, "Rejected G command changed public state")

    def race(*actions):
        barrier = Barrier(len(actions))

        def run(action):
            barrier.wait(timeout=30)
            try:
                return action()
            except (SqlError, SeasonAdminRejected) as exc:
                return code(exc)

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def wipe(sid, *, actor=None, body=None, key=None, extra=None):
        request = dict(actor_trainer_id=actor or f.owner["id"], season_id=sid)
        if body is not None:
            request.update(body=body, idempotency_key=key or uuid4().hex)
        request.update(extra or {})
        result = (
            client.rpc(
                RPC,
                {
                    "p_request": dict(
                        operation="set" if body is not None else "state",
                        request=request,
                    )
                },
            )
            .execute()
            .data
        )
        require(
            set(result)
            == {
                "season_id",
                "revived_after_wipe",
                "revision",
                "editable",
                "blocking_reason",
                "replayed",
            },
            "Wipe response leaked identity, internals or private save data",
        )
        require(
            result["season_id"] == sid
            and type(result["revived_after_wipe"]) is int
            and type(result["revision"]) is int,
            "Invalid own wipe scope/value",
        )
        return result

    def change(sid, value, *, actor=None, body=None, key=None):
        actor = actor or f.owner["id"]
        body = (
            body
            if body is not None
            else dict(
                revived_after_wipe=value,
                expected_revision=wipe(sid, actor=actor)["revision"],
            )
        )
        return wipe(sid, actor=actor, body=body, key=key)

    def own(sid):
        return next(p for p in f.players(sid) if p["trainer_id"] == f.owner["id"])

    def stats(player):
        return f.rows("season_player_stats", season_player_id=player["id"])[0]

    def events(sid):
        return f.rows("activity_events", season_id=sid)

    def old_fingerprint_check(sid):
        source = (
            Path(__file__).resolve().parents[1]
            / "supabase/v2/migrations/028_participant_status_admin.sql"
        ).read_text(encoding="utf-8")
        header = "create or replace function public.matchday_external_facts(sid uuid) returns text"
        old = source[source.index(header) :]
        old = old[: old.index("end $$;") + len("end $$;")]
        old = old.replace(
            header,
            "create function pg_temp.g_previous_external_facts(sid uuid) returns text",
            1,
        )
        before = snapshot()
        sql(
            args,
            old
            + " do $$ begin if public.matchday_external_facts("
            + literal(sid)
            + "::uuid) "
            "is distinct from pg_temp.g_previous_external_facts("
            + literal(sid)
            + "::uuid) then "
            "raise exception 'G migration changed unchanged historical fingerprint'; end if; end $$;",
        )
        require(snapshot() == before, "Historical fingerprint check mutated data")

    def observed(sid, player, dead_count):
        save_hash = uuid4().hex + uuid4().hex
        mons = [
            dict(
                species="Gastly",
                identity_evidence=asdict(
                    PokemonIdentityEvidence(
                        1,
                        5,
                        i + 1,
                        12345,
                        6789,
                        20,
                        2,
                        "Fixture",
                        0,
                        ivs=(17, 0, 0, 0, 0, 0),
                    )
                ),
                legacy_fingerprints=["g_" + str(i)],
            )
            for i in range(dead_count)
        ]
        payload = dict(
            party=[dict(slot_number=i, pokemon=None) for i in range(1, 7)],
            boxes=[
                dict(
                    box_number=b,
                    slots=[
                        dict(
                            slot_number=i,
                            pokemon=mons[i - 1] if b == 8 and i <= len(mons) else None,
                        )
                        for i in range(1, 31)
                    ],
                )
                for b in range(1, 25)
            ],
            observed_progress=dict(
                schema_version=1,
                game="B2",
                generation=5,
                source_hash=save_hash,
                progress=dict(
                    schema_version=1,
                    primary_region="unova",
                    regions=[
                        dict(region="unova", badge_flags=[True, True] + [False] * 6)
                    ],
                ),
            ),
        )
        saved = f.insert(
            "save_files",
            dict(
                season_id=sid,
                trainer_id=player["trainer_id"],
                storage_key=f.run_id + "/" + save_hash,
                original_filename="synthetic-no-bytes.sav",
                sha256=save_hash,
                parser_status="parsed",
                parser_version=PARSER,
            ),
        )
        parsed = f.insert(
            "parsed_saves",
            dict(
                save_file_id=saved["id"],
                parser_version=PARSER,
                schema_version=1,
                payload=payload,
            ),
        )
        reconcile_parsed_save(
            SupabasePokemonIdentityRepository(client),
            season_id=sid,
            trainer_id=player["trainer_id"],
            parsed_save_id=parsed["id"],
            capture_order=CaptureOrder(str(uuid4()), 1),
        )
        client.table("season_players").update({"current_save_file_id": saved["id"]}).eq(
            "id", player["id"]
        ).execute()
        sources[player["id"]] = saved, parsed
        return saved, parsed

    def modern(deaths=None, *, total=2):
        for sid in f.seasons:
            if f.rows("seasons", id=sid)[0]["status"] == "active":
                client.table("seasons").update({"status": "draft"}).eq(
                    "id", sid
                ).execute()
        request = f.request("create", body=dict(name=f.run_id + "_" + uuid4().hex[:8]))
        sid = (
            client.rpc("api_admin_create_season", {"p_request": request})
            .execute()
            .data["season_id"]
        )
        f.seasons.append(sid)
        roster = (
            f.trainers[2:6] if deaths is None or len(deaths) == 4 else f.trainers[1:7]
        )
        for trainer in roster:
            f.add(sid, trainer["id"])
        cfg = f.config(sid)
        cfg.update(
            total_matchdays=total,
            movement_count=0,
            rules=dict(team_lock_required=True, last_b_gets_steal=False),
        )
        f.call("create_config", sid, cfg)
        f.call(
            "activate",
            sid,
            dict(expected_setup_revision=f.state(sid)["setup_revision"]),
        )
        players = f.players(sid)
        for player, count in zip(players, deaths or []):
            observed(sid, player, count)
        require(
            not f.rows("matchdays", season_id=sid),
            "Initial gameplay fixture has unexpected day",
        )
        return sid, players

    def initial_context(sid):
        return (
            client.rpc(
                "initial_assignment_context",
                {
                    "p_request": dict(
                        operation="read",
                        request=dict(actor_trainer_id=f.admin["id"], season_id=sid),
                    )
                },
            )
            .execute()
            .data
        )

    def initial_plan(sid):
        ctx = initial_context(sid)
        body = dict(
            config_version_id=ctx["config_version_id"],
            input_hash=ctx["input_hash"],
            expected_setup_revision=ctx["setup_revision"],
            expected_roster_revision=ctx["roster_revision"],
        )
        return dict(
            request=f.request("initial_assignment", sid, body),
            plan=plan_initial_assignment(ctx, body),
            input_hash=ctx["input_hash"],
        )

    def commit_initial(envelope):
        return (
            client.rpc("api_admin_finalize_initial_assignment", {"p_request": envelope})
            .execute()
            .data
        )

    def day_context(sid, did):
        r = f.request(
            "close",
            sid,
            dict(expected_results_revision=f.ds(sid, did)["results_revision"]),
            did,
        )
        return client.rpc("matchday_context", {"op": "close", "r": r}).execute().data

    def close(sid, did):
        f.open(sid, did)
        f.results(sid, did)
        return f.close(sid, did)

    def immutable_history(sid):
        names = (
            "initial_division_snapshots",
            "matchday_snapshots",
            "matchday_snapshot_revisions",
            "matchday_movements",
            "coin_transactions",
            "purchases",
            "redemptions",
            "team_locks",
            "league_finalizations",
            "league_championship_resolutions",
            "season_archive_snapshots",
            "hall_of_fame_entries",
        )
        return {
            t: sorted(
                f.rows(t, season_id=sid), key=lambda x: x.get("id", x["season_id"])
            )
            for t in names
        }

    try:
        f.setup()
        sid, did = f.season(total=2)
        player = own(sid)
        before = snapshot()
        state = wipe(sid)
        require(
            state
            == dict(
                season_id=sid,
                revived_after_wipe=0,
                revision=0,
                editable=True,
                blocking_reason=None,
                replayed=False,
            ),
            "Initial own count is not zero/editable",
        )
        require(snapshot() == before, "Own read wrote state")
        old_fingerprint_check(sid)
        original_stats = stats(player)
        original_events = events(sid)
        fingerprint = client.rpc("matchday_external_facts", {"sid": sid}).execute().data
        noop = dict(revived_after_wipe=0, expected_revision=0)
        key = uuid4().hex
        result = wipe(sid, body=noop, key=key)
        require(
            result["revision"] == 0
            and stats(player) == original_stats
            and events(sid) == original_events,
            "Unchanged count changed stats/revision/audit",
        )
        require(
            client.rpc("matchday_external_facts", {"sid": sid}).execute().data
            == fingerprint,
            "No-op closed the historical correction window",
        )
        require(
            wipe(sid, body=noop, key=key) == dict(result, replayed=True),
            "No-op receipt not stable",
        )
        client.table("season_player_stats").update(
            {"metadata": {"kept": {"fixture": True}}}
        ).eq("season_player_id", player["id"]).execute()
        untouched = {
            p["id"]: stats(p) for p in f.players(sid) if p["id"] != player["id"]
        }
        body = dict(revived_after_wipe=1, expected_revision=0)
        key = uuid4().hex
        result = wipe(sid, body=body, key=key)
        require(
            result["revived_after_wipe"] == 1 and result["revision"] == 1,
            "Own absolute update failed",
        )
        require(
            stats(player)["metadata"]
            == {"kept": {"fixture": True}, "wipe_revision": 1},
            "Update overwrote unrelated metadata",
        )
        require(
            all(
                stats(p) == untouched[p["id"]]
                for p in f.players(sid)
                if p["id"] != player["id"]
            ),
            "Other participant changed",
        )
        require(
            len(events(sid)) == len(original_events) + 1,
            "Real update audit missing/duplicated",
        )
        require(
            wipe(sid, body=body, key=key) == dict(result, replayed=True),
            "Replay not exact",
        )
        reject(
            lambda: wipe(sid, body=dict(body, revived_after_wipe=2), key=key),
            "idempotency_conflict",
        )
        reject(lambda: wipe(sid, body=body), "wipe_revision_conflict")
        require(
            change(sid, 0)["revision"] == 2, "Owned absolute correction cannot decrease"
        )
        for actor in (f.admin["id"], f.admin2["id"], str(uuid4())):
            reject(
                lambda actor=actor: wipe(sid, actor=actor),
                "participant_not_found",
                "trainer_disabled",
            )
        for invalid in (-1, 0.5, "1", "bad", True, None, MAX_COUNT + 1, 10**100):
            reject(
                lambda invalid=invalid: wipe(
                    sid, body=dict(revived_after_wipe=invalid, expected_revision=2)
                ),
                "invalid_request",
            )
        for invalid in (-1, 1.5, "2", True, None, MAX_REVISION + 1, 10**100):
            reject(
                lambda invalid=invalid: wipe(
                    sid, body=dict(revived_after_wipe=1, expected_revision=invalid)
                ),
                "invalid_request",
            )
        for field in (
            "actor_trainer_id",
            "trainer_id",
            "season_player_id",
            "participant_id",
        ):
            reject(
                lambda field=field: wipe(
                    sid,
                    body=dict(
                        revived_after_wipe=1,
                        expected_revision=2,
                        **{field: f.admin["id"]},
                    ),
                ),
                "invalid_request",
            )
        reject(lambda: wipe(str(uuid4())), "season_not_found")
        client.table("trainers").update({"globally_enabled": False}).eq(
            "id", f.owner["id"]
        ).execute()
        reject(lambda: wipe(sid), "trainer_disabled")
        reject(lambda: wipe(sid, body=body, key=key), "trainer_disabled")
        client.table("trainers").update({"globally_enabled": True}).eq(
            "id", f.owner["id"]
        ).execute()
        f.passed(
            "G01 own strict absolute counter, exact replay/conflict/CAS, no-op fingerprint, audit, metadata and identity isolation"
        )

        original = stats(player)
        for malformed in (None, "0", -1, 0.5, True, MAX_REVISION + 1, {}):
            client.table("season_player_stats").update(
                {"metadata": {"wipe_revision": malformed}}
            ).eq("season_player_id", player["id"]).execute()
            reject(lambda: wipe(sid), "wipe_state_unavailable")
        client.table("season_player_stats").update(
            {"metadata": {"wipe_revision": MAX_REVISION}}
        ).eq("season_player_id", player["id"]).execute()
        require(wipe(sid)["revision"] == MAX_REVISION, "Valid maximum revision lost")
        reject(
            lambda: change(sid, 1), "wipe_state_unavailable", "wipe_revision_conflict"
        )
        client.table("season_player_stats").update(
            {"metadata": original["metadata"]}
        ).eq("season_player_id", player["id"]).execute()
        require(
            change(sid, MAX_COUNT)["revived_after_wipe"] == MAX_COUNT,
            "Maximum int32 count rejected",
        )
        ctx = day_context(sid, did)
        fact = next(p for p in ctx["inputs"]["players"] if p["id"] == player["id"])
        require(
            fact["dead_count"] == 2 * MAX_COUNT,
            "Full int32 count overflowed existing death formula",
        )
        close(sid, did)
        official = next(
            row
            for row in f.rows("public_sanctioned_points", season_id=sid)
            if row["season_player_id"] == player["id"]
        )
        require(
            Decimal(str(official["dead_points_penalty"]))
            == Decimal(MAX_COUNT) * Decimal("0.4"),
            "Full int32 count overflowed frozen official points",
        )
        change(sid, 0)
        f.passed(
            "G02 malformed stored revision fails closed; full int32 count closes with exact official points without clamping"
        )

        sid, players = modern()
        player = own(sid)
        require(wipe(sid)["editable"], "First progression segment has no owned flow")
        change(sid, 1)
        ctx = initial_context(sid)
        row = next(p for p in ctx["players"] if p["id"] == player["id"])
        require(
            row["adjusted_deaths"] is None and not ctx["ready"],
            "Wipe count fabricated complete E death evidence",
        )
        general = client.rpc("league_general_read", {"p_season_id": sid}).execute().data
        require(
            next(p for p in general["rows"] if p["season_player_id"] == player["id"])[
                "dead_count"
            ]
            is None,
            "Wipe count converted unknown B deaths to zero",
        )
        for p, deaths in zip(players, (0, 1, 4, 5)):
            observed(sid, p, deaths)
        target = players[-1]
        change(sid, 1, actor=target["trainer_id"])
        change(sid, 0, actor=player["trainer_id"]) if player["id"] != target[
            "id"
        ] else None
        row = next(
            p for p in initial_context(sid)["players"] if p["id"] == target["id"]
        )
        require(
            row["adjusted_deaths"] == 7,
            "Five observed dead plus one wipe did not yield seven",
        )
        saved, parsed = sources[target["id"]]
        for damaged in ({"boxes": []}, {"trainer_id": str(uuid4())}):
            payload = dict(parsed["payload"], **damaged)
            client.table("parsed_saves").update({"payload": payload}).eq(
                "id", parsed["id"]
            ).execute()
            require(
                next(
                    p
                    for p in initial_context(sid)["players"]
                    if p["id"] == target["id"]
                )["adjusted_deaths"]
                is None,
                "Wipe count bypassed malformed/foreign save evidence",
            )
        client.table("parsed_saves").update({"payload": parsed["payload"]}).eq(
            "id", parsed["id"]
        ).execute()
        commit_initial(initial_plan(sid))
        initial = deepcopy(f.rows("initial_division_snapshots", season_id=sid))
        did = f.state(sid)["current_matchday_id"]
        f.open(sid, did)
        f.results(sid, did)
        planned = plan_close(day_context(sid, did))
        standing = next(
            r for r in planned["standings"] if r["trainer_id"] == target["id"]
        )
        require(
            Decimal(str(standing["penalties"]["dead_points_penalty"]))
            == Decimal("1.4"),
            "Approved penalty not exact 1.4",
        )
        f.close(sid, did)
        first = deepcopy(f.rows("matchday_snapshots", matchday_id=did))
        first_points = deepcopy(f.rows("public_sanctioned_points", season_id=sid))
        nextday = f.state(sid)["current_matchday_id"]
        change(sid, 2, actor=target["trainer_id"])
        require(
            f.rows("initial_division_snapshots", season_id=sid) == initial
            and f.rows("matchday_snapshots", matchday_id=did) == first,
            "Later own count rewrote frozen initial/day snapshot",
        )
        require(
            f.rows("public_sanctioned_points", season_id=sid) == first_points,
            "Live count changed official points before next close",
        )
        reject(
            lambda: f.md("correct", sid, did, f.correction(sid, did)),
            "correction_window_closed",
        )
        close(sid, nextday)
        target_points = next(
            r
            for r in f.rows("public_sanctioned_points", season_id=sid)
            if r["season_player_id"] == target["id"]
        )
        require(
            Decimal(str(target_points["dead_points_penalty"])) == Decimal("1.8"),
            "Next freeze did not use live wipe counter",
        )
        require(
            Decimal(str(target_points["earned_points"]))
            - Decimal(str(target_points["sanctioned_points"]))
            == Decimal("1.8"),
            "Accumulated points double-counted past death penalties",
        )
        require(
            not wipe(sid, actor=target["trainer_id"])["editable"],
            "Final close left counter editable",
        )
        reject(
            lambda: change(sid, 3, actor=target["trainer_id"]),
            "wipe_revivals_not_editable",
        )
        f.life("finish", sid)
        f.life("archive", sid)
        frozen = immutable_history(sid)
        reject(
            lambda: change(sid, 0, actor=target["trainer_id"]),
            "wipe_revivals_not_editable",
        )
        require(
            immutable_history(sid) == frozen, "Archived certificate or Hall changed"
        )
        f.passed(
            "G03 unknown stays unknown; five-plus-one exact formula; future freeze only, points once, closed E/day/F/Hall preserved"
        )

        sid, did = f.season(total=2)
        player = own(sid)
        for first, second, same_key in ((1, 1, True), (2, 2, False), (3, 4, False)):
            revision = wipe(sid)["revision"]
            a = dict(revived_after_wipe=first, expected_revision=revision)
            b = dict(revived_after_wipe=second, expected_revision=revision)
            key = uuid4().hex
            before_events = len(events(sid))
            result = race(
                lambda: wipe(sid, body=a, key=key),
                lambda: wipe(sid, body=b, key=key if same_key else uuid4().hex),
            )
            if same_key:
                require(
                    all(isinstance(r, dict) for r in result)
                    and result[0]["revision"] == result[1]["revision"],
                    "Same key race duplicated",
                )
            else:
                require(
                    sum(isinstance(r, dict) for r in result) == 1
                    and "wipe_revision_conflict" in result,
                    "Conflicting/same value CAS race lost update",
                )
            require(
                wipe(sid)["revision"] == revision + 1
                and len(events(sid)) == before_events + 1,
                "Concurrent update duplicated revision/audit",
            )
        revision = wipe(sid)["revision"]
        key = uuid4().hex
        result = race(
            lambda: wipe(
                sid,
                body=dict(revived_after_wipe=8, expected_revision=revision),
                key=key,
            ),
            lambda: wipe(
                sid,
                body=dict(revived_after_wipe=9, expected_revision=revision),
                key=key,
            ),
        )
        require(
            sum(isinstance(r, dict) for r in result) == 1
            and "idempotency_conflict" in result,
            "Same-key different-body race accepted both",
        )
        f.passed(
            "G04 identical/conflicting concurrent values and keys have one revision and audit effect"
        )

        for total in (1, 2):
            sid, did = f.season(total=total)
            player = own(sid)
            f.open(sid, did)
            f.results(sid, did)
            body = dict(revived_after_wipe=1, expected_revision=0)
            result = race(lambda: wipe(sid, body=body), lambda: f.close(sid, did))
            require(
                isinstance(result[0], dict)
                or (total == 1 and result[0] == "wipe_revivals_not_editable"),
                "Update/close editability invalid",
            )
            require(
                isinstance(result[1], dict) or result[1] == "stale_inputs",
                "Close captured mixed G input",
            )
            if not isinstance(result[1], dict):
                f.close(sid, did)
            frozen = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]
            death = next(
                p["dead_count"]
                for p in frozen["inputs"]["players"]
                if p["id"] == player["id"]
            )
            require(death in (0, 2), "Update/close captured partial count")
            require(
                wipe(sid)["revived_after_wipe"] == int(isinstance(result[0], dict)),
                "Lost committed wipe update",
            )
            if total == 1 and isinstance(result[0], dict):
                require(death == 2, "Successful pre-final-close update not captured")
        sid, players = modern((0, 1, 4, 5))
        player = players[0]
        envelope = initial_plan(sid)
        result = race(
            lambda: change(
                sid,
                1,
                actor=player["trainer_id"],
                body=dict(revived_after_wipe=1, expected_revision=0),
            ),
            lambda: commit_initial(envelope),
        )
        require(
            isinstance(result[0], dict)
            and (
                isinstance(result[1], dict)
                or result[1] == "initial_assignment_review_stale"
            ),
            "G/E race violated whole reviewed facts",
        )
        if isinstance(result[1], dict):
            require(
                f.rows("initial_division_snapshots", season_id=sid)[0]["input_hash"]
                == envelope["input_hash"],
                "Mixed initial split committed",
            )
        else:
            commit_initial(initial_plan(sid))
        sid, did = f.complete()
        body = dict(revived_after_wipe=1, expected_revision=0)
        result = race(lambda: wipe(sid, body=body), lambda: f.life("finish", sid))
        require(
            result[0] == "wipe_revivals_not_editable" and isinstance(result[1], dict),
            "Final closed counter raced past certificate",
        )
        sid, did = f.season()
        player = own(sid)
        result = race(lambda: wipe(sid, body=body), lambda: f.change(sid, player["id"]))
        require(
            isinstance(result[1], dict)
            and (isinstance(result[0], dict) or result[0] == "participant_inactive"),
            "Participant exit race invalid",
        )
        require(
            wipe(sid)["blocking_reason"] == "participant_inactive",
            "Inactive own state not read-only",
        )
        reject(lambda: wipe(sid, body=body), "participant_inactive")
        f.passed(
            "G05 update versus close, initial split, final finish and participant exit serialize sporting authority"
        )

        sid, did = f.season()
        player = own(sid)
        body = dict(revived_after_wipe=1, expected_revision=0)
        for table in (
            "season_player_stats",
            "activity_events",
            "admin_operation_receipts",
        ):
            before = snapshot()
            sql(
                args,
                "create function public.phase10_5g_fail() returns trigger language plpgsql as $$ begin "
                "if new.season_id="
                + literal(sid)
                + "::uuid then raise exception 'G injected failure' using errcode='P0001'; "
                "end if; return new; end $$; create trigger phase10_5g_fail after insert or update on public."
                + table
                + " for each row execute function public.phase10_5g_fail();",
            )
            try:
                try:
                    wipe(sid, body=body)
                except SqlError as exc:
                    require(exc.code == "P0001", "Unexpected rollback rejection")
                else:
                    raise AssertionError("Failure injection did not fire " + table)
                require(snapshot() == before, "Partial G mutation after " + table)
            finally:
                sql(
                    args,
                    "drop trigger phase10_5g_fail on public."
                    + table
                    + "; drop function public.phase10_5g_fail();",
                )
        key = uuid4().hex
        result = wipe(sid, body=body, key=key)
        close(sid, did)
        require(
            wipe(sid, body=body, key=key) == dict(result, replayed=True),
            "Safe receipt replay after closed day failed",
        )
        f.passed(
            "G06 three exact all-public rollback boundaries and stable old receipt after day close"
        )

        for role in ("anon", "owner", "admin"):
            try:
                readers[role].rpc(
                    RPC,
                    {
                        "p_request": dict(
                            operation="state",
                            request=dict(actor_trainer_id=f.owner["id"], season_id=sid),
                        )
                    },
                ).execute()
            except SqlError as exc:
                require(exc.code == "42501", "Unsafe browser RPC ACL")
            else:
                raise AssertionError("Browser can invoke own counter privileged RPC")
            for update in (
                {"revived_after_wipe": 7},
                {"metadata": {"wipe_revision": 700}},
            ):
                try:
                    readers[role].table("season_player_stats").update(update).eq(
                        "season_player_id", player["id"]
                    ).execute()
                except SqlError as exc:
                    require(exc.code == "42501", "Wrong direct stats write rejection")
                else:
                    raise AssertionError("Browser can mutate authoritative wipe stats")
        catalog = client.execute(
            "select jsonb_agg(jsonb_build_object('name',proname,'definer',prosecdef,'path',proconfig,"
            "'browser',has_function_privilege('authenticated',p.oid,'execute') or has_function_privilege('anon',p.oid,'execute'),"
            "'service',has_function_privilege('service_role',p.oid,'execute'))) from pg_proc p "
            "join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' "
            "and (p.proname like 'wipe_%' or p.proname='api_participant_wipe_revivals')"
        ).data
        require(
            catalog
            and all(
                not p["definer"]
                and not p["browser"]
                and p["service"]
                and p["path"] == ["search_path=pg_catalog, public"]
                for p in catalog
            ),
            "Unsafe G function grants/security",
        )
        require(
            client.execute(
                "select to_jsonb(relrowsecurity) from pg_class where oid='public.season_player_stats'::regclass"
            ).data,
            "Stats RLS disabled",
        )
        f.passed(
            "G07 browser table/column/RPC denial, private response whitelist, fixed invoker helpers and existing RLS"
        )

        sid, players = modern((0, 1, 4, 5, 6, 7))
        commit_initial(initial_plan(sid))
        initial = deepcopy(f.rows("initial_division_snapshots", season_id=sid))
        did = f.state(sid)["current_matchday_id"]
        f.open(sid, did)
        context = day_context(sid, did)
        winners = {}
        for division in ("A", "B"):
            members = sorted(
                (p for p in context["inputs"]["players"] if p["division"] == division),
                key=lambda p: p["dead_count"],
            )
            ids = [p["id"] for p in members]
            for a, b in zip(ids, ids[1:] + ids[:1]):
                winners[frozenset((a, b))] = a
        f.md(
            "results",
            sid,
            did,
            dict(
                expected_results_revision=f.ds(sid, did)["results_revision"],
                results=[
                    dict(
                        match_id=m["id"],
                        winner_season_player_id=winners[
                            frozenset((m["player_a_id"], m["player_b_id"]))
                        ],
                    )
                    for m in f.ds(sid, did)["matches"]
                ],
            ),
        )
        before = plan_close(day_context(sid, did))
        target = players[0]
        require(
            next(r for r in before["standings"] if r["trainer_id"] == target["id"])[
                "position"
            ]
            == 1,
            "Equal-win daily fixture did not rank by fewer observed deaths",
        )
        change(sid, 1, actor=target["trainer_id"])
        after = plan_close(day_context(sid, did))
        require(
            next(r for r in after["standings"] if r["trainer_id"] == target["id"])[
                "position"
            ]
            == 2,
            "Live owned wipe count did not affect equal-win D daily order",
        )
        f.close(sid, did)
        frozen = deepcopy(f.rows("matchday_snapshots", matchday_id=did))
        change(sid, 0, actor=target["trainer_id"])
        require(
            f.rows("initial_division_snapshots", season_id=sid) == initial
            and f.rows("matchday_snapshots", matchday_id=did) == frozen,
            "Later counter decrease rewrote committed E or D order",
        )
        f.passed(
            "G08 equal-win daily ranking consumes live wipe deaths before close and preserves frozen order after decrease"
        )

        sid, did = f.season()
        player = own(sid)
        original = stats(player)
        client.table("season_player_stats").delete().eq(
            "season_player_id", player["id"]
        ).execute()
        reject(lambda: wipe(sid), "wipe_state_unavailable")
        reject(
            lambda: change(
                sid, 1, body=dict(revived_after_wipe=1, expected_revision=0)
            ),
            "wipe_state_unavailable",
        )
        f.insert("season_player_stats", original)
        for status in ("draft", "finished", "archived"):
            lifecycle = {"status": status}
            if status in ("finished", "archived"):
                lifecycle[status + "_at"] = "2026-10-04T00:00:00Z"
            client.table("seasons").update(lifecycle).eq("id", sid).execute()
            require(
                wipe(sid)["blocking_reason"] == "season_inactive"
                and not wipe(sid)["editable"],
                "Non-active season own state should be read-only",
            )
            reject(lambda: change(sid, 1), "wipe_revivals_not_editable")
        client.table("seasons").update({"status": "active"}).eq("id", sid).execute()
        client.table("seasons").update({"current_matchday_id": None}).eq(
            "id", sid
        ).execute()
        require(
            wipe(sid)["blocking_reason"] == "membership_ineligible",
            "Legacy missing day became editable",
        )
        reject(lambda: change(sid, 1), "wipe_revivals_not_editable")
        client.table("seasons").update({"current_matchday_id": did}).eq(
            "id", sid
        ).execute()
        membership = f.rows("division_memberships", season_player_id=player["id"])[0]
        client.table("division_memberships").update(
            {"eligibility_ends_before_matchday_number": 1}
        ).eq("id", membership["id"]).execute()
        require(
            wipe(sid)["blocking_reason"] == "membership_ineligible",
            "Ineligible membership became editable",
        )
        reject(lambda: change(sid, 1), "wipe_revivals_not_editable")
        client.table("seasons").update(
            {"status": "discarded", "discarded_at": "2026-10-04T00:00:00Z"}
        ).eq("id", sid).execute()
        reject(lambda: wipe(sid), "season_not_found")
        reject(
            lambda: change(
                sid, 1, body=dict(revived_after_wipe=1, expected_revision=0)
            ),
            "season_not_found",
        )
        f.passed(
            "G09 missing stats fail closed; draft/finished/archived/discarded, absent day and ineligible membership cannot mutate"
        )
    finally:
        for sid in f.seasons:
            client.table("initial_division_snapshots").delete().eq(
                "season_id", sid
            ).execute()
        f.cleanup()
        require(snapshot() == baseline, "G fixture residue or public baseline drift")
    groups = [check for check in f.checks if check.startswith("G")]
    print(
        f"PASS G exact cleanup: {len(tables)} public tables; groups={len(groups)}; rollback_boundaries=3; concurrent_scenarios=9",
        flush=True,
    )
    return dict(
        public_tables=len(tables),
        groups=groups,
        rollback_boundaries=3,
        concurrent_scenarios=9,
        cleanup="PASS",
    )


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="55439")
    parser.add_argument("--database", default="pokeapp_v2_validation_phase10_5g")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    validate(parser.parse_args(), _psql_text)
