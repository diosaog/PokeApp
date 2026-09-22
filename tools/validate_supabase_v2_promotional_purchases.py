"""Opt-in Phase 8E checks against approved V2 staging, with isolated fixture cleanup."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from threading import Barrier
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_supabase_v2_purchases import PurchaseValidation
from tools.validate_supabase_v2_rls import ValidationError
from tools.validate_supabase_v2_team_lock import direct_write_denied, require, staging_config


class PromotionalPurchaseValidation(PurchaseValidation):
    def balance(self, actor):
        return sum(row["amount"] for row in self.read(
            "coin_transactions", season_id=self.season_id, trainer_id=actor["trainer"]["id"]))

    def fund_to(self, actor, amount):
        adjustment = amount - self.balance(actor)
        if adjustment:
            self.insert("coin_transactions", {
                "season_id": self.season_id, "trainer_id": actor["trainer"]["id"],
                "season_player_id": actor["player"]["id"], "amount": adjustment,
                "transaction_type": "admin_adjustment",
            })

    def promotion(self, *, kind="normal", stock=2, price=8, category="bayas", **changes):
        item = self.insert("shop_items", {"code": self.config.run_id + "_" + uuid4().hex,
            "name": "Validation promotion", "category": category, "base_price": 10})
        now = datetime.now(timezone.utc)
        return self.insert("shop_promotions", {
            "season_id": self.season_id, "matchday_id": self.days[2]["id"],
            "shop_item_id": item["id"], "promotion_type": kind, "status": "active",
            "base_price": 10, "effective_price": price, "stock_total": stock,
            "announced_at": (now - timedelta(hours=48)).isoformat(),
            "activates_at": (now - timedelta(hours=24)).isoformat(), **changes,
        })

    def state(self):
        return {table: sorted(self.read(table, season_id=self.season_id), key=lambda row: row["id"])
                for table in ("purchases", "coin_transactions", "activity_events", "shop_promotions")}

    def validate_promotions(self):
        from fastapi.testclient import TestClient
        from app.api.config import APIConfig
        from app.api.main import create_app

        owner, other, admin = (self.actors[role] for role in ("owner", "other", "admin"))
        self.set_day(2)
        for actor in self.actors.values():
            self.fund_to(actor, 1000)
        config = APIConfig(supabase_url=self.config.url, supabase_anon_key=self.config.anon_key,
                           supabase_service_role_key=self.config.service_role_key)
        base = f"/v1/seasons/{self.season_id}/shop"

        def request(client, promo, actor=owner, key=None, *, normal=False):
            path = base + ("/purchases" if normal else f"/promotions/{promo['id']}/purchases")
            return client.post(path, headers={"Authorization": "Bearer " + actor["token"],
                "Idempotency-Key": key or uuid4().hex},
                json={"item_id": promo["shop_item_id"]} if normal else {})

        with TestClient(create_app(config=config)) as client:
            def accepted(promo, **kwargs):
                result = request(client, promo, **kwargs)
                require(result.status_code == 200, f"Expected claim success; HTTP {result.status_code}")
                return result.json()

            def rejected(promo, code, status=409, **kwargs):
                before = self.state()
                result = request(client, promo, **kwargs)
                require(result.status_code == status and result.json().get("detail", {}).get("code") == code,
                        f"Expected {status} {code}; HTTP {result.status_code}")
                require(self.state() == before, "Rejected claim changed stock or economic rows")

            normal = self.promotion()
            initial = accepted(normal, key="initial")
            require(initial["remaining_stock"] == 1 and initial["balance_after"] == 992, "RE01 receipt")
            self.passed("RE01 normal stock=2 trainer A")
            require(accepted(normal, actor=other)["remaining_stock"] == 0, "RE02 second claim")
            self.passed("RE02 trainer B consumes final stock")
            rejected(normal, "PROMOTION_EXHAUSTED", actor=admin)
            self.passed("RE03 trainer C cannot oversell")
            mega = self.promotion(kind="mega", stock=1, price=5)
            require(accepted(mega)["remaining_stock"] == 0, "RE04 mega claim")
            rejected(mega, "PROMOTION_EXHAUSTED", actor=other)
            self.passed("RE04 mega stock=1")
            rejected(normal, "PROMOTION_ALREADY_CLAIMED")
            self.passed("RE05 different key cannot reclaim")
            self.patch("shop_items", normal["shop_item_id"], {"base_price": 20})
            self.patch("shop_promotions", normal["id"], {"effective_price": 7})
            before = self.state()
            require(accepted(normal, key="initial") == initial and self.state() == before, "RE06 historical retry")
            self.passed("RE06 replay preserves price/balance/stock snapshot after another claim")
            rejected(mega, "IDEMPOTENCY_CONFLICT", key="initial")
            rejected(normal, "IDEMPOTENCY_CONFLICT", key="initial", normal=True)
            self.passed("RE07 promo and cross-operation key conflicts")
            poor = self.promotion()
            self.fund_to(admin, 7)
            rejected(poor, "INSUFFICIENT_FUNDS", actor=admin)
            self.fund_to(admin, 8)
            require(accepted(poor, actor=admin)["balance_after"] == self.balance(admin) == 0, "Exact funds")
            self.passed("RE08 insufficient has no effects; exact funds reach zero")
            future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            for category in ("bayas", "comodines"):
                pending = self.promotion(status="pending", activates_at=future, category=category)
                rejected(pending, "PROMOTION_PENDING")
                if category == "comodines":
                    accepted(pending, normal=True, key="normal-pending")
                    rejected(pending, "IDEMPOTENCY_CONFLICT", key="normal-pending")
            self.passed("RE09 pending blocks promo; comodin base path remains 8D")
            expired = self.promotion(ends_at=datetime.now(timezone.utc).isoformat())
            rejected(expired, "PROMOTION_EXPIRED")
            self.passed("RE10 expired rejected without fallback")
            wrong_day = self.promotion(matchday_id=self.days[3]["id"])
            rejected(wrong_day, "PROMOTION_NOT_CURRENT")
            self.passed("RE11 explicit current matchday required")
            self.set_day(3)
            rejected(wrong_day, "STORE_BANNED", 403)
            self.set_day(2)
            self.passed("RE12 promotional route enforces Store Ban")

            purchase = self.read("purchases", id=initial["id"])[0]
            require(purchase["status"] == "pending" and purchase["quantity"] == 1
                    and purchase["unit_price"] == purchase["total_price"] == 8
                    and purchase["promotion_id"] == normal["id"] and purchase["balance_after"] == 992,
                    "RE13 authoritative purchase")
            self.passed("RE13 pending single-unit historical paid price")
            debit = self.read("coin_transactions", id=initial["ledger_id"])[0]
            require(debit["amount"] == -8 and debit["reference_id"] == purchase["id"]
                    and debit["transaction_type"] == "purchase", "RE14 exact debit")
            self.passed("RE14 linked negative ledger debit")
            event = self.read("public_activity_events", auth=other["token"], id=initial["event_id"])[0]
            require(event["type"] == "PURCHASE_COMPLETED"
                    and event["payload"] == {"purchase_id": purchase["id"], "item": "Validation promotion",
                        "quantity": 1, "price": 8, "base_price": 10, "promotion_id": normal["id"],
                        "promotion_kind": "normal"}
                    and event["context"]["matchday_id"] == self.days[2]["id"], "RE15 public event")
            self.passed("RE15 exact public purchase event")
            require(accepted(normal, normal=True)["unit_price"] == 20, "Claimed trainer can buy base again")
            self.passed("RE23 already claimed preserves ordinary repeat purchase")

            def race(requests, expected_successes, expected_error):
                barrier = Barrier(len(requests))
                before = self.state()

                def run(entry):
                    promo, actor, key, is_normal = entry
                    with TestClient(create_app(config=config)) as peer:
                        barrier.wait(timeout=30)
                        result = request(peer, promo, actor, key, normal=is_normal)
                        return result.status_code, result.json()

                with ThreadPoolExecutor(max_workers=len(requests)) as pool:
                    results = list(pool.map(run, requests))
                require(sum(status == 200 for status, _ in results) == expected_successes, "Race winner count")
                for status, body in results:
                    require(status == 200 or (status == 409 and body.get("detail", {}).get("code") == expected_error),
                            "Race error contract")
                after = self.state()
                unique_successes = len({body["id"] for status, body in results if status == 200})
                for table in ("purchases", "coin_transactions", "activity_events"):
                    require(len(after[table]) - len(before[table]) == unique_successes, "Race atomic effect count")
                for promo in after["shop_promotions"]:
                    claims = [row for row in after["purchases"] if row["promotion_id"] == promo["id"]]
                    require(len(claims) == promo["stock_used"] <= promo["stock_total"], "Race stock consistency")
                    require(len({row["trainer_id"] for row in claims}) == len(claims), "Race unique claim")
                require(all(self.balance(actor) >= 0 for actor in self.actors.values()), "Race cannot overspend")
                return results

            last = self.promotion(kind="mega", stock=1)
            race([(last, owner, "last-A", False), (last, other, "last-B", False)], 1, "PROMOTION_EXHAUSTED")
            self.passed("RE16 concurrent last-stock exactly one winner")
            one, two = self.promotion(), self.promotion(price=5)
            self.fund_to(admin, 8)
            race([(one, admin, "wallet-A", False), (two, admin, "wallet-B", False)], 1, "INSUFFICIENT_FUNDS")
            self.passed("RE17 concurrent wallet double-spend blocked")
            self.fund_to(admin, 10)
            mixed_base = self.promotion(category="comodines", status="pending", activates_at=future)
            mixed_promo = self.promotion()
            race([(mixed_base, admin, "mixed-A", True), (mixed_promo, admin, "mixed-B", False)], 1, "INSUFFICIENT_FUNDS")
            self.passed("RE24 shared 8D/8E wallet lock")
            same = self.promotion()
            race([(same, owner, "same-A", False), (same, owner, "same-B", False)], 1, "PROMOTION_ALREADY_CLAIMED")
            replay = self.promotion()
            results = race([(replay, owner, "replay", False)] * 2, 2, "")
            require(results[0][1] == results[1][1], "Concurrent identical replay")
            self.passed("RE25 concurrent same-trainer and same-key claims")
            combined = self.promotion()
            for actor in self.actors.values():
                self.fund_to(actor, 8)
            race([(combined, actor, "combined", False) for actor in self.actors.values()], 2, "PROMOTION_EXHAUSTED")
            self.passed("RE26 combined limited-wallet and shared-stock race")

        args = {"p_season_id": self.season_id, "p_trainer_id": owner["trainer"]["id"],
                "p_promotion_id": normal["id"], "p_idempotency_key": "direct"}
        for actor in (owner, admin):
            require(self.rpc_call("api_create_promotional_purchase", args, actor["token"]).status == 403, "RE18 direct RPC")
        self.passed("RE18 owner/admin direct RPC denied")
        for table, row, field, value in (("purchases", purchase, "unit_price", 1),
                                         ("coin_transactions", debit, "amount", 999),
                                         ("shop_promotions", normal, "stock_used", 0)):
            original = self.read(table, id=row["id"])
            for actor in (owner, admin):
                insert = {k: v for k, v in row.items() if k not in ("id", "total_price", "created_at", "purchased_at")}
                insert[field] = value
                for method, body, params in (("POST", insert, None), ("PATCH", {field: value}, {"id": "eq." + row["id"]})):
                    result = self.http.rest(method, table, auth=actor["token"], body=body, params=params, raise_on_error=False)
                    require(direct_write_denied(method, result), "RE19 direct write denied")
                    require(self.read(table, id=row["id"]) == original, "RE19 unchanged row")
        self.passed("RE19 direct economic/stock writes denied, including browser admin")
        for relation, row_id in (("purchases", initial["id"]), ("current_purchases", initial["id"]),
                                  ("coin_transactions", initial["ledger_id"]), ("current_coin_transactions", initial["ledger_id"])):
            for actor in (owner, admin):
                require(len(self.read(relation, auth=actor["token"], id=row_id)) == 1, "RE20 owner/admin read")
            require(self.read(relation, auth=other["token"], id=row_id) == [], "RE20 private isolation")
        self.passed("RE20 owner/admin private access and trainer isolation")
        for actor in self.actors.values():
            rows = self.read("public_coin_balances", auth=other["token"], season_id=self.season_id,
                             trainer_id=actor["trainer"]["id"])
            require(len(rows) == 1 and rows[0]["balance"] == self.balance(actor), "RE21 public balance")
        self.passed("RE21 public balances equal ledger")
        require(self.rpc_call("api_create_promotional_purchase", args, "anon").status in (401, 403), "RE22 anon RPC")
        for table in ("purchases", "coin_transactions", "shop_promotions", "public_coin_balances", "public_activity_events"):
            result = self.http.rest("GET", table, auth="anon", params={"select": "*", "limit": "1"}, raise_on_error=False)
            require(result.status in (401, 403), "RE22 anon read")
        self.passed("RE22 anon denied")
        for table in ("save_files", "redemptions"):
            require(self.read(table, season_id=self.season_id) == [], "No save/redemption effects")
        self.passed("RE27 no save or redemption effects")
        print("Failure-injection triggers remain LOCAL only; no staging failure DDL.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--allow-staging-writes", action="store_true")
    args = parser.parse_args()
    validation = None
    failure = None
    remaining = []
    try:
        config = replace(staging_config(args.env_file, args.allow_staging_writes),
                         run_id="phase8e_validation_" + uuid4().hex)
        validation = PromotionalPurchaseValidation(config)
        print(f"V2 staging={config.url}\nrun_id={config.run_id}\nsecrets=redacted", flush=True)
        validation.setup_context()
        validation.validate_promotions()
    except Exception as exc:
        failure = str(exc) if isinstance(exc, ValidationError) and not str(exc).startswith("HTTP ") else type(exc).__name__
    finally:
        if validation:
            remaining = validation.cleanup()
            print("CLEANUP " + ("FAIL " + ",".join(remaining) if remaining else "PASS"), flush=True)
    if failure or remaining:
        print("RESULT failed: " + (failure or "cleanup incomplete"), flush=True)
        return 1
    print(f"RESULT ok checks={len(validation.checks)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
