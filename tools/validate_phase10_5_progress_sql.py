"""L: real disposable PostgreSQL observation scope, read-only effects and security."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from uuid import uuid4

from app.application.pokemon_identity import reconcile_parsed_save
from app.application.progress import progress_read
from app.domain.pokemon_identity import CaptureOrder
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import (
    LocalClient,
    SqlError,
    identifier,
    literal,
)


def validate(args):
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
    f = SeasonLifecycleFixtures(client, readers, auth, "phase10_5l_" + uuid4().hex)
    streams, checks = {}, []

    def passed(label):
        checks.append(label)
        print("PASS L " + label, flush=True)

    def update(table, id_, **fields):
        client.table(table).update(fields).eq("id", id_).execute()

    def observe(
        sid,
        player,
        flags=None,
        champion=None,
        *,
        game="B2",
        parser=3,
        promote=True,
        missing=False,
    ):
        stream, seq = streams.get(player["id"], (str(uuid4()), 0))
        streams[player["id"]] = stream, seq + 1
        digest = uuid4().hex + uuid4().hex
        version = f"pokeapp-reader/{parser};pkhex/24.11.11"
        primary = "johto" if game == "HG" else "unova"
        progress = (
            None
            if missing
            else dict(
                schema_version=1,
                primary_region=primary,
                regions=[
                    dict(
                        region=primary,
                        badge_flags=flags if flags is not None else [False] * 8,
                    )
                ],
                champion_defeated=champion,
            )
        )
        if game == "HG" and progress:
            progress["regions"].append(dict(region="kanto", badge_flags=[True] * 8))
        payload = dict(
            party=[dict(slot_number=i, pokemon=None) for i in range(1, 7)],
            boxes=[
                dict(
                    box_number=b,
                    slots=[dict(slot_number=i, pokemon=None) for i in range(1, 31)],
                )
                for b in range(1, 10)
            ],
            observed_progress=dict(
                schema_version=1,
                game=game,
                generation=4 if game == "HG" else 5,
                source_hash=digest,
                progress=progress,
            ),
        )
        saved = f.insert(
            "save_files",
            dict(
                season_id=sid,
                trainer_id=player["trainer_id"],
                storage_key=f.run_id + "/" + digest,
                original_filename="synthetic-no-bytes.sav",
                sha256=digest,
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
        reconcile_parsed_save(
            SupabasePokemonIdentityRepository(client),
            season_id=sid,
            trainer_id=player["trainer_id"],
            parsed_save_id=parsed["id"],
            capture_order=CaptureOrder(stream, seq + 1),
        )
        if promote:
            update("season_players", player["id"], current_save_file_id=saved["id"])
        return saved, parsed

    def read(sid, tid=None, using=client):
        # Preserve SQL NULL in the local psql transport, as PostgREST would.
        return using.execute(
            "select jsonb_build_object('value',public.observed_progress_read("
            + literal(sid)
            + "::uuid,"
            + (literal(tid) + "::uuid" if tid else "null")
            + "))"
        ).data["value"]

    def own(sid, player):
        rows = read(sid, player["trainer_id"])
        require(len(rows) == 1 and rows[0]["id"] == player["id"], "Cross-player read")
        return progress_read(rows[0])

    try:
        f.setup()
        sid, _ = f.season()
        a, b, c, d = f.players(sid)
        require(own(sid, a).state == "unknown", "No observation invented zero")
        require(
            read(str(uuid4())) is None and read(sid, str(uuid4())) == [],
            "Missing scope",
        )
        observe(sid, a, champion=False)
        require(
            own(sid, a).badges_count == 0 and own(sid, a).champion_defeated is False,
            "Observed zero lost",
        )
        observe(sid, b, missing=True)
        require(own(sid, b).state == "unknown", "Missing progress inferred")
        passed("unknown, observed zero, missing source and season scope")

        for champion in (True, False, None):
            observe(sid, a, [True] * 8, champion)
            require(
                own(sid, a).champion_defeated is champion, "Champion tri-state drift"
            )
        observe(sid, b, [True] * 8, True, parser=2)
        require(own(sid, b).champion_defeated is None, "Old reader forged Champion")
        observe(sid, c, [True] * 8, True, parser=1)
        require(own(sid, c).state == "unknown", "Unsupported reader accepted")
        passed(
            "Champion true/false/unknown, eight badges insufficient and reader compatibility"
        )

        sparse = [False, True, False, True] + [False] * 4
        observe(sid, a, sparse, game="HG")
        observed = own(sid, a)
        require(
            observed.badges_count == 10
            and observed.regions[0].earned_badges == [2, 4]
            and observed.regions[1].earned_badges == list(range(1, 9)),
            "Regional identity lost",
        )
        initial = (
            client.rpc("initial_assignment_observations", {"sid": sid}).execute().data
        )
        require(
            not next(r for r in initial if r["id"] == a["id"])["cap_reached"],
            "Count or Kanto satisfied J1",
        )
        observe(sid, a, [True, True] + [False] * 6)
        initial = (
            client.rpc("initial_assignment_observations", {"sid": sid}).execute().data
        )
        require(
            next(r for r in initial if r["id"] == a["id"])["cap_reached"],
            "First two primary badges lost",
        )
        passed(
            "sparse badge identity, HGSS second region and E first-two compatibility"
        )

        saved, _ = observe(sid, a, [True] * 8, True)
        observe(sid, a, [False] * 8, False, promote=False)
        require(own(sid, a).state == "unknown", "Stale pointer read as current")
        latest = max(
            f.rows(
                "pokemon_identity_revisions", season_id=sid, trainer_id=a["trainer_id"]
            ),
            key=lambda r: r["revision_number"],
        )
        update("season_players", a["id"], current_save_file_id=latest["save_file_id"])
        require(
            own(sid, a).badges_count == 0 and own(sid, a).champion_defeated is False,
            "Current regression ignored",
        )
        passed("stale pointer rejected and later regressed observation remains current")

        saved, parsed = observe(sid, a, [True] * 8, True)
        original = deepcopy(parsed["payload"])
        for field, value in (
            ("source_hash", "f" * 64),
            ("trainer_id", b["trainer_id"]),
            ("save_record_id", str(uuid4())),
        ):
            payload = deepcopy(original)
            payload[field] = value
            update("parsed_saves", parsed["id"], payload=payload)
            require(
                own(sid, a).state == "unknown", "Mismatched source accepted: " + field
            )
        for change in (
            dict(champion_defeated="true"),
            dict(regions=[dict(region="unova", badge_flags=[0] * 8)]),
        ):
            payload = deepcopy(original)
            payload["observed_progress"]["progress"].update(change)
            update("parsed_saves", parsed["id"], payload=payload)
            require(own(sid, a).state == "unknown", "Malformed progress accepted")
        update("parsed_saves", parsed["id"], payload=original)
        update("save_files", saved["id"], deleted_at="2026-10-08T00:00:00Z")
        require(own(sid, a).state == "unknown", "Deleted source accepted")
        update("save_files", saved["id"], deleted_at=None)
        # Composite FK already forbids another owner's pointer. An unowned caller
        # cannot manufacture current progress by choosing a different save.
        try:
            update("season_players", b["id"], current_save_file_id=saved["id"])
        except SqlError:
            pass
        else:
            require(own(sid, b).state == "unknown", "Foreign current save accepted")
        passed("malformed/deleted/unowned/hash-mismatched observation rejection")

        before = snapshot()
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: read(sid), range(6)))
        require(all(r == results[0] for r in results), "Read replay changed evidence")
        require(
            snapshot() == before, "Read mutated reward, competitive or historical state"
        )
        passed(
            "concurrent replay is read-only: rewards, history and all tables unchanged"
        )

        for reader in readers.values():
            try:
                read(sid, using=reader)
            except SqlError as exc:
                require(exc.code == "42501", "Unexpected browser denial")
            else:
                raise AssertionError("Browser called protected RPC")
        catalog = client.execute(
            "select jsonb_build_object('invoker',not prosecdef,'stable',provolatile='s',"
            "'path',proconfig=array['search_path=pg_catalog, public'],"
            "'service',has_function_privilege('service_role',oid,'EXECUTE'),"
            "'public',exists(select 1 from aclexplode(proacl) a where a.grantee=0)) "
            "from pg_proc where oid='public.observed_progress_read(uuid,uuid)'::regprocedure"
        ).data
        require(
            catalog
            == dict(invoker=True, stable=True, path=True, service=True, public=False),
            "Unsafe function catalog",
        )
        passed(
            "service-only invoker, fixed search_path, stable snapshot and browser denials"
        )
    finally:
        for sid in f.seasons:
            client.table("progress_reward_claims").delete().eq(
                "season_id", sid
            ).execute()
        f.cleanup()
        require(snapshot() == baseline, "L fixture residue")
        print(f"PASS L exact {len(tables)}-table restoration", flush=True)
    return dict(groups=len(checks), checks=checks, restored_tables=len(tables))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="55439")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    print(json.dumps(validate(parser.parse_args()), indent=2))
