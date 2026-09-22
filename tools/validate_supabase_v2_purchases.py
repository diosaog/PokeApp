"""Opt-in V2 staging contract/purchase checks; never touches V1 or real fixtures."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import secrets
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_supabase_v2_rls import ValidationError
from tools.validate_supabase_v2_team_lock import TeamLockValidation, require, staging_config, direct_write_denied


class PurchaseValidation(TeamLockValidation):
    def rpc_call(self, name, args, auth="service"):
        return self.http.request("POST", self.http.rest_url + "/rpc/" + name,
                                 auth=auth, body=args, raise_on_error=False)

    def setup_context(self):
        active = self.http.rest("GET", "seasons", auth="service", params={"select": "id", "status": "eq.active", "limit": "1"})
        require(active.data == [], "Staging already has an active season; refusing to alter it")
        self.actors = {}
        for role in ("owner", "other", "admin"):
            email = f"{self.config.run_id}_{role}@{self.config.email_domain}"
            password = "PokeApp!" + secrets.token_urlsafe(28)
            user_id = self.http.auth_create_user(email, password)
            self.users.append(user_id)
            token = self.http.auth_sign_in(email, password)
            trainer = self.insert("trainers", {"display_name": f"{self.config.run_id}_{role}",
                "slug": f"{self.config.run_id}_{role}", "auth_user_id": user_id, "is_admin": role == "admin",
                "metadata": {"validation_run": self.config.run_id}})
            self.actors[role] = dict(trainer=trainer, token=token)
        season = self.insert("seasons", {"name": self.config.run_id, "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(), "metadata": {"validation_run": self.config.run_id}})
        self.season_id = season["id"]
        self.other_season = self.insert("seasons", {"name": self.config.run_id + "_other", "metadata": {"validation_run": self.config.run_id}})
        self.days = {}
        for season_id, count in ((self.season_id, 5), (self.other_season["id"], 1)):
            config = self.insert("season_config_versions", {"season_id": season_id, "version_number": 1,
                "name": self.config.run_id, "effective_from_matchday": 1, "total_matchdays": 5, "division_count": 2})
            for number in range(1, count + 1):
                day = self.insert("matchdays", {"season_id": season_id, "number": number, "status": "scheduled",
                                                "season_config_version_id": config["id"]})
                if season_id == self.season_id:
                    self.days[number] = day
                else:
                    self.other_day = day
        for actor in self.actors.values():
            actor["player"] = self.insert("season_players", {"season_id": self.season_id,
                "trainer_id": actor["trainer"]["id"], "metadata": {"validation_run": self.config.run_id}})
        self.case = self.insert("trial_cases", {"season_id": self.season_id, "title": self.config.run_id,
            "status": "resolved", "accused_trainer_id": self.actors["owner"]["trainer"]["id"]})
        self.penalty = self.insert("penalties", {"season_id": self.season_id,
            "trainer_id": self.actors["owner"]["trainer"]["id"], "trial_case_id": self.case["id"],
            "penalty_type": "store_ban", "start_matchday_number": 3, "end_matchday_number": 4})

    def set_day(self, number):
        self.patch("seasons", self.season_id, {"current_matchday_id": self.days[number]["id"]})

    def validate_context(self):
        args = {"p_season_id": self.season_id}
        result = self.rpc_call("api_resolve_current_matchday", args)
        require(result.status == 409, "NULL current pointer must conflict")
        bad = self.http.rest("PATCH", "seasons", auth="service", params={"id": "eq." + self.season_id},
                            body={"current_matchday_id": self.other_day["id"]}, raise_on_error=False)
        require(bad.status == 409 and bad.data.get("code") == "23503", "Same-season FK must reject foreign day")
        self.set_day(3)
        result = self.rpc_call("api_resolve_current_matchday", args)
        require(result.ok and result.data[0]["number"] == 3, "Explicit scheduled pointer")
        self.patch("matchdays", self.days[3]["id"], {"status": "cancelled"})
        require(self.rpc_call("api_resolve_current_matchday", args).status == 409, "Cancelled pointer rejected")
        self.patch("matchdays", self.days[3]["id"], {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat()})
        require(self.rpc_call("api_resolve_current_matchday", args).data[0]["number"] == 3, "Closed pointer not advanced")
        self.passed("D0 current pointer NULL/FK/scheduled/cancelled/closed")
        owner = self.actors["owner"]

        def banned(n, trainer=owner["trainer"]["id"]):
            response = self.rpc_call("api_is_store_banned", {"p_season_id": self.season_id,
                "p_trainer_id": trainer, "p_matchday_number": n})
            require(response.ok and type(response.data) is bool, "Store-ban RPC response")
            return response.data

        for n in (2, 3, 4, 5):
            require(banned(n) == (n in (3, 4)), "Inclusive store-ban boundaries")
        self.passed("D0 inclusive windows 2/3/4/5")
        self.patch("penalties", self.penalty["id"], {"resolved_at": datetime.now(timezone.utc).isoformat()})
        require(banned(3), "resolved_at must not expire ban")
        for start, end in ((3, None), (None, 4), (None, None)):
            self.patch("penalties", self.penalty["id"], {"start_matchday_number": start, "end_matchday_number": end})
            require(banned(99), "Missing/partial window active")
        self.passed("D0 missing/partial window and resolved_at")
        self.patch("trial_cases", self.case["id"], {"status": "open"})
        require(not banned(3), "Unfinished case cannot ban")
        self.patch("trial_cases", self.case["id"], {"status": "resolved"})
        require(not banned(3, self.actors["other"]["trainer"]["id"]), "Other trainer unaffected")
        self.patch("penalties", self.penalty["id"], {"penalty_type": "coins_reduction"})
        require(not banned(3), "Unrelated penalty cannot ban")
        self.passed("D0 finished case and type/trainer scoping")
        for auth in ("anon", owner["token"]):
            require(self.rpc_call("api_resolve_current_matchday", args, auth).status in (401, 403), "Direct helper denied")
        admin_pointer = self.http.rest("PATCH", "seasons", auth=self.actors["admin"]["token"],
            params={"id": "eq." + self.season_id}, body={"current_matchday_id": None}, raise_on_error=False)
        require(admin_pointer.status == 403, "Current pointer remains backend-only even for browser admin")
        for table, row_id, body in (("seasons", self.season_id, {"current_matchday_id": None}),
                                    ("penalties", self.penalty["id"], {"start_matchday_number": 2})):
            before = self.read(table, id=row_id)
            response = self.http.rest("PATCH", table, auth=owner["token"], params={"id": "eq." + row_id}, body=body, raise_on_error=False)
            require(direct_write_denied("PATCH", response) and self.read(table, id=row_id) == before, "Trainer cannot alter eligibility")
        self.passed("D0 helper permissions and unchanged trainer write restrictions")

    def cleanup(self):
        remaining = []
        for table in ("coin_transactions", "purchases", "shop_promotions", "penalties", "trial_cases", "shop_items"):
            params_list = [{"id": "eq." + x} for x in self.rows.get(table, [])]
            if table in ("coin_transactions", "purchases") and self.season_id:
                params_list = [{"season_id": "eq." + self.season_id}]
            for params in params_list:
                try:
                    result = self.http.rest("DELETE", table, auth="service", params=params, raise_on_error=False)
                    checked = self.http.rest("GET", table, auth="service", params={**params, "select": "id"}, raise_on_error=False)
                    if not result.ok or not checked.ok or checked.data != []:
                        remaining.append(table + ":" + next(iter(params.values())))
                except Exception:
                    remaining.append(table + ":" + next(iter(params.values())))
        for season_id in self.rows.get("seasons", []):
            try:
                result = self.http.rest("PATCH", "seasons", auth="service", params={"id": "eq." + season_id},
                                        body={"current_matchday_id": None}, raise_on_error=False)
                if not result.ok:
                    remaining.append("season pointer:" + season_id)
            except Exception:
                remaining.append("season pointer:" + season_id)
        return remaining + super().cleanup()

    def validate_purchases(self):
        from fastapi.testclient import TestClient
        from app.api.config import APIConfig
        from app.api.main import create_app

        owner, other, admin = (self.actors[x] for x in ("owner", "other", "admin"))
        self.set_day(2)
        item = self.insert("shop_items", {"code": self.config.run_id + "_item", "name": "Validation Berry",
                                         "category": "bayas", "base_price": 10})
        comodin = self.insert("shop_items", {"code": self.config.run_id + "_comodin", "name": "Validation Comodin",
                                            "category": "comodines", "base_price": 10})
        for actor, amount in ((owner, 1000), (other, 10), (admin, 10)):
            self.insert("coin_transactions", {"season_id": self.season_id, "trainer_id": actor["trainer"]["id"],
                "season_player_id": actor["player"]["id"], "amount": amount, "transaction_type": "admin_adjustment"})
        config = APIConfig(supabase_url=self.config.url, supabase_anon_key=self.config.anon_key,
                           supabase_service_role_key=self.config.service_role_key)
        path = f"/v1/seasons/{self.season_id}/shop/purchases"

        def counts():
            return tuple(len(self.read(t, season_id=self.season_id)) for t in ("purchases", "coin_transactions", "activity_events"))

        with TestClient(create_app(config=config)) as client:
            def buy(key=None, actor=owner, selected=item, confirm=False):
                return client.post(path, headers={"Authorization": "Bearer " + actor["token"],
                    "Idempotency-Key": key or uuid4().hex}, json={"item_id": selected["id"], "confirm_base_price": confirm})

            def accepted(*args, **kwargs):
                result = buy(*args, **kwargs)
                require(result.status_code == 200, f"Purchase expected success, HTTP {result.status_code}")
                return result.json()

            def rejected(code, status=409, **kwargs):
                before = counts()
                result = buy(**kwargs)
                require(result.status_code == status and result.json().get("detail", {}).get("code") == code,
                        f"Expected {status} {code}; got HTTP {result.status_code}")
                require(counts() == before, "Rejected purchase created partial effects")

            initial = accepted("initial")
            require(initial["trainer_id"] == owner["trainer"]["id"], "R01 verified identity")
            self.passed("R01 real JWT API normal purchase")
            purchase = self.read("purchases", id=initial["id"])[0]
            require(purchase["quantity"] == 1 and purchase["status"] == "pending" and purchase["unit_price"] == 10, "R02 pending row")
            self.passed("R02 pending single-unit authoritative price")
            debit = self.read("coin_transactions", id=initial["ledger_id"])[0]
            require(debit["amount"] == -10 and debit["reference_id"] == purchase["id"] and debit["transaction_type"] == "purchase", "R03 debit")
            self.passed("R03 exact linked debit")
            event = self.read("public_activity_events", auth=other["token"], id=initial["event_id"])[0]
            require(event["type"] == "PURCHASE_COMPLETED" and event["payload"]["purchase_id"] == purchase["id"], "R04 public event")
            self.passed("R04 public purchase event")
            require(initial["balance_after"] == purchase["balance_after"] == 990, "R05 balance snapshot")
            self.passed("R05 balance_after snapshot")
            require(accepted(actor=admin)["balance_after"] == 0, "R06 exact balance")
            self.passed("R06 exact balance zero")
            rejected("INSUFFICIENT_FUNDS", actor=admin)
            self.passed("R07 insufficient funds has no effects")
            accepted("second")
            self.patch("shop_items", item["id"], {"base_price": 20})
            before = counts()
            require(accepted("initial", confirm=True) == initial and counts() == before, "R08 stable original receipt")
            require(self.read("purchases", id=initial["id"])[0]["unit_price"] == 10, "R08 historical price")
            self.patch("shop_items", item["id"], {"base_price": 10})
            self.passed("R08 idempotent retry preserves price and original balance")
            rejected("IDEMPOTENCY_CONFLICT", key="initial", selected=comodin)
            self.passed("R09 conflicting item rejected")

            # Separate API containers/HTTP clients and a barrier ensure actual overlap.
            from threading import Barrier
            barrier = Barrier(2)

            def concurrent_buy(n):
                with TestClient(create_app(config=config)) as concurrent_client:
                    barrier.wait(timeout=30)
                    response = concurrent_client.post(path, headers={"Authorization": "Bearer " + other["token"],
                        "Idempotency-Key": f"race-{n}"}, json={"item_id": item["id"]})
                    return response.status_code, response.json()

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(concurrent_buy, range(2)))
            require(sorted(x[0] for x in results) == [200, 409], "R10 exactly one concurrent success")
            require(next(x[1] for x in results if x[0] == 409)["detail"]["code"] == "INSUFFICIENT_FUNDS", "R10 insufficient loser")
            require(len(self.read("purchases", season_id=self.season_id, trainer_id=other["trainer"]["id"])) == 1, "R10 one purchase")
            require(sum(x["amount"] for x in self.read("coin_transactions", season_id=self.season_id, trainer_id=other["trainer"]["id"])) == 0, "R10 no overspend")
            self.passed("R10 concurrent double-spend prevented")

            self.patch("penalties", self.penalty["id"], {"penalty_type": "store_ban", "start_matchday_number": 3, "end_matchday_number": 4})
            self.set_day(3)
            rejected("STORE_BANNED", 403)
            self.set_day(4)
            rejected("STORE_BANNED", 403)
            self.passed("R11 inclusive Store Ban boundaries")
            self.set_day(5)
            accepted()
            self.passed("R12 outside ban window allowed")
            self.patch("penalties", self.penalty["id"], {"start_matchday_number": None, "end_matchday_number": None})
            rejected("STORE_BANNED", 403)
            self.passed("R13 no-window Store Ban active")
            self.patch("trial_cases", self.case["id"], {"status": "open"})
            accepted()
            self.passed("R14 unfinished case does not ban")
            self.patch("penalties", self.penalty["id"], {"penalty_type": "coins_reduction"})
            self.set_day(2)
            promo_body = {"season_id": self.season_id, "matchday_id": self.days[2]["id"], "shop_item_id": item["id"],
                          "promotion_type": "normal", "status": "pending", "base_price": 10, "effective_price": 5, "stock_total": 2}
            promo = self.insert("shop_promotions", promo_body)
            rejected("PROMOTION_PENDING")
            self.passed("R15 pending non-comodin blocked")
            self.insert("shop_promotions", {**promo_body, "shop_item_id": comodin["id"]})
            accepted(selected=comodin)
            self.passed("R16 pending comodin base purchase allowed")
            self.patch("shop_promotions", promo["id"], {"status": "active"})
            rejected("PROMOTION_AVAILABLE", confirm=True)
            self.passed("R17 active unclaimed promotion cannot be bypassed")
            for status in ("exhausted", "ended"):
                self.patch("shop_promotions", promo["id"], {"status": status})
                rejected("BASE_PRICE_CONFIRMATION_REQUIRED")
            self.passed("R18 exhausted/expired requires confirmation")
            accepted("confirmed", confirm=True)
            rejected("IDEMPOTENCY_CONFLICT", key="confirmed", confirm=False)
            self.passed("R19 explicit fallback and relevant idempotency semantics")

        args = {"p_season_id": self.season_id, "p_trainer_id": owner["trainer"]["id"], "p_item_id": item["id"],
                "p_idempotency_key": "direct", "p_confirm_base_price": False}
        for actor in (owner, admin):
            require(self.rpc_call("api_create_normal_purchase", args, actor["token"]).status == 403, "R20 direct RPC denied")
        self.passed("R20 owner/admin direct RPC denied")
        for table, row, forbidden_field, value in (("purchases", purchase, "unit_price", 1),
                                                  ("coin_transactions", debit, "amount", 999)):
            for actor in (owner, admin):
                original = self.read(table, id=row["id"])
                insert = {k: v for k, v in row.items() if k not in ("id", "total_price", "created_at", "purchased_at")}
                for method, body, params in (("POST", insert, None),
                                             ("PATCH", {forbidden_field: value}, {"id": "eq." + row["id"]})):
                    result = self.http.rest(method, table, auth=actor["token"], body=body, params=params, raise_on_error=False)
                    require(direct_write_denied(method, result), "R21 direct write denied")
                    require(self.read(table, id=row["id"]) == original, "R21 unchanged row")
        self.passed("R21 owner/admin direct purchase and ledger writes denied")
        for relation, row_id in (("purchases", initial["id"]), ("current_purchases", initial["id"]),
                                  ("coin_transactions", initial["ledger_id"]), ("current_coin_transactions", initial["ledger_id"])):
            for actor in (owner, admin):
                require(len(self.read(relation, auth=actor["token"], id=row_id)) == 1, "R22 owner/admin read")
            require(self.read(relation, auth=other["token"], id=row_id) == [], "R22 trainer isolation")
        self.passed("R22 private owner/admin reads and other-trainer isolation")
        balances = self.read("public_coin_balances", auth=other["token"], season_id=self.season_id, trainer_id=owner["trainer"]["id"])
        actual = sum(x["amount"] for x in self.read("coin_transactions", season_id=self.season_id, trainer_id=owner["trainer"]["id"]))
        require(len(balances) == 1 and balances[0]["balance"] == actual, "R23 public balance projection")
        self.passed("R23 public balance agrees with ledger")
        require(self.rpc_call("api_create_normal_purchase", args, "anon").status in (401, 403), "R24 anon RPC")
        for table in ("purchases", "coin_transactions", "public_coin_balances", "public_activity_events"):
            result = self.http.rest("GET", table, auth="anon", params={"select": "*", "limit": "1"}, raise_on_error=False)
            require(result.status in (401, 403), "R24 anon read denied")
        self.passed("R24 anon denied")
        print("Deep write-failure injection: local PostgreSQL only; no intrusive staging DDL.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--allow-staging-writes", action="store_true")
    parser.add_argument("--suite", choices=("context", "purchase"), default="context")
    args = parser.parse_args()
    validation = None
    failure = None
    remaining = []
    try:
        config = staging_config(args.env_file, args.allow_staging_writes)
        prefix = "phase8d0_validation_" if args.suite == "context" else "phase8d_validation_"
        config = replace(config, run_id=prefix + uuid4().hex)
        validation = PurchaseValidation(config)
        print(f"V2 staging={config.url}\nrun_id={config.run_id}\nsecrets=redacted", flush=True)
        validation.setup_context()
        validation.validate_context()
        if args.suite == "purchase":
            validation.validate_purchases()
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
