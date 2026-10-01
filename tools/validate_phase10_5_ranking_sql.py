"""LOCAL ONLY: sporting ties, audited resolutions, frozen corrections and lifecycle."""

from copy import deepcopy
import json
from uuid import uuid4

from app.application.daily_ranking import LEGACY_RULE, RULE, RankingDecisionRequired
from app.application.matchdays import plan_close
from app.repositories.errors import PersistenceError
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate(args, sql):
    client = LocalClient(args)
    ids = {r: str(uuid4()) for r in ("admin", "other", "owner")}
    readers = {r: LocalClient(args, "authenticated", uid) for r, uid in ids.items()}
    readers["anon"] = LocalClient(args, "anon")
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        # One SQL statement: exact full-row content across every public table.
        pieces = [
            "select '"
            + t
            + "' as name,coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]') as rows from public.\""
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
    f = SeasonLifecycleFixtures(client, readers, ids, "phase10_5d_" + uuid4().hex)

    def setup_day(*, movement=0, gift=False, equal_rewards=True, total=1):
        for old in f.seasons:
            if f.rows("seasons", id=old)[0]["status"] == "active":
                client.table("seasons").update({"status": "draft"}).eq(
                    "id", old
                ).execute()
        sid = f.draft()
        for trainer in f.trainers[1:]:
            f.add(sid, trainer["id"])
        cfg = f.config(sid)
        cfg.update(
            total_matchdays=total,
            movement_count=movement,
            scoring={
                str(i): (3 if equal_rewards and i >= 4 else 7 - i) for i in range(1, 7)
            },
            coin_rewards={
                str(i): (5 if equal_rewards and i >= 4 else 7 - i) for i in range(1, 7)
            },
            rules=dict(team_lock_required=True, last_b_gets_steal=gift),
        )
        cid = f.call("create_config", sid, cfg)["resource_id"]
        state = f.state(sid)
        players = sorted(p["id"] for p in state["participants"])
        f.call(
            "initial_divisions",
            sid,
            dict(
                config_version_id=cid,
                assignments={"A": players[:3], "B": players[3:]},
                expected_roster_revision=state["roster_revision"],
                expected_setup_revision=state["setup_revision"],
            ),
        )
        f.call(
            "prepare", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]}
        )
        f.call(
            "activate", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]}
        )
        did = f.state(sid)["current_matchday_id"]
        f.open(sid, did)
        state = f.ds(sid, did)
        cycle = {
            (players[3], players[4]): players[3],
            (players[4], players[5]): players[4],
            (players[3], players[5]): players[5],
        }
        f.md(
            "results",
            sid,
            did,
            dict(
                expected_results_revision=state["results_revision"],
                results=[
                    dict(
                        match_id=m["id"],
                        winner_season_player_id=cycle.get(
                            tuple(sorted((m["player_a_id"], m["player_b_id"]))),
                            min(m["player_a_id"], m["player_b_id"]),
                        ),
                    )
                    for m in state["matches"]
                ],
            ),
        )
        return sid, did, players

    def review(sid, did, body=None, op="close"):
        before = snapshot()
        try:
            f.md(
                op,
                sid,
                did,
                body
                or {"expected_results_revision": f.ds(sid, did)["results_revision"]},
            )
        except RankingDecisionRequired as exc:
            require(exc.code == "RANKING_TIE_UNRESOLVED", "wrong tie rejection")
            result = exc.review
        else:
            raise AssertionError("Consequential tie silently resolved")
        require(snapshot() == before, "Unresolved close mutated tables")
        return result

    def decision(value):
        orders = [
            dict(
                player_ids=list(reversed(g["player_ids"])),
                reason="External fixture agreement",
            )
            for g in value["groups"]
            if g["consequences"]
        ]
        orders.sort(key=lambda o: sorted(o["player_ids"]))
        return dict(input_hash=value["input_hash"], orders=orders)

    try:
        f.setup()
        sid, did, players = setup_day()
        f.close(sid, did)
        snap = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]
        tied = [r for r in snap["standings"] if r["division_id"] == "B"]
        require(
            [r["position"] for r in tied] == [4, 4, 4], "Fake unique neutral positions"
        )
        require(
            {r["metadata"]["allocation_position"] for r in tied} == {4, 5, 6},
            "Integrity slots incomplete",
        )
        require(
            all(
                r["metadata"]["tie_status"] == "unresolved_neutral"
                and r["coins_awarded"] == 5
                for r in tied
            ),
            "Neutral rewards inconsistent",
        )
        require(not f.rows("matchday_movements", season_id=sid), "Final day movement")
        frozen = deepcopy(f.rows("matchday_snapshot_revisions", matchday_id=did))
        f.life("finish", sid)
        f.life("archive", sid)
        require(
            f.rows("matchday_snapshot_revisions", matchday_id=did) == frozen,
            "Lifecycle rewrote sporting facts",
        )
        archive = f.rows("season_archive_snapshots", season_id=sid)[0]
        require(
            "unresolved_neutral" in json.dumps(archive),
            "Archive lost shared sporting truth",
        )
        require(
            len(f.rows("hall_of_fame_entries", season_id=sid)) == 1,
            "Legacy lifecycle compatibility failed",
        )
        f.passed(
            "D01 neutral shared positions, equal rewards, final close/finish/archive and frozen history"
        )

        for kwargs, effect in [
            (dict(movement=1, total=2), "movement"),
            (dict(equal_rewards=False), "points"),
            (dict(gift=True), "last_b_reward"),
        ]:
            sid, did, players = setup_day(**kwargs)
            pending = review(sid, did)
            require(
                effect in pending["groups"][0]["consequences"],
                "Consequential boundary missed",
            )
        f.passed(
            "D02 movement/reward/last-B boundary rejects before every public write"
        )

        body = dict(
            expected_results_revision=f.ds(sid, did)["results_revision"],
            tie_resolution=decision(pending),
        )
        key = uuid4().hex
        same = f.race(
            lambda: f.md("close", sid, did, body, key=key),
            lambda: f.md("close", sid, did, body, key=key),
        )
        require(
            same[0]["operation_id"] == same[1]["operation_id"],
            "Resolution race duplicated close",
        )
        snap = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]
        require(
            snap["inputs"]["ranking"]["resolutions"]
            == body["tie_resolution"]["orders"],
            "Decision audit lost",
        )
        require(
            snap["last_b_player_id"]
            == body["tie_resolution"]["orders"][0]["player_ids"][-1],
            "Technical order selected gift",
        )
        require(
            len(f.rows("purchases", origin_matchday_id=did)) == 1, "Reward duplicated"
        )
        first = deepcopy(f.rows("matchday_snapshot_revisions", matchday_id=did)[0])
        # All winners reversed: B remains a cycle, so correction needs its own bound review.
        correction = f.correction(sid, did)
        corrected_review = review(sid, did, correction, "correct")
        correction["tie_resolution"] = decision(corrected_review)
        ck = uuid4().hex
        receipt = f.md("correct", sid, did, correction, key=ck)
        require(
            f.md("correct", sid, did, correction, key=ck)["operation_id"]
            == receipt["operation_id"],
            "Correction replay failed",
        )
        require(
            next(
                r
                for r in f.rows("matchday_snapshot_revisions", matchday_id=did)
                if r["revision"] == 1
            )
            == first,
            "Frozen revision changed",
        )
        require(
            f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]["inputs"][
                "ranking"
            ]["rule"]
            == RULE,
            "Correction rule lost",
        )
        f.passed(
            "D03 external gift order, same-key concurrent close, correction/replay and immutable prior revision"
        )

        sid, did, players = setup_day(movement=1, total=2)
        pending = review(sid, did)
        body = dict(
            expected_results_revision=f.ds(sid, did)["results_revision"],
            tie_resolution=decision(pending),
        )
        original = deepcopy(body)
        # The live death input changes without touching results: old human decision is stale.
        client.table("season_player_stats").update({"revived_after_wipe": 1}).eq(
            "season_player_id", players[0]
        ).execute()
        before = snapshot()
        try:
            f.md("close", sid, did, body)
        except RankingDecisionRequired as exc:
            require(exc.code == "RANKING_REVIEW_STALE", "Stale decision accepted")
        else:
            raise AssertionError("Stale decision accepted")
        require(snapshot() == before, "Stale decision mutated tables")
        pending = review(sid, did)
        body["tie_resolution"] = decision(pending)
        require(body != original, "Review hash did not bind adjusted death inputs")
        altered = deepcopy(body)
        altered["tie_resolution"]["orders"][0]["player_ids"].reverse()
        race = f.race(
            lambda: f.md("close", sid, did, body),
            lambda: f.md("close", sid, did, altered),
        )
        f.one_winner(
            race,
            "ALREADY_CLOSED",
            "MATCHDAY_NOT_CURRENT",
            "STALE_INPUTS",
            "STALE_REVISION",
        )
        official = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]
        promoted = official["inputs"]["ranking"]["resolutions"][0]["player_ids"][0]
        require(
            promoted in official["new_divisions"]["A"],
            "Movement ignored explicit resolution",
        )
        f.passed(
            "D04 changed-death review freshness, competing external decisions and promotion correctness"
        )

        sid, did, players = setup_day(equal_rewards=False)
        pending = review(sid, did)
        body = dict(
            expected_results_revision=f.ds(sid, did)["results_revision"],
            tie_resolution=decision(pending),
        )
        for table in (
            "matchday_snapshot_revisions",
            "coin_transactions",
            "activity_events",
            "admin_operation_receipts",
        ):
            before = snapshot()
            sql(
                args,
                f"create function public.phase10_5d_fail() returns trigger language plpgsql as $$ begin raise exception 'local injected failure'; end $$; create trigger phase10_5d_fail after insert on public.{table} for each row execute function public.phase10_5d_fail();",
            )
            try:
                try:
                    f.md("close", sid, did, body)
                except PersistenceError:
                    pass
                else:
                    raise AssertionError("Injected failure did not abort")
                require(snapshot() == before, "Partial commit after " + table)
            finally:
                sql(
                    args,
                    f"drop trigger phase10_5d_fail on public.{table}; drop function public.phase10_5d_fail();",
                )
        f.passed(
            "D05 four exact all-public-table rollback boundaries after resolved planning"
        )

        # Build an actual pre-D-shaped snapshot using the retained old commit helper
        # locally; it is deliberately inaccessible to browsers. No remote fixture.
        request = dict(
            actor_trainer_id=f.admin["id"],
            season_id=sid,
            resource_id=did,
            body={"expected_results_revision": f.ds(sid, did)["results_revision"]},
            idempotency_key=uuid4().hex,
        )
        ctx = (
            client.rpc("matchday_context_v034", {"op": "close", "r": request})
            .execute()
            .data
        )
        ctx["ranking_rule"] = LEGACY_RULE
        old_plan = plan_close(ctx)
        client.rpc(
            "matchday_commit_close_v034",
            {"op": "close", "r": request, "ctx": ctx, "plan": old_plan},
        ).execute()
        original_snapshot = deepcopy(
            f.rows("matchday_snapshot_revisions", matchday_id=did)[0]
        )
        f.md("correct", sid, did, f.correction(sid, did))
        history = f.rows("matchday_snapshot_revisions", matchday_id=did)
        require(
            next(r for r in history if r["revision"] == 1) == original_snapshot,
            "Old snapshot changed",
        )
        corrected = next(r for r in history if r["revision"] == 2)["snapshot"]
        require(
            corrected["inputs"]["ranking"]["rule"] == LEGACY_RULE,
            "Old correction got new sporting rule",
        )
        require(
            all(p["dead_count"] == 0 for p in corrected["inputs"]["players"]),
            "Live deaths rewrote frozen correction inputs",
        )
        client.table("season_player_stats").update({"revived_after_wipe": 50}).eq(
            "season_player_id", players[-1]
        ).execute()
        f.reject(
            lambda: f.md("correct", sid, did, f.correction(sid, did)),
            "CORRECTION_WINDOW_CLOSED",
        )
        require(
            f.rows("matchday_snapshot_revisions", matchday_id=did) == history,
            "Later live deaths changed frozen history",
        )
        f.passed(
            "D06 actual old-shaped snapshot correction retains legacy rule and frozen deaths"
        )

        names = [
            "matchday_context",
            "matchday_context_v034",
            "matchday_commit_close",
            "matchday_commit_close_v034",
            "lifecycle_standings",
            "lifecycle_final_source",
        ]
        catalog = client.execute(
            "select jsonb_agg(jsonb_build_object('name',proname,'definer',prosecdef,'path',proconfig,'browser',has_function_privilege('authenticated',p.oid,'execute') or has_function_privilege('anon',p.oid,'execute'),'service',has_function_privilege('service_role',p.oid,'execute'))) from pg_proc p join pg_namespace n on n.oid=pronamespace where n.nspname='public' and proname in ("
            + ",".join(map(literal, names))
            + ")"
        ).data
        require(
            len(catalog) == len(names)
            and all(
                not r["definer"]
                and not r["browser"]
                and r["service"]
                and r["path"] == ["search_path=pg_catalog, public"]
                for r in catalog
            ),
            "Unsafe D function ACL",
        )
        f.passed(
            "D07 all six new/replaced helper catalog grants, invoker and fixed search path"
        )
    finally:
        f.cleanup()
    require(snapshot() == baseline, "D fixture residue or baseline drift")
    print(f"PASS D exact cleanup: {len(tables)} public tables", flush=True)


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--database", default="pokeapp_v2_validation_phase10_5d")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    validate(p.parse_args(), _psql_text)
