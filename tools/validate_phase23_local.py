"""Isolated loopback PostgreSQL gate. No live credentials or remote clients."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.domain.item_use import ItemUsePrepareRequest
from app.repositories.errors import ItemUseRejectedError, PersistenceError
from app.repositories.supabase.item_use import SupabaseItemUseRepository
from tools.validate_accounts_local import ROOT, LocalPG
from tools.validate_redemption_fixtures import RedemptionFixtures
from tools.validate_supabase_v2_identity_sql import LocalClient, SqlError


def parity(pg):
    chain = "pokeapp_v2_validation_phase23_chain"
    pg.sql(f"create database {chain};", "postgres")
    try:
        pg.storage(chain)
        paths = sorted((ROOT / "supabase/v2/migrations").glob("*.sql"))
        for path in paths[:-1]:
            pg.sql(path.read_text(encoding="utf-8"), chain)
        tables = pg.sql(
            "select tablename from pg_tables where schemaname='public' order by tablename;",
            chain,
        ).stdout.splitlines()
        hashes = (
            "select jsonb_object_agg(name,value) from ("
            + " union all ".join(
                f"select '{t}' name,md5(coalesce(string_agg(to_jsonb(r)::text,'' order by to_jsonb(r)::text),'')) value from public.{t} r"
                for t in tables
            )
            + ") q;"
        )
        before = pg.sql(hashes, chain).stdout
        pg.sql(paths[-1].read_text(encoding="utf-8"), chain)
        assert pg.sql(hashes, chain).stdout == before

        def dump(db):
            raw = pg.command(
                "pg_dump",
                [
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(pg.port),
                    "-U",
                    "postgres",
                    "-d",
                    db,
                    "--schema-only",
                ],
            ).stdout
            return "\n".join(
                x
                for x in raw.splitlines()
                if not x.startswith(("\\restrict", "\\unrestrict"))
            )

        a, b = dump(chain), dump("pokeapp_v2_validation_accounts")
        assert a == b, "bootstrap/catalog mismatch"
        return {"schema_lines": len(a.splitlines()), "preserved_tables": len(tables)}
    finally:
        pg.sql(f"drop database {chain};", "postgres")


def bridge_gate(pg, args, repo, setup, request, proof, pending):
    import sys
    from hashlib import sha256

    sys.path.insert(0, str(ROOT / "tests"))
    from test_phase22_write_engine import SOURCE, engine_at, intent

    from app.launcher.item_use import EngineeringItemUse
    from app.launcher.save_activity import SaveActivityGate, SaveBusy
    from app.launcher.write_control import LocalWriteController

    f, saved = setup()
    root = pg.root / "disposable-bridge"
    root.mkdir()
    target = root / "main"
    target.write_bytes(SOURCE)
    saved["sha256"] = sha256(SOURCE).hexdigest()
    LocalClient(args).table("save_files").update({"sha256": saved["sha256"]}).eq(
        "id", saved["id"]
    ).execute()
    a = repo.prepare(request(f, saved))

    def bridge(repository):
        controller = LocalWriteController(
            SaveActivityGate(), lambda: str(target), engine_at(root)
        )
        return EngineeringItemUse(
            controller, repository, season_id=a["season_id"], trainer_id=a["trainer_id"]
        )

    first = bridge(repo)
    first.bind_fixture(a, intent(), pokemon_entity_id=a["target_pokemon_entity_id"])
    assert (
        first.apply(a["id"], closed_emulator_confirmed=True)
        == "LOCAL_VERIFIED_AWAITING_CONFIRMATION"
    )
    pending(a)
    try:
        with first.controller.gate.reading():
            pass
    except SaveBusy:
        pass
    else:
        raise AssertionError("sync resumed before reconciliation")
    # A client statement alone, even from a correct local engine, is not sufficient.
    assert first.complete(a["id"]) == "BLOCKED_UNCERTAIN"
    pending(a)
    native_id, record = first._load(a["id"])
    engine = first.engine
    native_intent, original, prepared = engine._materials(engine._load(native_id))
    persisted = engine.files.read_path(target)
    engine.native.verify(original, persisted, native_intent, prepared)
    assert original == SOURCE and persisted != original
    result_hash = sha256(persisted).hexdigest()
    proof(
        a,
        record["claim_id"],
        result_sha256=result_hash,
        native_operation_id=native_id,
        plan_sha256=sha256(
            json.dumps(native_intent.to_payload(), sort_keys=True).encode()
        ).hexdigest(),
    )

    class LostAck:
        def complete(self, *parts):
            repo.complete(*parts)
            raise OSError("synthetic lost confirmation response")

    restarted = bridge(LostAck())
    try:
        restarted.complete(a["id"])
    except OSError:
        pass
    else:
        raise AssertionError("missing lost response")
    assert restarted.controller.gate.recovery_required
    final = bridge(repo)
    assert final.complete(a["id"]) == "APPLIED_VERIFIED"
    assert final.complete(a["id"]) == "APPLIED_VERIFIED"
    assert sha256(target.read_bytes()).hexdigest() == result_hash
    assert len(f.select("redemptions", purchase_id=a["purchase_id"])) == 1
    assert not f.select("coin_transactions", season_id=a["season_id"])
    assert not final.controller.gate.recovery_required
    return {
        "status": "PASS",
        "semantics": "synthetic test_marking only; NOT physical revive certification",
        "original_backup_preserved": True,
        "independent_local_native_readback": True,
        "client_claim_denied": True,
        "restart_lost_ack_single_consume": True,
    }


def run(binary, output):
    pg = LocalPG(binary, 55473)
    result = {"status": "RUNNING", "cluster": str(pg.root), "checks": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        pg.start()
        result["version"] = pg.sql("select version();").stdout.strip()
        args = SimpleNamespace(
            psql=str(binary / "psql.exe"),
            host="127.0.0.1",
            port=pg.port,
            user="postgres",
            password="",
            database="pokeapp_v2_validation_accounts",
        )
        client = LocalClient(args)
        repo = SupabaseItemUseRepository(client)

        def passed(name):
            result["checks"].append(name)
            print("PASS " + name, flush=True)

        def reject(action, code):
            try:
                action()
            except ItemUseRejectedError as exc:
                assert exc.code == code, (exc.code, code)
            else:
                raise AssertionError("expected " + code)

        def setup():
            f = RedemptionFixtures(
                client, {}, {x: str(uuid4()) for x in ("owner", "other", "admin")}
            )
            f.setup()
            sid = f.select("pokemon_identity_revisions", id=f.head)[0]["save_file_id"]
            saved = f.select("save_files", id=sid)[0]
            client.table("season_players").update({"current_save_file_id": sid}).eq(
                "id", f.player["id"]
            ).execute()
            return f, saved

        def request(f, saved, target=0):
            p = f.purchase("revivir_pokemon")
            return ItemUsePrepareRequest(
                f.season["id"],
                f.owner["id"],
                p["id"],
                f.dead[target],
                saved["id"],
                saved["sha256"],
                str(uuid4()),
                str(uuid4()),
            )

        def claim(a, key):
            return repo.claim(
                a["id"],
                a["season_id"],
                a["trainer_id"],
                {"operation_id": a["operation_id"], "claim_id": key},
            )

        def finish(a, key, **kw):
            return repo.complete(
                a["id"],
                a["season_id"],
                a["trainer_id"],
                dict(
                    operation_id=a["operation_id"],
                    claim_id=key,
                    status="APPLIED_VERIFIED",
                    observed_sha256="b" * 64,
                    **kw,
                ),
            )

        def pending(a):
            assert (
                client.table("purchases")
                .select("*")
                .eq("id", a["purchase_id"])
                .execute()
                .data[0]["status"]
                == "pending"
            )

        def proof(a, key, **kw):
            # SQL trust-boundary tests use synthetic attestations. ONLY the later
            # bridge test independently reads the engine result before this insert.
            values = {
                "authorization_id": a["id"],
                "claim_id": key,
                "operation_id": a["operation_id"],
                "source_sha256": a["save_sha256"],
                "result_sha256": "b" * 64,
                "target_pokemon_entity_id": a["target_pokemon_entity_id"],
                "identity_revision_id": a["identity_revision_id"],
                "native_operation_id": str(uuid4()),
                "plan_sha256": "c" * 64,
            }
            values.update(kw)
            LocalClient(args, "postgres").table("item_use_verifications").insert(
                values
            ).execute()

        f, saved = setup()
        req = request(f, saved)
        with ThreadPoolExecutor(4) as pool:
            authorizations = list(pool.map(lambda _: repo.prepare(req), range(4)))
        a = authorizations[0]
        assert all(x == a for x in authorizations)
        pending(a)
        reject(
            lambda: repo.prepare(replace(req, operation_id=str(uuid4()))),
            "ITEM_USE_CONFLICT",
        )
        reject(lambda: repo.prepare(request(f, saved)), "ITEM_USE_CONFLICT")
        reject(
            lambda: repo.prepare(
                replace(request(f, saved, 1), pokemon_entity_id=f.party[0])
            ),
            "POKEMON_NOT_REVIVABLE",
        )
        reject(
            lambda: repo.prepare(replace(request(f, saved, 1), save_sha256="e" * 64)),
            "SAVE_CONTEXT_CHANGED",
        )
        passed(
            "concurrent_prepare_exact_replay_target_reservation_wrong_pokemon_stale_hash"
        )
        keys = [str(uuid4()), str(uuid4())]

        def try_claim(key):
            try:
                return claim(a, key)
            except ItemUseRejectedError as e:
                return e.code

        with ThreadPoolExecutor(2) as pool:
            winners = list(pool.map(try_claim, keys))
        assert (
            sum(isinstance(x, dict) for x in winners) == 1
            and "ITEM_USE_CONFLICT" in winners
        )
        key = keys[next(i for i, x in enumerate(winners) if isinstance(x, dict))]
        assert claim(a, key)["status"] == "PENDING_APPLICATION"
        assert "claim_id" not in repo.list(a["season_id"], a["trainer_id"])[0]
        assert repo.list(a["season_id"], f.actors["other"]["id"]) == []
        passed("two_launchers_single_claim_lost_claim_response_replay_private_list")
        assert finish(a, key)["status"] == "BLOCKED_UNCERTAIN"
        pending(a)
        f.reject(
            lambda: f.redeem({"id": a["purchase_id"]}, f.dead[0], req.idempotency_key),
            "PHYSICAL_VERIFICATION_REQUIRED",
        )
        assert not f.select("redemptions", purchase_id=a["purchase_id"])
        assert not f.select("pokemon_entity_flags", pokemon_entity_id=f.dead[0])
        passed("forged_client_claim_and_legacy_redemption_no_consumption_or_flags")
        proof(a, key)
        f.reject(
            lambda: f.redeem({"id": a["purchase_id"]}, f.dead[0], req.idempotency_key),
            "PHYSICAL_VERIFICATION_REQUIRED",
        )
        # An unexpected failure AFTER the business transaction must roll everything back.
        pg.sql("""create function public.phase23_fault() returns trigger language plpgsql as $$
        begin if new.status='APPLIED_VERIFIED' and new.receipt is not null then raise exception 'injected_after_redemption'; end if; return new; end $$;
        create trigger phase23_fault before update on item_use_authorizations for each row execute function phase23_fault();""")
        try:
            finish(a, key)
            raise AssertionError("fault not triggered")
        except PersistenceError as e:
            assert str(e) == "Item-use backend unavailable.", str(e)
        pending(a)
        assert not f.select("redemptions", purchase_id=a["purchase_id"])
        assert not f.select("pokemon_entity_flags", pokemon_entity_id=f.dead[0])
        pg.sql(
            "drop trigger phase23_fault on item_use_authorizations; drop function phase23_fault();"
        )
        passed("rollback_after_redemption_preserves_purchase_flags_and_journal")
        with ThreadPoolExecutor(4) as pool:
            receipts = list(pool.map(lambda _: finish(a, key), range(4)))
        assert (
            all(x == receipts[0] for x in receipts)
            and receipts[0]["status"] == "APPLIED_VERIFIED"
        ), receipts
        assert len(f.select("redemptions", purchase_id=a["purchase_id"])) == 1
        assert not f.select("coin_transactions", season_id=f.season["id"])
        assert (
            finish(a, key) == receipts[0]
        )  # lost response: original operation, no reapply
        passed(
            "concurrent_verified_completion_once_distinct_hashes_lost_response_no_economic_effect"
        )
        for index, change in enumerate(
            ("expired", "wrong_target", "stale_pointer", "wrong_claim"), start=1
        ):
            a2 = repo.prepare(request(f, saved, index))
            k2 = str(uuid4())
            claim(a2, k2)
            if change == "expired":
                pg.sql(
                    f"update item_use_authorizations set expires_at=clock_timestamp()-interval '1 second' where id='{a2['id']}';"
                )
                reject(lambda a2=a2, k2=k2: claim(a2, k2), "ITEM_USE_EXPIRED")
            elif change == "wrong_target":
                proof(a2, k2, target_pokemon_entity_id=f.party[0])
            elif change == "stale_pointer":
                proof(a2, k2)
                client.table("season_players").update(
                    {"current_save_file_id": None}
                ).eq("id", f.player["id"]).execute()
            else:
                proof(a2, k2, claim_id=str(uuid4()))
            assert finish(a2, k2)["status"] == "BLOCKED_UNCERTAIN"
            pending(a2)
            client.table("season_players").update(
                {"current_save_file_id": saved["id"]}
            ).eq("id", f.player["id"]).execute()
        passed(
            "expired_cross_target_cross_claim_and_changed_current_pointer_preserve_entitlements"
        )
        for role in ("anon", "authenticated", "service_role"):
            for privilege in ("insert", "update", "delete"):
                assert (
                    pg.sql(
                        f"select has_table_privilege('{role}','item_use_verifications','{privilege}');"
                    ).stdout.strip()
                    == "f"
                )
            if role != "service_role":
                for table in ("item_use_authorizations", "item_use_verifications"):
                    assert (
                        pg.sql(
                            f"select has_table_privilege('{role}','{table}','select');"
                        ).stdout.strip()
                        == "f"
                    )
                assert (
                    pg.sql(
                        f"select bool_and(not has_function_privilege('{role}',oid,'execute')) from pg_proc where proname like 'api_%item_use%';"
                    ).stdout.strip()
                    == "t"
                )
        assert (
            pg.sql(
                "select bool_and(relrowsecurity and relforcerowsecurity) from pg_class where relname in ('item_use_authorizations','item_use_verifications');"
            ).stdout.strip()
            == "t"
        )
        try:
            client.table("item_use_verifications").insert(
                {"authorization_id": str(uuid4())}
            ).execute()
        except SqlError as e:
            assert e.code == "42501"
        else:
            raise AssertionError("API can forge proof")
        passed("real_RLS_RPC_grants_and_API_cannot_issue_verification")

        # Existing purchase authority; debit at purchase only, not at application.
        pg.sql(
            f"update seasons set status='finished',finished_at=now() where id='{f.season['id']}';"
        )
        item = f.select("shop_items", code="revivir_pokemon")[0]
        buy = {
            "p_season_id": f.season["id"],
            "p_trainer_id": f.owner["id"],
            "p_item_id": item["id"],
            "p_idempotency_key": str(uuid4()),
        }
        try:
            client.rpc("api_create_normal_purchase_8d", buy).execute()
        except SqlError as e:
            assert e.message == "insufficient_funds", e.message
        else:
            raise AssertionError("unfunded purchase")
        pg.sql(
            f"insert into coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type) values('{f.season['id']}','{f.owner['id']}','{f.player['id']}',1000,'admin_adjustment');"
        )
        with ThreadPoolExecutor(3) as pool:
            bought = list(
                pool.map(
                    lambda _: (
                        client.rpc("api_create_normal_purchase_8d", buy).execute().data
                    ),
                    range(3),
                )
            )
        assert all(x == bought[0] for x in bought)
        assert pg.sql(
            f"select sum(amount) from coin_transactions where season_id='{f.season['id']}';"
        ).stdout.strip() == str(1000 - item["base_price"])
        passed("real_purchase_funded_unfunded_concurrent_retry_single_debit")
        result["parity"] = parity(pg)
        passed("upgrade_001_054_equals_bootstrap_and_053_rows_preserved")
        result["bridge"] = bridge_gate(pg, args, repo, setup, request, proof, pending)
        passed(
            "existing_launcher_journal_apply_independent_local_verify_restart_and_lost_ack"
        )
        result["status"] = "PASS"
    except Exception:
        result["status"] = "FAIL"
        raise
    finally:
        try:
            pg.stop()
            result["cleanup"] = "owned_database_dropped_cluster_stopped"
        finally:
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.pg_bin, args.output)
