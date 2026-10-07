"""Disposable loopback PostgreSQL: I economy, observations, replay and rollback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import Barrier
from uuid import uuid4

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
    f = SeasonLifecycleFixtures(client, readers, auth, "phase10_5i_" + uuid4().hex)
    streams, sources = {}, {}
    checks, rollbacks = [], []

    def passed(label):
        checks.append(label)
        print("PASS I " + label, flush=True)

    def race(*actions):
        barrier = Barrier(len(actions))

        def run(action):
            barrier.wait(timeout=30)
            try:
                return action()
            except SqlError as exc:
                return exc.message

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def rejected(action, *codes):
        try:
            action()
        except SqlError as exc:
            require(
                exc.message in codes or exc.code in codes,
                f"Unexpected SQL rejection {exc.code}: {exc.message}",
            )
        else:
            raise AssertionError("Expected rejection: " + str(codes))

    def update(table, row_id, **body):
        return client.table(table).update(body).eq("id", row_id).execute().data

    def credit(sid, p, amount):
        return f.insert(
            "coin_transactions",
            dict(
                season_id=sid,
                trainer_id=p["trainer_id"],
                season_player_id=p["id"],
                amount=amount,
                transaction_type="admin_adjustment",
            ),
        )

    def balance(sid, p):
        rows = f.rows("public_coin_balances", season_id=sid, trainer_id=p["trainer_id"])
        return rows[0]["balance"] if rows else "0"

    def purchase(sid, p, item, key=None):
        return (
            client.rpc(
                "api_create_normal_purchase",
                dict(
                    p_season_id=sid,
                    p_trainer_id=p["trainer_id"],
                    p_item_id=item,
                    p_idempotency_key=key or uuid4().hex,
                    p_confirm_base_price=True,
                ),
            )
            .execute()
            .data
        )

    def promotional(sid, p, promo, key=None):
        return (
            client.rpc(
                "api_create_promotional_purchase",
                dict(
                    p_season_id=sid,
                    p_trainer_id=p["trainer_id"],
                    p_promotion_id=promo,
                    p_idempotency_key=key or uuid4().hex,
                ),
            )
            .execute()
            .data
        )

    def settle(sid, p):
        return (
            client.rpc(
                "settle_observed_progress_rewards", dict(sid=sid, tid=p["trainer_id"])
            )
            .execute()
            .data
        )

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

    def deaths(sid, p):
        return next(
            r
            for r in client.rpc("initial_assignment_observations", {"sid": sid})
            .execute()
            .data
            if r["id"] == p["id"]
        )["adjusted_deaths"]

    def redeem(sid, p, bought, entity, key=None):
        head = f.rows(
            "pokemon_identity_revisions", season_id=sid, trainer_id=p["trainer_id"]
        )
        head = max(head, key=lambda r: r["revision_number"])
        return (
            client.rpc(
                "api_redeem_purchase",
                dict(
                    p_season_id=sid,
                    p_trainer_id=p["trainer_id"],
                    p_purchase_id=bought,
                    p_pokemon_entity_id=entity,
                    p_idempotency_key=key or uuid4().hex,
                    p_expected_revision_id=head["id"],
                ),
            )
            .execute()
            .data
        )

    def force_rollback(sid, table, operation, action):
        before = snapshot()
        sql(
            args,
            f"""create function public.__phase10_5i_fail() returns trigger language plpgsql as $$
          begin raise exception 'I forced rollback'; end $$;
          create trigger __phase10_5i_fail after {operation} on public.{table}
          for each row when(new.season_id='{sid}'::uuid) execute function public.__phase10_5i_fail();""",
        )
        try:
            rejected(action, "P0001")
            require(snapshot() == before, "Partial economic effects after " + table)
            rollbacks.append(table + ":" + operation)
        finally:
            sql(args, "drop function public.__phase10_5i_fail() cascade;")

    try:
        f.setup()
        sid, day = f.season()
        a, b, c, d = f.players(sid)
        item = f.rows("shop_items", code="blindar_pokemon")[0]
        revive = f.rows("shop_items", code="revivir_pokemon")[0]
        credit(sid, a, 2147483647)
        credit(sid, a, 2147483647)
        require(balance(sid, a) == "4294967294", "Int32 wallet truncation")
        key = uuid4().hex
        first = purchase(sid, a, item["id"], key)
        require(
            first["balance_after"] == 4294967294 - item["base_price"],
            "Purchase lost exact balance",
        )
        require(purchase(sid, a, item["id"], key) == first, "Receipt replay changed")
        rejected(lambda: purchase(sid, a, revive["id"], key), "idempotency_conflict")
        credit(sid, b, -10)
        require(balance(sid, b) == "-10", "Negative wallet clamped")
        rejected(lambda: purchase(sid, b, item["id"]), "insufficient_funds")
        credit(sid, c, item["base_price"])
        outcomes = race(
            lambda: purchase(sid, c, item["id"]), lambda: purchase(sid, c, item["id"])
        )
        require(
            sum(isinstance(r, dict) for r in outcomes) == 1
            and "insufficient_funds" in outcomes
            and balance(sid, c) == "0",
            "Double spend",
        )
        key = uuid4().hex
        outcomes = race(
            lambda: purchase(sid, a, item["id"], key),
            lambda: purchase(sid, a, item["id"], key),
        )
        require(
            outcomes[0] == outcomes[1] and isinstance(outcomes[0], dict),
            "Concurrent replay duplicated",
        )
        passed(
            "exact >int32/negative wallet; same/conflicting key and concurrent double-spend/replay"
        )

        promo = f.insert(
            "shop_promotions",
            dict(
                season_id=sid,
                matchday_id=day,
                shop_item_id=revive["id"],
                promotion_type="normal",
                status="pending",
                base_price=revive["base_price"],
                effective_price=1,
                stock_total=1,
                announced_at="2020-01-01T00:00:00Z",
                activates_at="2099-01-01T00:00:00Z",
            ),
        )
        require(
            f.rows("public_shop_promotions", id=promo["id"])[0]["status"] == "pending",
            "Pending announcement invisible",
        )
        rejected(lambda: promotional(sid, a, promo["id"]), "promotion_pending")
        update("shop_promotions", promo["id"], announced_at=None)
        require(
            not f.rows("public_shop_promotions", id=promo["id"]),
            "Private promotion leaked",
        )
        update("shop_promotions", promo["id"], activates_at="2020-01-01T00:00:00Z")
        require(
            f.rows("public_shop_promotions", id=promo["id"])[0]["status"] == "active",
            "Activated pending offer invisible",
        )
        credit(sid, d, 100)
        outcomes = race(
            lambda: promotional(sid, a, promo["id"]),
            lambda: promotional(sid, d, promo["id"]),
        )
        require(
            sum(isinstance(r, dict) for r in outcomes) == 1, "Promotion stock oversold"
        )
        winner = next(r for r in outcomes if isinstance(r, dict))
        winning_player = a if winner["trainer_id"] == a["trainer_id"] else d
        original_purchase = f.rows("purchases", id=winner["id"])[0]
        winning_key = original_purchase["idempotency_key"]
        require(
            promotional(sid, winning_player, promo["id"], winning_key) == winner,
            "Promotional receipt replay changed",
        )
        rejected(
            lambda: purchase(sid, winning_player, revive["id"], winning_key),
            "idempotency_conflict",
        )
        require(
            f.rows("shop_promotions", id=promo["id"])[0]["stock_used"] == 1,
            "Stock not atomic",
        )
        passed(
            "pending/publication privacy, activation, promotional price and one-stock concurrency"
        )

        # The same applicable Store Ban blocks active purchases but cannot invent a
        # competitive window after finish/archive (including a stale final pointer).
        trial = f.insert(
            "trial_cases",
            dict(
                season_id=sid,
                accused_trainer_id=a["trainer_id"],
                title="Synthetic store ban",
                description="I fixture",
                status="resolved",
            ),
        )
        f.insert(
            "penalties",
            dict(
                season_id=sid,
                trainer_id=a["trainer_id"],
                trial_case_id=trial["id"],
                penalty_type="store_ban",
                amount=0,
                start_matchday_number=1,
                end_matchday_number=2,
            ),
        )
        rejected(lambda: purchase(sid, a, item["id"]), "store_banned")
        for status in ("finished", "archived"):
            update(
                "seasons",
                sid,
                status=status,
                current_matchday_id=None,
                finished_at="2026-10-07T00:00:00Z",
                archived_at="2026-10-07T00:00:00Z" if status == "archived" else None,
            )
            r = purchase(sid, a, item["id"])
            require(
                r["matchday_id"] is None and r["matchday_number"] is None,
                "Fabricated post-League matchday",
            )
        update("seasons", sid, current_matchday_id=day)
        require(
            purchase(sid, a, item["id"])["matchday_id"] is None,
            "Reused frozen day for purchase",
        )
        global_promo = f.insert(
            "shop_promotions",
            dict(
                season_id=sid,
                shop_item_id=revive["id"],
                promotion_type="normal",
                status="active",
                base_price=revive["base_price"],
                effective_price=1,
                stock_total=5,
            ),
        )
        require(
            promotional(sid, a, global_promo["id"])["matchday_id"] is None,
            "Post-League promotion blocked",
        )
        rejected(lambda: promotional(sid, a, promo["id"]), "promotion_not_current")
        passed(
            "finished/archived normal and season-wide promotional spending without fake matchdays"
        )

        # New independent season for observation rewards; only synthetic season status changes.
        sid, day = f.season()
        a, b, c, d = f.players(sid)
        require(settle(sid, a) == 0, "Missing progress paid")
        observe(sid, a, None)
        require(balance(sid, a) == "0", "Unknown progress paid")
        observe(sid, a, 0, False)
        require(balance(sid, a) == "0", "Observed zero paid")
        observe(sid, a, 2, False, before_identity=True)
        require(balance(sid, a) == "8", "Badge defaults or commit hook failed")
        before = snapshot()
        require(
            race(lambda: settle(sid, a), lambda: settle(sid, a)) == [0, 0]
            and snapshot() == before,
            "Repeated proof paid",
        )
        old = sources[a["id"]][0]
        observe(sid, a, 4, False)
        require(balance(sid, a) == "16", "Badge delta not exact")
        observe(sid, a, 1, None)
        require(balance(sid, a) == "16", "Regressed progress compensated")
        update("season_players", a["id"], current_save_file_id=old["id"])
        require(
            settle(sid, a) == 0 and balance(sid, a) == "16", "Stale observation paid"
        )
        observe(sid, a, 8, False)
        require(balance(sid, a) == "32", "Eight badges wrongly imply Champion")
        observe(sid, a, 8, True, parser=2)
        require(balance(sid, a) == "32", "Old parser fabricated completion")
        observe(sid, a, 8, True)
        require(balance(sid, a) == "44", "Champion proof did not pay once")
        observe(sid, a, 8, True)
        require(
            balance(sid, a) == "44"
            and len(
                f.rows(
                    "progress_reward_claims", season_id=sid, trainer_id=a["trainer_id"]
                )
            )
            == 9,
            "Completion replay duplicated",
        )
        passed(
            "unknown/zero, trusted hooks, badge deltas, regression/stale proof, eight badges, reader version and completion once"
        )

        for mutate in (
            lambda p: p["observed_progress"].update(source_hash="0" * 64),
            lambda p: p["observed_progress"].update(game="HGSS"),
            lambda p: p["observed_progress"]["progress"].update(
                champion_defeated="true"
            ),
            lambda p: p["observed_progress"]["progress"]["regions"][0].update(
                badge_flags=[1] * 8
            ),
        ):
            observe(sid, b, 8, True, malformed=mutate)
            require(balance(sid, b) == "0", "Malformed evidence paid")
        rejected(
            lambda: update(
                "season_players",
                b["id"],
                current_save_file_id=sources[a["id"]][0]["id"],
            ),
            "23503",
        )
        require(settle(sid, b) == 0, "Another trainer's progress paid")
        passed("malformed/hash/game/bool and cross-trainer progress cannot mint coins")

        # New config persists via the production admin boundary, takes effect only
        # at its real window, and never reprices old claims.
        cfg = f.config(sid)
        cfg.update(
            name="New reward amounts",
            effective_from_matchday=2,
            rules={
                "team_lock_required": True,
                "last_b_gets_steal": False,
                "badge_reward_coins": 7,
                "game_completion_reward_coins": 20,
            },
        )
        version = f.call("create_config", sid, cfg)["resource_id"]
        observe(sid, c, 1, False)
        require(balance(sid, c) == "4", "Future config used early")
        next_day = f.insert(
            "matchdays", dict(season_id=sid, number=2, season_config_version_id=version)
        )
        update("seasons", sid, current_matchday_id=next_day["id"])
        observe(sid, c, 2, True)
        require(balance(sid, c) == "31", "Config delta or completion amount ignored")
        require(
            settle(sid, a) == 0 and balance(sid, a) == "44",
            "Config repriced paid history",
        )
        passed(
            "persistent configured 4/12 defaults and 7/20 amounts with actual-window selection"
        )

        # Pending physical revive is still the same death. Observing it alive and
        # later dead proves a distinct death; wipe revival retains its own factor 2.
        observe(sid, d, 0, False)
        entity = f.rows("pokemon_observations", save_file_id=sources[d["id"]][0]["id"])[
            0
        ]["pokemon_entity_id"]
        bought = f.entitlement(sid, d, "revivir_pokemon")
        require(deaths(sid, d) == 1, "Visible death missing")
        receipt = redeem(sid, d, bought["id"], entity, "revive")
        require(
            receipt["physical_effect_status"] == "pending" and deaths(sid, d) == 1,
            "Revive double counted pending visible death",
        )
        require(
            redeem(sid, d, bought["id"], entity, "revive") == receipt,
            "Revive replay changed",
        )
        second = f.entitlement(sid, d, "revivir_pokemon")
        rejected(lambda: redeem(sid, d, second["id"], entity), "pokemon_revive_pending")
        observe(sid, d, 0, False, location=0)
        require(deaths(sid, d) == 1, "Leaving dead box erased historical death")
        observe(sid, d, 0, False, location=8)
        require(deaths(sid, d) == 2, "A distinct later death was erased")
        redeem(sid, d, second["id"], entity)
        require(deaths(sid, d) == 2, "A second legitimate revive stacked on its visible death")
        observe(sid, d, 0, False, location=9)
        require(deaths(sid, d) == 2, "Non-dead PC box erased historical revives")
        observe(sid, d, 0, False, location=8)
        require(deaths(sid, d) == 3, "Return from Box 9 erased a distinct later death")
        client.table("season_player_stats").update({"revived_after_wipe": 1}).eq(
            "season_player_id", d["id"]
        ).execute()
        require(deaths(sid, d) == 5, "Wipe revival lost separate -0.4 rule")
        live = (
            client.rpc(
                "matchday_context_v034",
                {"op": "close", "r": {"season_id": sid, "resource_id": day}},
            )
            .execute()
            .data
        )
        require(
            next(p for p in live["inputs"]["players"] if p["id"] == d["id"])[
                "dead_count"
            ]
            == 5,
            "Daily/initial death consumers differ",
        )
        passed(
            "revive before/while pending/after save movement/re-death, duplicate denial, wipe and live daily parity"
        )
        legacy = f.entitlement(sid, d, "revivir_pokemon")
        update("purchases", legacy["id"], status="used")
        require(deaths(sid, d) is None, "Unlinked legacy revive fabricated an extra visible death")
        client.table("purchases").delete().eq("id", legacy["id"]).execute()

        # Real robbery creates the voucher. It is never sold or fabricated.
        steal = f.entitlement(sid, a, "robar_pokemon")
        observe(sid, b, 0, False, location=0)
        target = f.rows("pokemon_observations", save_file_id=sources[b["id"]][0]["id"])[
            0
        ]["pokemon_entity_id"]
        # Redemption target's revision belongs to its current owner, not the thief.
        head = max(
            f.rows(
                "pokemon_identity_revisions", season_id=sid, trainer_id=b["trainer_id"]
            ),
            key=lambda r: r["revision_number"],
        )
        theft = (
            client.rpc(
                "api_redeem_purchase",
                dict(
                    p_season_id=sid,
                    p_trainer_id=a["trainer_id"],
                    p_purchase_id=steal["id"],
                    p_pokemon_entity_id=target,
                    p_idempotency_key="steal",
                    p_expected_revision_id=head["id"],
                ),
            )
            .execute()
            .data
        )
        gift = f.rows("purchases", id=theft["gift_purchase_id"])[0]
        require(
            gift["acquisition_type"] == "reward"
            and gift["origin_redemption_id"] == theft["redemption_id"],
            "Voucher origin lost",
        )
        voucher = f.rows("shop_items", code="robbery_shield_voucher")[0]
        require(
            not f.rows("public_shop_items", id=voucher["id"]), "Voucher purchasable"
        )
        rejected(lambda: purchase(sid, a, voucher["id"]), "item_unavailable")
        own = f.rows("pokemon_observations", save_file_id=sources[a["id"]][0]["id"])[0][
            "pokemon_entity_id"
        ]
        require(
            own
            in client.rpc(
                "inventory_shield_targets", {"sid": sid, "tid": a["trainer_id"]}
            )
            .execute()
            .data,
            "Eligible own voucher target hidden",
        )
        outcomes = race(
            lambda: redeem(sid, a, gift["id"], own, "gift"),
            lambda: redeem(sid, a, gift["id"], own, "gift"),
        )
        require(
            isinstance(outcomes[0], dict)
            and outcomes[0] == outcomes[1]
            and outcomes[0]["physical_effect_status"] == "not_required",
            "Voucher duplicate/physical write",
        )
        rejected(
            lambda: redeem(sid, a, gift["id"], own, "other"),
            "purchase_already_redeemed",
        )
        require(
            own
            not in client.rpc(
                "inventory_shield_targets", {"sid": sid, "tid": a["trainer_id"]}
            )
            .execute()
            .data,
            "Shielded target remains eligible",
        )
        passed(
            "legitimate robbery voucher origin, hidden catalog, eligible owner targets and one-time concurrent redemption"
        )

        # Failure after each economic boundary must roll back all rows exactly.
        credit(sid, a, 1000)
        for table in ("purchases", "coin_transactions", "activity_events"):
            force_rollback(sid, table, "insert", lambda: purchase(sid, a, item["id"]))
        observe(sid, b, 2, True, promote=False)
        saved = sources[b["id"]][0]
        for table in ("coin_transactions", "progress_reward_claims"):
            force_rollback(
                sid,
                table,
                "insert",
                lambda: update(
                    "season_players", b["id"], current_save_file_id=saved["id"]
                ),
            )
        update("season_players", b["id"], current_save_file_id=saved["id"])
        # A new proof can arrive concurrently at both acceptance hooks. Only one
        # ledger delta is allowed; repeated pointer updates have no extra effect.
        observe(sid, b, 3, True, promote=False)
        saved = sources[b["id"]][0]
        before_balance = int(balance(sid, b))
        outcomes = race(
            lambda: update("season_players", b["id"], current_save_file_id=saved["id"]),
            lambda: update("season_players", b["id"], current_save_file_id=saved["id"]),
        )
        require(
            all(isinstance(r, list) for r in outcomes)
            and int(balance(sid, b)) == before_balance + 7,
            "Concurrent new proof duplicated the badge delta",
        )
        passed(
            "wallet/purchase/activity and pointer/reward-ledger/claim transactional rollback"
        )

        for role, reader in readers.items():
            for rpc, params in (
                (
                    "settle_observed_progress_rewards",
                    {"sid": sid, "tid": a["trainer_id"]},
                ),
                ("inventory_shield_targets", {"sid": sid, "tid": a["trainer_id"]}),
                ("commit_pokemon_identity", {"p_request": {}}),
                (
                    "api_create_normal_purchase",
                    dict(
                        p_season_id=sid,
                        p_trainer_id=a["trainer_id"],
                        p_item_id=item["id"],
                        p_idempotency_key="browser",
                    ),
                ),
            ):
                rejected(lambda: reader.rpc(rpc, params).execute(), "42501")
            rejected(
                lambda: reader.table("progress_reward_claims").select("*").execute(),
                "42501",
            )
            rejected(
                lambda: (
                    reader.table("progress_reward_claims")
                    .insert({"season_id": sid})
                    .execute()
                ),
                "42501",
            )
        rejected(
            lambda: update(
                "progress_reward_claims",
                f.rows("progress_reward_claims", season_id=sid)[0]["id"],
                amount=999,
            ),
            "42501",
        )
        passed(
            "anon/participant/browser-admin service RPC and private proof access denied; immutable claims"
        )
    finally:
        for sid in f.seasons:
            client.table("progress_reward_claims").delete().eq(
                "season_id", sid
            ).execute()
        f.cleanup()
        require(
            snapshot() == baseline, "I fixture cleanup changed original public rows"
        )
        print(f"PASS I exact {len(tables)}-table restoration", flush=True)
    result = dict(
        groups=len(checks),
        checks=checks,
        rollback_boundaries=rollbacks,
        restored_tables=len(tables),
    )
    print("I PostgreSQL RESULT", result, flush=True)
    return result


if __name__ == "__main__":
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--psql", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="55439")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="")
    validate(p.parse_args(), _psql_text)
