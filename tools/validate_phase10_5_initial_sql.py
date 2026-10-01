"""Loopback-only E observation, split, authorization, concurrency and rollback checks."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from threading import Barrier
from uuid import uuid4

from app.application.initial_assignment import (
    InitialAssignmentRejected,
    initial_assignment_review,
    plan_initial_assignment,
)
from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import (
    LocalClient,
    SqlError,
    identifier,
    literal,
)

PARSER = "pokeapp-reader/2;pkhex/24.11.11"


def validate(args, sql):
    client = LocalClient(args)
    auth = {r: str(uuid4()) for r in ("admin", "other", "owner")}
    readers = {r: LocalClient(args, "authenticated", uid) for r, uid in auth.items()}
    readers["anon"] = LocalClient(args, "anon")
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        return client.execute(
            "select jsonb_object_agg(name,rows) from ("
            + " union all ".join(
                "select "
                + literal(t)
                + " name,coalesce(jsonb_agg(to_jsonb(r) order by to_jsonb(r)::text),'[]') rows from public."
                + identifier(t)
                + " r"
                for t in tables
            )
            + ") x"
        ).data

    baseline = snapshot()
    f = SeasonLifecycleFixtures(client, readers, auth, "phase10_5e_" + uuid4().hex)
    sources = {}

    def modern(deaths=None, capacities=None):
        for old in f.seasons:
            if f.rows("seasons", id=old)[0]["status"] == "active":
                client.table("seasons").update({"status": "draft"}).eq(
                    "id", old
                ).execute()
        n = len(deaths) if deaths is not None else 4
        # Explicit production RPC: inherited fixtures may select the old creator
        # to test their own frozen pre-E setup contract.
        r = f.request("create", body={"name": f.run_id + "_" + uuid4().hex[:8]})
        sid = (
            client.rpc("api_admin_create_season", {"p_request": r})
            .execute()
            .data["season_id"]
        )
        f.seasons.append(sid)
        for trainer in f.trainers[1 : n + 1]:
            f.add(sid, trainer["id"])
        cfg = f.config(sid)
        cfg.update(
            division_sizes=capacities or {"A": n // 2, "B": n - n // 2},
            rules={"team_lock_required": True, "last_b_gets_steal": False},
        )
        f.call("create_config", sid, cfg)
        require(
            f.state(sid)["readiness"]["can_activate"],
            "First leg cannot start before division assignment",
        )
        f.call(
            "activate", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]}
        )
        require(
            not f.rows("matchdays", season_id=sid),
            "Gameplay activation invented competitive matches",
        )
        players = sorted(f.rows("season_players", season_id=sid), key=lambda p: p["id"])
        if deaths is not None:
            for p, count in zip(players, deaths):
                observed(sid, p, count)
        return sid, players

    def observed(sid, player, deaths, flags=None):
        save_hash = uuid4().hex + uuid4().hex
        flags = flags if flags is not None else [True, True] + [False] * 6
        mons = []
        for i in range(deaths):
            evidence = PokemonIdentityEvidence(
                1, 5, i + 1, 12345, 6789, 20, 2, "Fixture", 0, ivs=(17, 0, 0, 0, 0, 0)
            )
            mons.append(
                {
                    "species": "Gastly",
                    "identity_evidence": asdict(evidence),
                    "legacy_fingerprints": ["e_" + str(i)],
                }
            )
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
                    regions=[dict(region="unova", badge_flags=flags)],
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
        sources[player["id"]] = (saved, parsed)

    def context(sid, request=None):
        return (
            client.rpc(
                "initial_assignment_context",
                {
                    "p_request": {
                        "operation": "finalize" if request else "read",
                        "request": request
                        or dict(actor_trainer_id=f.admin["id"], season_id=sid),
                    }
                },
            )
            .execute()
            .data
        )

    def prepared(sid, *, decision=False, reverse=False, key=None, actor=None):
        ctx = context(sid)
        body = {
            "config_version_id": ctx["config_version_id"],
            "input_hash": ctx["input_hash"],
            "expected_setup_revision": ctx["setup_revision"],
            "expected_roster_revision": ctx["roster_revision"],
        }
        if decision:
            boundary = initial_assignment_review(ctx)["boundary_tie"]
            ids = boundary["player_ids"][::-1] if reverse else boundary["player_ids"]
            body["tie_resolution"] = dict(
                input_hash=ctx["input_hash"],
                orders=[dict(player_ids=ids, reason="External sporting decision")],
            )
        r = f.request("initial_assignment", sid, body, key=key, actor=actor)
        return dict(
            request=r,
            plan=plan_initial_assignment(ctx, body),
            input_hash=ctx["input_hash"],
        )

    def commit(envelope):
        return (
            client.rpc("api_admin_finalize_initial_assignment", {"p_request": envelope})
            .execute()
            .data
        )

    def rejected(action, *codes):
        before = snapshot()
        try:
            action()
        except (SqlError, InitialAssignmentRejected) as exc:
            code = exc.message if isinstance(exc, SqlError) else exc.code.lower()
            require(
                code in codes,
                "Unexpected rejection " + code + " expected " + str(codes),
            )
        else:
            raise AssertionError("Expected rejection " + str(codes))
        require(snapshot() == before, "Rejected operation mutated public state")

    def race(*actions):
        barrier = Barrier(len(actions))

        def call(action):
            barrier.wait(timeout=30)
            try:
                return action()
            except SqlError as exc:
                return exc.message

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(call, actions))

    try:
        f.setup()
        sid, players = modern()
        ctx = context(sid)
        require(
            not ctx["ready"]
            and all(
                p["observed_badges"] is None and p["adjusted_deaths"] is None
                for p in ctx["players"]
            ),
            "Unobserved zero fabricated",
        )
        client.table("season_player_stats").update({"badges_count": 8}).eq(
            "season_id", sid
        ).execute()
        require(
            context(sid)["input_hash"] == ctx["input_hash"],
            "Manual legacy badge counter became authority",
        )
        for i, p in enumerate(players):
            observed(sid, p, i)
        ctx = context(sid)
        require(ctx["ready"], "Complete trusted source did not unblock")
        saved, parsed = sources[players[0]["id"]]
        payload = deepcopy(parsed["payload"])
        for change in (None, [False, True, True] + [False] * 5, [False] * 8):
            changed = deepcopy(payload)
            if change is None:
                changed.pop("observed_progress")
            else:
                changed["observed_progress"]["progress"]["regions"][0][
                    "badge_flags"
                ] = change
            client.table("parsed_saves").update({"payload": changed}).eq(
                "id", parsed["id"]
            ).execute()
            current = context(sid)
            require(not current["ready"], "Missing/insufficient cap accepted")
            first = next(p for p in current["players"] if p["id"] == players[0]["id"])
            require(
                first["observed_badges"] == (None if change is None else sum(change)),
                "Unknown versus observed zero lost",
            )
        client.table("parsed_saves").update({"payload": payload}).eq(
            "id", parsed["id"]
        ).execute()
        for field in ("source_hash", "game"):
            changed = deepcopy(payload)
            changed["observed_progress"][field] = "invalid"
            client.table("parsed_saves").update({"payload": changed}).eq(
                "id", parsed["id"]
            ).execute()
            require(not context(sid)["ready"], "Unbound progress accepted")
        changed = deepcopy(payload)
        changed["boxes"][7]["slots"].pop()
        client.table("parsed_saves").update({"payload": changed}).eq(
            "id", parsed["id"]
        ).execute()
        incomplete = context(sid)
        first = next(p for p in incomplete["players"] if p["id"] == players[0]["id"])
        require(
            not incomplete["ready"]
            and first["observed_badges"] == 2
            and first["adjusted_deaths"] is None
            and "death_inputs_unobserved" in incomplete["blocking_reasons"],
            "Independent progress/death evidence collapsed",
        )
        client.table("parsed_saves").update({"payload": payload}).eq(
            "id", parsed["id"]
        ).execute()
        f.passed(
            "E01 real identity binding, observed progress versus unknown/zero, Medal 2 flags, hash/game/complete Box 8"
        )

        envelope = prepared(sid)
        rejected(
            lambda: commit(
                {
                    **envelope,
                    "request": {
                        **envelope["request"],
                        "actor_trainer_id": f.owner["id"],
                    },
                }
            ),
            "admin_required",
        )
        rejected(
            lambda: client.rpc(
                "api_admin_initial_divisions",
                {"p_request": f.request("initial_divisions", sid, {})},
            ).execute(),
            "initial_assignment_required",
        )
        for table, where, values in (
            (
                "season_player_stats",
                {"season_player_id": players[0]["id"]},
                {"revived_after_wipe": 1},
            ),
            ("parsed_saves", {"id": parsed["id"]}, {"payload": changed}),
        ):
            query = client.table(table).update(values)
            for key, value in where.items():
                query = query.eq(key, value)
            query.execute()
            rejected(lambda: commit(envelope), "initial_assignment_review_stale")
            if table == "season_player_stats":
                client.table(table).update({"revived_after_wipe": 0}).eq(
                    "season_player_id", players[0]["id"]
                ).execute()
            else:
                client.table(table).update({"payload": payload}).eq(
                    "id", parsed["id"]
                ).execute()
        f.passed(
            "E02 admin authority, manual setup bypass denied, stale death/progress evidence rejected with exact rollback"
        )

        # Every durable write statement group, including each A/B iteration.
        points = [
            ("divisions", "new.code='A'"),
            ("divisions", "new.code='B'"),
            (
                "division_memberships",
                "new.division_id=(select id from public.divisions where season_id=new.season_id and code='A')",
            ),
            (
                "division_memberships",
                "new.division_id=(select id from public.divisions where season_id=new.season_id and code='B')",
            ),
            ("matchdays", "true"),
            (
                "matches",
                "new.division_id=(select id from public.divisions where season_id=new.season_id and code='A')",
            ),
            (
                "matches",
                "new.division_id=(select id from public.divisions where season_id=new.season_id and code='B')",
            ),
            ("initial_division_snapshots", "true"),
            ("seasons", "true"),
            ("season_admin_state", "true"),
            ("activity_events", "true"),
            ("admin_operation_receipts", "true"),
        ]
        for table, condition in points:
            column = "id" if table == "seasons" else "season_id"
            before = snapshot()
            sql(
                args,
                "create function public.__phase10_5e_fail() returns trigger language plpgsql as $$ begin if new."
                + column
                + "="
                + literal(sid)
                + "::uuid and ("
                + condition
                + ") then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "
                + "create trigger phase10_5e_failure after insert or update on public."
                + identifier(table)
                + " for each row execute function public.__phase10_5e_fail();",
            )
            try:
                try:
                    commit(envelope)
                except SqlError as exc:
                    require(
                        exc.code == "P0001", "Wrong rollback failure " + exc.message
                    )
                else:
                    raise AssertionError("Failure boundary not reached " + table)
                require(
                    snapshot() == before, "Partial initial assignment commit " + table
                )
            finally:
                sql(
                    args,
                    "drop trigger phase10_5e_failure on public."
                    + identifier(table)
                    + "; drop function public.__phase10_5e_fail();",
                )
        f.passed("E03 twelve durable write boundaries restore all public rows exactly")

        result = race(lambda: commit(envelope), lambda: commit(envelope))
        require(
            all(isinstance(r, dict) for r in result)
            and result[0]["operation_id"] == result[1]["operation_id"],
            "Same-key replay duplicated split",
        )
        require(
            context(sid, envelope["request"])["receipt"]["operation_id"]
            == result[0]["operation_id"],
            "Unknown-outcome replay replanned assigned state",
        )
        for table in (
            "coin_transactions",
            "matchday_movements",
            "purchases",
            "shop_promotions",
            "matchday_snapshots",
        ):
            require(
                not f.rows(table, season_id=sid),
                "Initial split accidentally applied daily consequences " + table,
            )
        frozen = deepcopy(f.rows("initial_division_snapshots", season_id=sid))
        require(
            all(
                p["_source"]["observed_progress"]["progress"]["regions"][0][
                    "badge_flags"
                ]
                == [True, True] + [False] * 6
                for p in frozen[0]["inputs"]["players"]
            ),
            "Initial audit did not freeze exact canonical observed flags",
        )
        did = result[0]["resource_id"]
        require(
            len(f.rows("matches", season_id=sid)) == 2,
            "Canonical first match pairs missing",
        )
        f.open(sid, did)
        require(
            not f.rows("team_locks", season_id=sid),
            "Team Lock became initial readiness blocker",
        )
        changed = deepcopy(payload)
        changed.pop("observed_progress")
        client.table("parsed_saves").update({"payload": changed}).eq(
            "id", parsed["id"]
        ).execute()
        rejected(
            lambda: client.rpc(
                "api_participant_matchday",
                {
                    "p_request": {
                        "operation": "results",
                        "request": f.request(
                            "results",
                            sid,
                            {
                                "expected_results_revision": f.ds(sid, did)[
                                    "results_revision"
                                ],
                                "results": [
                                    {
                                        "match_id": f.rows("matches", season_id=sid)[0][
                                            "id"
                                        ],
                                        "winner_season_player_id": f.rows(
                                            "matches", season_id=sid
                                        )[0]["player_a_id"],
                                    }
                                ],
                            },
                            did,
                            actor=players[0]["trainer_id"],
                        ),
                    }
                },
            ).execute(),
            "initial_assignment_not_ready",
        )
        client.table("parsed_saves").update({"payload": payload}).eq(
            "id", parsed["id"]
        ).execute()
        require(
            f.rows("initial_division_snapshots", season_id=sid) == frozen
            and context(sid)["state"] == "assigned",
            "Finalized history changed with live progress",
        )
        match = f.rows("matches", season_id=sid)[0]
        request = f.request(
            "results",
            sid,
            {
                "expected_results_revision": f.ds(sid, did)["results_revision"],
                "results": [
                    {
                        "match_id": match["id"],
                        "winner_season_player_id": match["player_a_id"],
                    }
                ],
            },
            did,
            actor=players[0]["trainer_id"],
        )
        replay_and_result = race(
            lambda: commit(envelope),
            lambda: (
                client.rpc(
                    "api_participant_matchday",
                    {"p_request": {"operation": "results", "request": request}},
                )
                .execute()
                .data
            ),
        )
        require(
            all(isinstance(r, dict) for r in replay_and_result)
            and replay_and_result[0]["operation_id"] == result[0]["operation_id"]
            and f.rows("initial_division_snapshots", season_id=sid) == frozen,
            "Participant results versus unknown-outcome initialization replay changed initial truth",
        )
        # Same actual redemption is present in both imported-used and applied
        # records: max() avoids counting it twice, exactly as 030/D do.
        p = players[1]
        entitlement = f.entitlement(sid, p, "revivir_pokemon")
        entity = f.rows("pokemon_observations", save_file_id=sources[p["id"]][0]["id"])[
            0
        ]["pokemon_entity_id"]
        f.use(entitlement, entity)
        client.table("season_player_stats").update({"revived_after_wipe": 2}).eq(
            "season_player_id", p["id"]
        ).execute()
        observed_players = (
            client.rpc("initial_assignment_observations", {"sid": sid}).execute().data
        )
        daily = (
            client.rpc(
                "matchday_context",
                {"op": "close", "r": {"season_id": sid, "resource_id": did}},
            )
            .execute()
            .data
        )
        require(
            {p["id"]: p["adjusted_deaths"] for p in observed_players}
            == {p["id"]: p["dead_count"] for p in daily["inputs"]["players"]},
            "E versus authoritative 030/D death formula differs",
        )
        require(
            next(x["adjusted_deaths"] for x in observed_players if x["id"] == p["id"])
            == 6,
            "Revive counted twice or wipes unadjusted",
        )
        f.results(sid, did)
        partial = deepcopy(payload)
        partial["boxes"][7]["slots"].pop()
        client.table("parsed_saves").update({"payload": partial}).eq(
            "id", parsed["id"]
        ).execute()
        rejected(
            lambda: client.rpc(
                "api_admin_matchday_context",
                {
                    "p_request": {
                        "operation": "close",
                        "request": f.request(
                            "close",
                            sid,
                            {
                                "expected_results_revision": f.ds(sid, did)[
                                    "results_revision"
                                ]
                            },
                            did,
                        ),
                    }
                },
            ).execute(),
            "ranking_inputs_unavailable",
        )
        client.table("parsed_saves").update({"payload": payload}).eq(
            "id", parsed["id"]
        ).execute()
        f.close(sid, did)
        require(
            f.rows("initial_division_snapshots", season_id=sid) == frozen
            and f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]["inputs"][
                "ranking"
            ]["rule"]
            == "wins_adjusted_deaths_v1",
            "D close reinterpreted initial E evidence/rule",
        )
        f.passed(
            "E04 concurrent replay, no daily effects/Team Lock blocker, participant results cap recheck, frozen initial facts"
        )

        for deaths, capacities in (
            ([0, 1, 1, 3], {"A": 2, "B": 2}),
            ([0, 1, 1, 1, 3], {"A": 3, "B": 2}),
            ([0, 0, 2, 2], {"A": 2, "B": 2}),
            ([0, 0, 2, 2, 3], {"A": 2, "B": 3}),
        ):
            sid, _ = modern(deaths, capacities)
            boundary = initial_assignment_review(context(sid))["boundary_tie"]
            if boundary:
                rejected(lambda: prepared(sid), "initial_boundary_tie_unresolved")
                first, second = (
                    prepared(sid, decision=True),
                    prepared(sid, decision=True, reverse=True, actor=f.admin2["id"]),
                )
                results = race(lambda: commit(first), lambda: commit(second))
                require(
                    sum(isinstance(r, dict) for r in results) == 1
                    and "initial_assignment_locked" in results,
                    "Competing boundary decisions both won",
                )
                winner = first if isinstance(results[0], dict) else second
                recorded = f.rows("initial_division_snapshots", season_id=sid)[0]
                require(
                    recorded["assignments"] == winner["plan"]["assignments"]
                    and recorded["audit"]["resolution"]
                    == winner["plan"]["audit"]["resolution"],
                    "External order/reason lost",
                )
            else:
                commit(prepared(sid))
            require(
                {
                    code: sum(
                        m["division_id"]
                        == next(
                            d["id"]
                            for d in f.rows("divisions", season_id=sid)
                            if d["code"] == code
                        )
                        for m in f.rows("division_memberships", season_id=sid)
                    )
                    for code in ("A", "B")
                }
                == capacities,
                "Odd/even configured capacity changed",
            )
        f.passed(
            "E05 two/multi-member boundary ties only, competing decisions, neutral ties both sides, odd/even configured cuts"
        )

        for mutation in ("deaths", "progress", "selected_save"):
            sid, players = modern([0, 1, 2, 3])
            envelope = prepared(sid)
            # Separate sessions race source mutations with finalization. Either
            # the old observation freezes before the update, or stale rejects.
            player = players[0]
            parsed = sources[player["id"]][1]
            changed = deepcopy(parsed["payload"])
            changed["observed_progress"]["progress"]["regions"][0]["badge_flags"][1] = (
                False
            )
            update = {
                "deaths": lambda: (
                    client.table("season_player_stats")
                    .update({"revived_after_wipe": 1})
                    .eq("season_player_id", player["id"])
                    .execute()
                    .data
                ),
                "progress": lambda: (
                    client.table("parsed_saves")
                    .update({"payload": changed})
                    .eq("id", parsed["id"])
                    .execute()
                    .data
                ),
                "selected_save": lambda: (
                    client.table("season_players")
                    .update({"current_save_file_id": None})
                    .eq("id", player["id"])
                    .execute()
                    .data
                ),
            }[mutation]
            result = race(lambda: commit(envelope), update)
            require(
                isinstance(result[0], dict)
                or result[0] == "initial_assignment_review_stale",
                "Source/finalization race invalid result " + mutation,
            )
            if isinstance(result[0], dict):
                require(
                    f.rows("initial_division_snapshots", season_id=sid)[0]["input_hash"]
                    == envelope["input_hash"],
                    "Mixed observation committed",
                )
        f.passed(
            "E06 separate-session progress, selected save and death adjustment versus finalization serialize complete inputs"
        )

        legacy = f.ready(prepare=True)
        previous = snapshot()
        require(
            context(legacy)["state"] == "legacy"
            and not f.rows("initial_division_snapshots", season_id=legacy),
            "Legacy reinterpreted as modern",
        )
        require(
            snapshot() == previous, "Historical membership/source rewritten by E read"
        )
        rejected(
            lambda: client.rpc(
                "api_admin_finalize_initial_assignment",
                {
                    "p_request": {
                        "request": f.request("initial_assignment", legacy, {}),
                        "plan": {},
                        "input_hash": "0" * 64,
                    }
                },
            ).execute(),
            "initial_assignment_locked",
        )
        f.passed(
            "E07 actual legacy creator/manual memberships stay unchanged and reject modern reinterpretation"
        )

        for role in readers:
            for name, params in (
                ("initial_assignment_context", {"p_request": {}}),
                ("initial_assignment_observations", {"sid": sid}),
                ("api_admin_finalize_initial_assignment", {"p_request": {}}),
            ):
                try:
                    readers[role].rpc(name, params).execute()
                except SqlError as exc:
                    require(exc.code == "42501", "Wrong direct RPC denial")
                else:
                    raise AssertionError("Browser RPC exposed")
            try:
                readers[role].table("initial_division_snapshots").select("*").execute()
            except SqlError as exc:
                require(exc.code == "42501", "Wrong snapshot privacy denial")
            else:
                raise AssertionError("Private initialization snapshot exposed")
        catalog = client.execute(
            "select jsonb_build_object('rls',(select relrowsecurity from pg_class where oid='public.initial_division_snapshots'::regclass),"
            "'unsafe',(select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' "
            "and (proname like 'initial_assignment_%' or proname='api_admin_finalize_initial_assignment') "
            "and (prosecdef or proconfig is null or has_function_privilege('anon',p.oid,'EXECUTE') or has_function_privilege('authenticated',p.oid,'EXECUTE'))))"
        ).data
        require(
            catalog == {"rls": True, "unsafe": 0}, "New catalog/RLS security unsafe"
        )
        f.passed(
            "E08 private snapshot, browser RPC denial, fixed invoker helpers and RLS"
        )
    finally:
        for sid in f.seasons:
            client.table("initial_division_snapshots").delete().eq(
                "season_id", sid
            ).execute()
        f.cleanup()
    require(snapshot() == baseline, "E fixture residue or unrelated public drift")
    print(f"PASS E exact cleanup: {len(tables)} public tables", flush=True)


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--database", default="pokeapp_v2_validation_phase10_5e")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    try:
        validate(p.parse_args(), _psql_text)
    except SqlError as exc:
        raise AssertionError(f"Local SQL {exc.code}: {exc.message}") from exc
