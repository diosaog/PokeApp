"""Actual concurrent-session 074 guards on a disposable loopback database.

Starts its own cluster, loads the versioned migrations and creates synthetic
rows only. A reservation stays uncommitted while each competing command blocks;
after its commit, the competitor must recheck the reservation and refuse.
No remote configuration, accounts, balances or real save files are accessed.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import time
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from tools.phase30_release_audit import SupabaseLikePG
from tools.validate_phase074_training import validate as training_fixture

ROOT = Path(__file__).resolve().parents[1]


def connection(pg, *, label="074-concurrency", autocommit=True):
    return psycopg.connect(host="127.0.0.1", port=pg.port, dbname=pg.database,
                           user="supabase_admin", password="", sslmode="disable",
                           application_name=label, autocommit=autocommit)


def rpc(conn, name, request):
    return conn.execute(sql.SQL("select public.{}(%s::jsonb)").format(sql.Identifier(name)),
                        (Jsonb(request),)).fetchone()[0]


def validate(pg):
    fixture = training_fixture(None, capture_only=True)
    sid, tid, oldsid = fixture["season_id"], fixture["trainer_id"], fixture["purchase_season_id"]
    owner_purchase = fixture["purchase_id"]
    other = str(uuid4())
    other_player, other_old_player, other_purchase, bag_purchase = (str(uuid4()) for _ in range(4))
    evidence = []
    with connection(pg) as admin:
        admin.execute(fixture["seed_sql"])
        admin.execute("insert into public.trainers(id,display_name,slug) values(%s,'074 Other',%s)",
                      (other, "074-other-" + other))
        admin.execute("insert into public.season_players(id,season_id,trainer_id,status) values"
                      "(%s,%s,%s,'active'),(%s,%s,%s,'active')",
                      (other_player, sid, other, other_old_player, oldsid, other))
        admin.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)"
                      " select %s,%s,%s,%s,id,1,6,'paid','pending' from public.shop_items where code='chapa_plateada'",
                      (other_purchase, oldsid, other, other_old_player))
        admin.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)"
                      " select %s,%s,%s,%s,id,1,6,'paid','pending' from public.shop_items where code='objeto_evolutivo'",
                      (bag_purchase, sid, tid, fixture["season_player_id"]))
        # Existing catalog revisions may use the concrete stone instead of the
        # family code. Keep the test on a normal compatible physical purchase.
        if not admin.execute("select 1 from public.purchases where id=%s", (bag_purchase,)).fetchone():
            admin.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)"
                          " select %s,%s,%s,%s,id,1,6,'paid','pending' from public.shop_items where code='piedra_evolutiva'",
                          (bag_purchase, sid, tid, fixture["season_player_id"]))
        assert admin.execute("select 1 from public.purchases where id=%s", (bag_purchase,)).fetchone(), "normal bag fixture item missing"
        context = rpc(admin, "api_training_operation", dict(operation="context", season_id=sid, trainer_id=tid))
        head = context["revision"]["id"]

        def reserve_request():
            request = deepcopy(fixture["reserve"])
            request["operation_id"] = str(uuid4())
            request["identity_revision_id"] = head
            request["intent"]["mutation"]["attempt"] = request["operation_id"]
            return request

        def release(request):
            return rpc(admin, "api_training_operation", dict(operation="release", season_id=sid,
                       trainer_id=tid, operation_id=request["operation_id"]))

        def race(label, competing, expected):
            request = reserve_request()
            with connection(pg, label="074-reserver", autocommit=False) as reserver:
                assert rpc(reserver, "api_training_operation", request)["status"] == "RESERVED"

                def run_competitor():
                    with connection(pg, label=label, autocommit=False) as competitor:
                        competitor.execute("set local lock_timeout='10s';set local statement_timeout='12s'")
                        try:
                            result = competing(competitor, request)
                            competitor.commit()
                            return {"succeeded": True, "result": result}
                        except psycopg.Error as error:
                            competitor.rollback()
                            return {"succeeded": False, "state": error.sqlstate,
                                    "reason": error.diag.message_primary}

                with ThreadPoolExecutor(1) as pool:
                    future = pool.submit(run_competitor)
                    waiting = False
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline and not future.done():
                        waiting = bool(admin.execute("select 1 from pg_stat_activity where application_name=%s"
                                                     " and wait_event_type='Lock'", (label,)).fetchone())
                        if waiting:
                            break
                        time.sleep(0.02)
                    assert waiting, (label, "competitor did not wait behind uncommitted reservation")
                    reserver.commit()
                    outcome = future.result(timeout=14)
                assert not outcome["succeeded"] and outcome["reason"] == expected, (label, outcome)
                assert admin.execute("select status from public.purchases where id=%s", (owner_purchase,)).fetchone()[0] == "pending"
                assert admin.execute("select current_save_file_id::text from public.season_players where id=%s",
                                     (fixture["season_player_id"],)).fetchone()[0] == fixture["initial_register"]["save_id"]
                assert admin.execute("select count(*) from public.training_operations where season_id=%s and trainer_id=%s and status='RESERVED'",
                                     (sid, tid)).fetchone()[0] == 1
                assert release(request)["status"] == "RELEASED"
                evidence.append({"check": label, "waited_for_reservation": True, "pass": True,
                                 "refusal": expected, "purchase_pending": True, "current_save_preserved": True})

        future_register = deepcopy(fixture["future_register"])
        future_register["operation"] = "register"
        future_register["identity_plan"]["expected_predecessor_id"] = head
        race("074-ingestion", lambda conn, _: rpc(conn, "api_register_save", future_register),
             "training_reconciliation_required")
        race("074-bag-reservation", lambda conn, _: conn.execute(
            "select public.api_reserve_item_delivery(%s,%s,%s,%s,'leaf_stone',85,'Y')",
            (sid, tid, bag_purchase, str(uuid4()))).fetchone()[0], "delivery_in_progress")
        race("074-admin-refund", lambda conn, _: conn.execute(
            "select public.admin_purchase_resolve(%s,%s,%s,'purchase_cancel',%s,%s,'Synthetic concurrent cancellation')",
            (tid, oldsid, owner_purchase, str(uuid4()), "f" * 64)).fetchone()[0], "purchase_linked_to_save_operation")

        def competing_training(conn, _):
            return rpc(conn, "api_training_operation", reserve_request())

        race("074-second-training", competing_training, "training_save_busy")

        request = reserve_request()
        rpc(admin, "api_training_operation", request)
        for wrong_sid, wrong_tid, label in ((sid, other, "other-account"), (oldsid, tid, "other-season")):
            assert rpc(admin, "api_training_operation", dict(operation="load", season_id=wrong_sid,
                       trainer_id=wrong_tid, operation_id=request["operation_id"])) is None
            for action in ("reserve", "complete", "release"):
                denied = dict(request, operation=action, season_id=wrong_sid, trainer_id=wrong_tid)
                try:
                    rpc(admin, "api_training_operation", denied)
                except psycopg.Error as error:
                    assert error.sqlstate == "PT404" and error.diag.message_primary == "training_not_found", (action, error)
                else:
                    raise AssertionError((label, action, "foreign operation accepted"))
            evidence.append({"check": label, "pass": True, "scoped_load_empty": True,
                             "reserve_complete_release": "404 training_not_found"})
        release(request)
        foreign_purchase = reserve_request()
        foreign_purchase["purchase_id"] = other_purchase
        try:
            rpc(admin, "api_training_operation", foreign_purchase)
        except psycopg.Error as error:
            assert error.sqlstate == "PT409" and error.diag.message_primary == "training_purchase_unavailable", error
        else:
            raise AssertionError("another trainer's legacy purchase accepted")
        evidence.append({"check": "other-account-legacy-purchase", "pass": True,
                         "refusal": "training_purchase_unavailable"})
        for role in ("anon", "authenticated"):
            with connection(pg, autocommit=False) as browser:
                browser.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
                try:
                    rpc(browser, "api_training_operation", dict(operation="complete", season_id=sid,
                        trainer_id=tid, operation_id=request["operation_id"], output_sha256="b" * 64,
                        result={"native_verified": True}))
                except psycopg.Error as error:
                    assert error.sqlstate == "42501", error
                else:
                    raise AssertionError("browser forged native proof accepted")
                browser.rollback()
            evidence.append({"check": role + "-forged-proof", "pass": True, "refusal": "42501"})
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55675)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in sorted((ROOT / "supabase/v2/migrations").glob("*.sql")):
            pg.sql(migration.read_text(encoding="utf-8"))
        checks = validate(pg)
    finally:
        pg.stop()
    args.evidence.write_text(json.dumps({"checks": checks, "pass": all(c["pass"] for c in checks),
        "boundary": "Separate disposable loopback PostgreSQL; concurrent sessions, synthetic fixtures; no production access."}, indent=2) + "\n", encoding="utf-8")
    print(f"PASS {len(checks)} concurrent/scoping/forged-proof gates; isolated PostgreSQL stopped")


if __name__ == "__main__":
    main()
