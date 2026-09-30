"""LOCAL ONLY participant result security, races, rollback and admin correction."""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_matchday_fixtures import MatchdayFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate(args, sql):
    client = LocalClient(
        args
    )  # Rejects non-loopback/non-validation DB before fixtures.
    ids = {r: str(uuid4()) for r in ("admin", "other", "owner")}
    readers = {r: LocalClient(args, "authenticated", uid) for r, uid in ids.items()}
    readers["anon"] = LocalClient(args, "anon")
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        return {
            t: sorted(
                client.table(t).select("*").execute().data,
                key=lambda r: repr(sorted(r.items())),
            )
            for t in tables
        }

    baseline = snapshot()
    f = MatchdayFixtures(client, readers, ids, "phase10_5c_" + uuid4().hex)
    try:
        f.setup()
        sid, did = f.season()
        f.open(sid, did)
        own = next(
            p
            for p in f.rows("season_players", season_id=sid)
            if p["trainer_id"] == f.owner["id"]
        )
        state = f.ds(sid, did)
        match = next(
            m
            for m in state["matches"]
            if own["id"] not in (m["player_a_id"], m["player_b_id"])
        )

        def request(body=None, key=None, actor=None, season=None, day=None):
            r = dict(
                actor_trainer_id=actor or f.owner["id"],
                season_id=season or sid,
                resource_id=day or did,
            )
            if body is not None:
                r.update(body=body, idempotency_key=key or uuid4().hex)
            return r

        def body(winner=None):
            return dict(
                expected_results_revision=f.ds(sid, did)["results_revision"],
                results=[
                    dict(
                        match_id=match["id"],
                        winner_season_player_id=winner or match["player_a_id"],
                    )
                ],
            )

        def send(b, **kw):
            return f.matchdays.execute("participant_results", request(b, **kw))

        b = body()
        original_body = deepcopy(b)
        key = uuid4().hex
        receipt = send(b, key=key)
        require(not receipt["replayed"], "new mutation marked replay")
        replay = send(b, key=key)
        require(
            replay["replayed"] and replay["operation_id"] == receipt["operation_id"],
            "unstable replay",
        )
        f.reject(
            lambda: send(dict(b, expected_results_revision=99), key=key),
            "IDEMPOTENCY_CONFLICT",
        )
        f.reject(lambda: send(b), "STALE_REVISION")
        send(body(match["player_b_id"]))
        clear = body()
        clear["results"][0]["winner_season_player_id"] = None
        send(clear)
        require(
            next(m for m in f.ds(sid, did)["matches"] if m["id"] == match["id"])[
                "winner_id"
            ]
            is None,
            "ordinary clear unsupported",
        )
        f.passed(
            "C01 third-party participant entry/edit/clear and exact/conflicting replay/CAS"
        )

        f.reject(lambda: send(body(), actor=f.admin["id"]), "PARTICIPANT_REQUIRED")
        for status in ("retired", "abandoned", "disqualified"):
            client.table("season_players").update({"status": status}).eq(
                "id", own["id"]
            ).execute()
            f.reject(lambda: send(body()), "PARTICIPANT_INACTIVE")
            f.reject(lambda: send(b, key=key), "PARTICIPANT_INACTIVE")
            client.table("season_players").update({"status": "active"}).eq(
                "id", own["id"]
            ).execute()
        client.table("trainers").update({"globally_enabled": False}).eq(
            "id", f.owner["id"]
        ).execute()
        f.reject(lambda: send(body()), "TRAINER_DISABLED")
        client.table("trainers").update({"globally_enabled": True}).eq(
            "id", f.owner["id"]
        ).execute()
        membership = f.rows("division_memberships", season_player_id=own["id"])[0]
        client.table("division_memberships").update(
            {"eligibility_ends_before_matchday_number": 1}
        ).eq("id", membership["id"]).execute()
        f.reject(lambda: send(body()), "PARTICIPANT_INELIGIBLE")
        client.table("division_memberships").update(
            {"eligibility_ends_before_matchday_number": None}
        ).eq("id", membership["id"]).execute()
        f.reject(lambda: send(body(), day=str(uuid4())), "MATCHDAY_NOT_FOUND")
        f.reject(lambda: send(body(), season=f.draft()), "PARTICIPANT_REQUIRED")
        discarded = f.draft()
        client.table("seasons").update(
            {
                "status": "discarded",
                "discarded_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", discarded).execute()
        f.reject(lambda: send(body(), season=discarded), "SEASON_NOT_FOUND")
        f.reject(
            lambda: f.matchdays.execute("participant_state", request(season=discarded)),
            "SEASON_NOT_FOUND",
        )
        invalid = body(str(uuid4()))
        before = snapshot()
        f.reject(lambda: send(invalid), "INVALID_RESULTS")
        require(snapshot() == before, "invalid winner changed data")
        invalid = body()
        invalid["results"].append(
            dict(match_id=str(uuid4()), winner_season_player_id=None)
        )
        before = snapshot()
        f.reject(lambda: send(invalid), "INVALID_RESULTS")
        require(snapshot() == before, "invalid batch partially committed")
        f.passed(
            "C02 enabled/membership/eligibility/scope/winner negative matrix and exact batch rollback"
        )

        b = body()
        competitor = f.trainers[3]["id"]
        race = f.race(lambda: send(b), lambda: send(b, actor=competitor))
        f.one_winner(race, "STALE_REVISION")
        b = body()
        k = uuid4().hex
        race = f.race(lambda: send(b, key=k), lambda: send(b, key=k))
        require(
            race[0]["operation_id"] == race[1]["operation_id"],
            "same key concurrent duplicates",
        )
        b = body()
        altered = deepcopy(b)
        altered["results"][0]["winner_season_player_id"] = match["player_b_id"]
        k = uuid4().hex
        f.one_winner(
            f.race(lambda: send(b, key=k), lambda: send(altered, key=k)),
            "IDEMPOTENCY_CONFLICT",
        )
        f.passed("C03 separate-session conflicting/same-key/different-body concurrency")

        for target, condition in [
            ("matches", "true"),
            ("matchdays", "true"),
            ("activity_events", "new.type='MATCHDAY_PARTICIPANT_RESULTS'"),
            (
                "admin_operation_receipts",
                "new.operation_scope like 'matchday_participant_results:%'",
            ),
        ]:
            b = body()
            before = snapshot()
            sql(
                args,
                f"create function public.__phase10_5c_fail() returns trigger language plpgsql as $$ begin if new.season_id={literal(sid)}::uuid and ({condition}) then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; create trigger phase10_5c_fail after insert or update on public.{target} for each row execute function public.__phase10_5c_fail();",
            )
            try:
                try:
                    send(b)
                except PersistenceError as exc:
                    require(
                        getattr(exc.__cause__, "code", None) == "P0001",
                        "wrong injected failure",
                    )
                else:
                    raise AssertionError("injection did not fire")
                require(snapshot() == before, "partial write at " + target)
            finally:
                sql(
                    args,
                    f"drop trigger phase10_5c_fail on public.{target}; drop function public.__phase10_5c_fail();",
                )
        f.passed("C04 four exact full-public-table rollback boundaries")

        f.results(sid, did)
        b = body(match["player_b_id"])
        race = f.race(lambda: send(b), lambda: f.close(sid, did))
        require(
            all(
                isinstance(x, dict)
                or x
                in (
                    "STALE_REVISION",
                    "STALE_INPUTS",
                    "MATCHDAY_NOT_CURRENT",
                    "ALREADY_CLOSED",
                )
                for x in race
            ),
            "unexpected close race",
        )
        if f.ds(sid, did)["state"] != "closed":
            f.close(sid, did)
        frozen = snapshot()
        f.reject(lambda: send(body()), "MATCHDAY_NOT_CURRENT", "ALREADY_CLOSED")
        require(snapshot() == frozen, "closed mutation changed data")
        replay = send(original_body, key=key)
        require(
            replay["operation_id"] == receipt["operation_id"],
            "replay after close not stable",
        )
        before_revision = f.ds(sid, did)["snapshot_revision"]
        f.md("correct", sid, did, f.correction(sid, did))
        require(
            f.ds(sid, did)["snapshot_revision"] == before_revision + 1,
            "admin correction no longer works",
        )
        nxt = f.ds(sid, did)["current_matchday_id"]
        f.open(sid, nxt)
        f.reject(lambda: send(body()), "MATCHDAY_NOT_CURRENT", "ALREADY_CLOSED")
        f.passed(
            "C05 result/close concurrency, frozen history, replay after close, distinct admin correction/later day"
        )

        envelope = dict(operation="results", request=request(body()))
        for role, c in readers.items():
            try:
                c.rpc("api_participant_matchday", {"p_request": envelope}).execute()
            except Exception as exc:
                require(
                    getattr(exc, "code", None) == "42501",
                    "browser RPC privilege not denied " + role,
                )
            else:
                raise AssertionError("browser RPC executable " + role)
            try:
                c.table("matches").update({"winner_id": None}).eq(
                    "id", match["id"]
                ).execute()
            except Exception as exc:
                require(
                    getattr(exc, "code", None) == "42501",
                    "browser table mutation not denied " + role,
                )
            else:
                raise AssertionError("browser writes results " + role)
        catalog = client.execute(
            "select jsonb_build_object('definer',prosecdef,'path',proconfig,'acl',has_function_privilege('authenticated',oid,'execute') or has_function_privilege('anon',oid,'execute')) from pg_proc where oid='public.api_participant_matchday(jsonb)'::regprocedure"
        ).data
        require(
            not catalog["definer"]
            and not catalog["acl"]
            and catalog["path"] == ["search_path=pg_catalog, public"],
            "unsafe RPC catalog",
        )
        events = f.rows(
            "activity_events", season_id=sid, type="MATCHDAY_PARTICIPANT_RESULTS"
        )
        require(
            events
            and all(
                "before" in e["payload"] and "after" in e["payload"] for e in events
            ),
            "missing audit result evidence",
        )
        f.passed(
            "C06 browser table/RPC denial, invoker/search_path and before/after audit"
        )
    finally:
        f.cleanup()
    require(snapshot() == baseline, "fixture residue or baseline drift")
    print(
        "PASS participant results exact cleanup across "
        + str(len(tables))
        + " public tables",
        flush=True,
    )


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--database", default="pokeapp_v2_validation_phase10_5c")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    validate(p.parse_args(), _psql_text)
