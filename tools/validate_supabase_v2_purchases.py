"""Opt-in V2 staging contract/purchase checks; never touches V1 or real fixtures."""
from __future__ import annotations

import argparse
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
            result = self.http.rest("PATCH", "seasons", auth="service", params={"id": "eq." + season_id},
                                    body={"current_matchday_id": None}, raise_on_error=False)
            if not result.ok:
                remaining.append("season pointer:" + season_id)
        return remaining + super().cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--allow-staging-writes", action="store_true")
    args = parser.parse_args()
    validation = None
    failure = None
    remaining = []
    try:
        config = staging_config(args.env_file, args.allow_staging_writes)
        config = replace(config, run_id="phase8d0_validation_" + uuid4().hex)
        validation = PurchaseValidation(config)
        print(f"V2 staging={config.url}\nrun_id={config.run_id}\nsecrets=redacted", flush=True)
        validation.setup_context()
        validation.validate_context()
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
