"""LOCAL ONLY final alignment: cutover, participant authority and first fixation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from uuid import uuid4

from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence
from app.repositories.errors import ConflictError, PersistenceError
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from app.repositories.supabase.team_locks import SupabaseTeamLockRepository
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import (
    LocalClient,
    SqlError,
    identifier,
    literal,
)


def validate(args, sql):
    client = LocalClient(args)
    auth = {r: str(uuid4()) for r in ("admin", "owner", "other")}
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
    f = SeasonLifecycleFixtures(client, readers, auth, "phase10_5final_" + uuid4().hex)
    streams, sources, checks, rollbacks = {}, {}, [], []

    def passed(label):
        checks.append(label)
        print("PASS FINAL " + label, flush=True)

    def update(table, row_id, **body):
        return client.table(table).update(body).eq("id", row_id).execute().data

    def observe(
        sid,
        p,
        badges=None,
        champion=None,
        *,
        parser=3,
        location=8,
        promote=True,
        before_identity=False,
        malformed=None,
    ):
        stream, seq = streams.get(p["id"], (str(uuid4()), 0))
        seq += 1
        streams[p["id"]] = stream, seq
        hash_ = uuid4().hex + uuid4().hex
        evidence = PokemonIdentityEvidence(
            1, 5, 100, 12345, 6789, 20, 2, "Fixture", 0, ivs=(17, 0, 0, 0, 0, 0)
        )
        mon = dict(
            species="Gastly",
            identity_evidence=asdict(evidence),
            legacy_fingerprints=["i-100"],
        )
        payload = dict(
            party=[
                dict(slot_number=i, pokemon=mon if location == 0 and i == 1 else None)
                for i in range(1, 7)
            ],
            boxes=[
                dict(
                    box_number=b,
                    slots=[
                        dict(
                            slot_number=i,
                            pokemon=mon if b == location and i == 1 else None,
                        )
                        for i in range(1, 31)
                    ],
                )
                for b in range(1, 10)
            ],
            observed_progress=dict(
                schema_version=1,
                game="B2",
                generation=5,
                source_hash=hash_,
                progress=None,
            ),
        )
        if badges is not None:
            payload["observed_progress"]["progress"] = dict(
                schema_version=1,
                primary_region="unova",
                regions=[
                    dict(region="unova", badge_flags=[i < badges for i in range(8)])
                ],
                champion_defeated=champion,
            )
        if malformed:
            malformed(payload)
        version = f"pokeapp-reader/{parser};pkhex/24.11.11"
        saved = f.insert(
            "save_files",
            dict(
                season_id=sid,
                trainer_id=p["trainer_id"],
                storage_key=f.run_id + "/" + hash_,
                original_filename="synthetic-no-bytes.sav",
                sha256=hash_,
                parser_status="parsed",
                parser_version=version,
            ),
        )
        parsed = f.insert(
            "parsed_saves",
            dict(
                save_file_id=saved["id"],
                parser_version=version,
                schema_version=1,
                payload=payload,
            ),
        )
        if promote and before_identity:
            update("season_players", p["id"], current_save_file_id=saved["id"])
        result = reconcile_parsed_save(
            SupabasePokemonIdentityRepository(client),
            season_id=sid,
            trainer_id=p["trainer_id"],
            parsed_save_id=parsed["id"],
            capture_order=CaptureOrder(stream, seq),
        )
        if promote and not before_identity:
            update("season_players", p["id"], current_save_file_id=saved["id"])
        sources[p["id"]] = saved, parsed, result
        return saved

    def rules(sid):
        return (
            client.rpc(
                "api_admin_live_rules_read",
                {"p_request": dict(season_id=sid, actor_trainer_id=f.admin["id"])},
            )
            .execute()
            .data
        )

    def body(sid, badge=5, champion=13):
        r = rules(sid)
        return dict(
            expected_revision=r["revision"],
            expected_config_revision=r["config_revision"],
            badge_reward_coins=badge,
            game_completion_reward_coins=champion,
        )

    def reject(action, *codes):
        before = snapshot()
        try:
            action()
        except (SqlError, PersistenceError, ConflictError) as exc:
            code = getattr(exc, "code", None)
            cause = getattr(exc, "__cause__", None)
            message = getattr(exc, "message", None) or getattr(cause, "message", None)
            require(
                code in codes or message in codes,
                f"Unexpected rejection {code}: {message}, expected {codes}",
            )
        else:
            raise AssertionError("Expected rejection " + str(codes))
        require(snapshot() == before, "Rejected operation changed public data")

    def injected(sid, table, action):
        before = snapshot()
        sql(
            args,
            f"create function public.__final_fail() returns trigger language plpgsql as $$ begin raise exception 'Final rollback'; end $$; create trigger __final_fail after insert or update on public.{table} for each row execute function public.__final_fail();",
        )
        try:
            try:
                action()
            except (SqlError, PersistenceError):
                pass
            else:
                raise AssertionError("Missing forced rollback " + table)
            require(snapshot() == before, "Partial state after rollback " + table)
            rollbacks.append(table)
        finally:
            sql(args, "drop function public.__final_fail() cascade;")

    try:
        f.setup()
        sid, did = f.season(1)
        p = f.players(sid)[0]
        require(rules(sid)["badge_reward_coins"] == 4, "Legacy rule fallback")
        observe(sid, p, 1, False)
        claims = f.rows("progress_reward_claims", season_id=sid)
        require([r["amount"] for r in claims] == [4], "Initial observation reward")
        request, key = body(sid), uuid4().hex
        result = f.call("live_rules_update", sid, request, key=key)
        require(
            f.call("live_rules_update", sid, request, key=key)["operation_id"]
            == result["operation_id"],
            "Rule replay",
        )
        require(
            f.rows("progress_reward_claims", season_id=sid) == claims,
            "Historical reward repriced",
        )
        observe(sid, p, 2, False)
        require(
            sorted(r["amount"] for r in f.rows("progress_reward_claims", season_id=sid))
            == [4, 5],
            "Prospective badge rule",
        )
        f.call("live_rules_update", sid, body(sid, 0, 0))
        observe(sid, p, 3, True)
        claims = f.rows("progress_reward_claims", season_id=sid)
        require(
            sorted(r["amount"] for r in claims) == [0, 0, 4, 5],
            "Observed zero rule/Champion",
        )
        f.call("live_rules_update", sid, body(sid, 8, 18))
        observe(sid, p, 3, True)
        require(
            f.rows("progress_reward_claims", season_id=sid) == claims,
            "Zero reward repaid after rule change",
        )
        reject(lambda: f.call("live_rules_update", sid, request), "STALE_REVISION")
        reject(
            lambda: f.call("live_rules_update", sid, body(sid), actor=p["trainer_id"]),
            "ADMIN_REQUIRED",
        )
        for bad in (True, -1, 1.5, "5", 2147483648):
            reject(
                lambda: f.call(
                    "live_rules_update", sid, dict(body(sid), badge_reward_coins=bad)
                ),
                "INVALID_REQUEST",
            )
        race_body = body(sid, 7, 17)
        outcomes = f.race(
            lambda: f.call("live_rules_update", sid, race_body),
            lambda: f.call("live_rules_update", sid, race_body, actor=f.admin2["id"]),
        )
        f.one_winner(outcomes, "STALE_REVISION")
        for table in (
            "season_reward_rule_revisions",
            "season_admin_state",
            "activity_events",
            "admin_operation_receipts",
        ):
            injected(sid, table, lambda: f.call("live_rules_update", sid, body(sid)))
        # Race cutover with a batch of two newly observed badges: one rule for the entire batch.
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [
                pool.submit(observe, sid, p, 5, True),
                pool.submit(f.call, "live_rules_update", sid, body(sid, 9, 19)),
            ]
            for job in jobs:
                job.result()
        latest = [
            c
            for c in f.rows("progress_reward_claims", season_id=sid)
            if c["id"] not in {r["id"] for r in claims}
        ]
        require(
            len(latest) == 2
            and len({c["amount"] for c in latest}) == 1
            and latest[0]["amount"] in (7, 9),
            "Observation crossed reward cutover",
        )
        passed(
            "prospective rewards, zero, immutable old claims, CAS/replay/race and four rollback boundaries"
        )

        participant = p["trainer_id"]
        outsider = f.trainers[-1]["id"]
        reject(lambda: f.open(sid, did, actor=outsider), "PARTICIPANT_REQUIRED")
        update("season_players", p["id"], status="retired")
        reject(lambda: f.open(sid, did, actor=participant), "PARTICIPANT_INACTIVE")
        update("season_players", p["id"], status="active")
        open_body = dict(expected_revision=f.ds(sid, did)["revision"])
        key = uuid4().hex
        race = f.race(
            lambda: f.md("open", sid, did, open_body, key=key, actor=participant),
            lambda: f.md("open", sid, did, open_body, key=key, actor=participant),
        )
        require(
            race[0]["operation_id"] == race[1]["operation_id"],
            "Participant open replay",
        )
        reject(
            lambda: f.md(
                "cancel",
                sid,
                did,
                dict(
                    expected_revision=f.ds(sid, did)["revision"], reason="Exceptional"
                ),
                actor=participant,
            ),
            "ADMIN_REQUIRED",
        )
        f.results(sid, did)
        close_body = dict(expected_results_revision=f.ds(sid, did)["results_revision"])
        reject(
            lambda: f.md(
                "close",
                sid,
                did,
                dict(close_body, tie_resolution={}),
                actor=participant,
            ),
            "ADMIN_REQUIRED",
        )
        reject(
            lambda: f.md(
                "close",
                sid,
                did,
                dict(close_body, expected_results_revision=0),
                actor=participant,
            ),
            "STALE_REVISION",
        )
        # This fixture uses deterministic scores and authoritative deaths, never an arbitrary decision.
        for table in (
            "matchday_snapshots",
            "coin_transactions",
            "admin_operation_receipts",
        ):
            injected(
                sid,
                table,
                lambda: f.md("close", sid, did, close_body, actor=participant),
            )
        key = uuid4().hex
        race = f.race(
            lambda: f.md("close", sid, did, close_body, key=key, actor=participant),
            lambda: f.md("close", sid, did, close_body, key=key, actor=participant),
        )
        require(
            race[0]["operation_id"] == race[1]["operation_id"],
            "Participant close replay",
        )
        championship = f.championship(sid, actor=participant)
        if championship["state"] == "bo3_required":
            f.life(
                "championship_bo3",
                sid,
                dict(
                    expected_revision=championship["setup_revision"],
                    input_hash=championship["input_hash"],
                    winner_season_player_id=championship["tied_player_ids"][0],
                    reason="External fixture decision",
                ),
            )
            championship = f.championship(sid, actor=participant)
        finish = dict(
            expected_revision=championship["setup_revision"],
            input_hash=championship["input_hash"],
        )
        for table in ("league_finalizations", "seasons", "admin_operation_receipts"):
            injected(
                sid, table, lambda: f.life("finish", sid, finish, actor=participant)
            )
        key = uuid4().hex
        race = f.race(
            lambda: f.life("finish", sid, finish, key=key, actor=participant),
            lambda: f.life("finish", sid, finish, key=key, actor=participant),
        )
        require(
            race[0]["operation_id"] == race[1]["operation_id"],
            "Participant finish replay",
        )
        reject(lambda: f.life("archive", sid, actor=participant), "ADMIN_REQUIRED")
        reject(
            lambda: f.call("live_rules_update", sid, body(sid)), "CONFIG_WINDOW_CLOSED"
        )
        passed(
            "eligible non-admin open/close/finish, denial, replay, races and six rollback boundaries"
        )

        locks = SupabaseTeamLockRepository(client)
        sid, did = f.season()
        mutation = f.lock_source(sid, did)
        injected(
            sid,
            "team_lock_first_fixations",
            lambda: locks.upsert_with_activity(mutation),
        )
        original = locks.upsert_with_activity(mutation)
        evidence = f.rows("team_lock_first_fixations", lock_id=original.id)[0]
        require(evidence["timing_status"] == "on_time", "Before-start first fixation")
        injected(sid, "matchday_start_evidence", lambda: f.open(sid, did))
        f.open(sid, did)
        first_start = f.rows("matchday_start_evidence", matchday_id=did)[0]
        locks.upsert_with_activity(mutation)
        require(
            f.rows("team_lock_first_fixations", lock_id=original.id) == [evidence],
            "Replacement erased first fixation",
        )
        f.md(
            "cancel",
            sid,
            did,
            dict(
                expected_revision=f.ds(sid, did)["revision"],
                reason="Local cancellation",
            ),
        )
        f.open(sid, did)
        require(
            f.rows("matchday_start_evidence", matchday_id=did) == [first_start],
            "Reopening rewrote first start",
        )
        second = next(x for x in f.players(sid) if x["id"] != mutation.season_player_id)
        saved = f.rows("save_files", id=mutation.save_file_id)[0]
        saved.pop("id")
        saved["trainer_id"] = second["trainer_id"]
        saved["storage_key"] += "-other"
        second_save = f.insert("save_files", saved)
        parsed = f.insert(
            "parsed_saves",
            dict(
                save_file_id=second_save["id"],
                parser_version="phase8h",
                payload=mutation.parsed_payload,
            ),
        )
        late = replace(
            mutation,
            trainer_id=second["trainer_id"],
            season_player_id=second["id"],
            save_file_id=second_save["id"],
            parsed_save_id=parsed["id"],
        )
        late_record = locks.upsert_with_activity(late)
        require(
            f.rows("team_lock_first_fixations", lock_id=late_record.id)[0][
                "timing_status"
            ]
            == "late",
            "Late first fixation",
        )
        f.results(sid, did)
        locks.upsert_with_activity(late)
        require(
            f.rows("team_lock_first_fixations", lock_id=late_record.id)[0][
                "timing_status"
            ]
            == "late",
            "Post-combat replacement cutoff or timing reset",
        )
        f.close(sid, did)
        reject(lambda: locks.upsert_with_activity(late), "matchday_not_lockable")
        # Simulate pre-041 absence only on disposable fixtures; old replacement remains unknown.
        sid2, did2 = f.season()
        old = f.lock_source(sid2, did2)
        old_record = locks.upsert_with_activity(old)
        client.table("team_lock_first_fixations").delete().eq(
            "lock_id", old_record.id
        ).execute()
        client.table("matchday_start_evidence").delete().eq(
            "matchday_id", did2
        ).execute()
        locks.upsert_with_activity(old)
        require(
            f.rows("public_team_locks", id=old_record.id)[0]["timing_status"]
            == "unknown",
            "Fabricated legacy timing",
        )
        passed(
            "first on-time/late, no combat cutoff, replacements/cancellation/reopen, closed history and legacy unknown"
        )

        for table in (
            "season_reward_rule_revisions",
            "team_lock_first_fixations",
            "matchday_start_evidence",
        ):
            require(
                client.execute(
                    "select to_jsonb(relrowsecurity) from pg_class where oid="
                    + literal("public." + table)
                    + "::regclass"
                ).data,
                "Missing RLS",
            )
            for reader in readers.values():
                reject(lambda: reader.table(table).select("*").execute(), "42501")
        for reader in readers.values():
            reject(
                lambda: reader.rpc("live_reward_rules", dict(sid=sid2)).execute(),
                "42501",
            )
            reject(
                lambda: reader.rpc(
                    "league_operation_principal", dict(actor=participant, sid=sid2)
                ).execute(),
                "42501",
            )
        passed("browser table/helper denial including admin JWT; private RLS")
    finally:
        for sid in f.seasons:
            client.table("progress_reward_claims").delete().eq(
                "season_id", sid
            ).execute()
            client.table("season_reward_rule_revisions").delete().eq(
                "season_id", sid
            ).execute()
        f.cleanup()
        require(snapshot() == baseline, "Final fixtures changed baseline")
        print(f"PASS FINAL exact {len(tables)}-table restoration", flush=True)
    return dict(
        groups=len(checks),
        checks=checks,
        rollback_boundaries=rollbacks,
        restored_tables=len(tables),
    )


if __name__ == "__main__":
    import argparse
    import json
    from tools.validate_supabase_v2_schema import _psql_text

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    print(json.dumps(validate(p.parse_args(), _psql_text), indent=2))
