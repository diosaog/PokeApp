"""Opt-in Team Lock validation against the approved V2 staging project only."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_supabase_v2_rls import Config, SupabaseHttp, ValidationError, _load_env_file

STAGING_URL = "https://uwleqeuzsveqlugugzba.supabase.co"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValidationError(label)


def direct_write_denied(method: str, result) -> bool:
    # PostgREST returns an empty representation when RLS filters an UPDATE.
    return result.status in (401, 403) or (method == "PATCH" and result.status == 200 and result.data == [])


def staging_config(env_file: Path, allow_writes: bool) -> Config:
    require(allow_writes, "Explicit --allow-staging-writes is required")
    _load_env_file(env_file)
    url = os.environ.get("POKEAPP_V2_SUPABASE_URL", "").rstrip("/")
    require(url == STAGING_URL, "Refusing an unapproved project; V2 staging only")
    anon = os.environ.get("POKEAPP_V2_SUPABASE_ANON_KEY", "")
    service = os.environ.get("POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY", "")
    require(bool(anon and service), "Missing V2 credentials")
    return Config(url, anon, service, os.environ.get("POKEAPP_V2_TEST_EMAIL_DOMAIN", "example.com"),
                  True, "phase8c_validation_" + uuid4().hex)


class TeamLockValidation:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.http = SupabaseHttp(config)
        self.rows: dict[str, list[str]] = {}
        self.users: list[str] = []
        self.checks: list[str] = []
        self.season_id: str | None = None

    def passed(self, name: str) -> None:
        self.checks.append(name)
        print("PASS " + name, flush=True)

    def insert(self, table: str, body: dict) -> dict:
        row_id = str(uuid4())
        self.rows.setdefault(table, []).append(row_id)
        result = self.http.rest("POST", table, auth="service", body={"id": row_id, **body})
        require(isinstance(result.data, list) and len(result.data) == 1, "Fixture insert: " + table)
        require(result.data[0]["id"] == row_id, "Fixture identity: " + table)
        return result.data[0]

    def read(self, table: str, *, auth: str = "service", **filters) -> list[dict]:
        result = self.http.rest("GET", table, auth=auth,
                                params={"select": "*", **{k: "eq." + str(v) for k, v in filters.items()}})
        require(isinstance(result.data, list), "Expected rows: " + table)
        return result.data

    def patch(self, table: str, row_id: str, body: dict) -> None:
        require(row_id in self.rows.get(table, []), "Refusing to update a non-fixture row")
        result = self.http.rest("PATCH", table, auth="service", params={"id": "eq." + row_id}, body=body)
        require(len(result.data) == 1, "Fixture patch: " + table)

    def rpc(self, body: dict, auth: str = "service"):
        return self.http.request("POST", self.http.rest_url + "/rpc/api_upsert_team_lock",
                                 auth=auth, body=body, raise_on_error=False)

    def setup(self) -> dict:
        from app.domain.common import to_jsonable
        from app.domain.pokemon import PrivatePokemon, StatSpread

        actors = {}
        password = "PokeApp!" + secrets.token_urlsafe(28)
        for role in ("owner", "other", "admin"):
            email = f"{self.config.run_id}_{role}@{self.config.email_domain}"
            user_id = self.http.auth_create_user(email, password)
            self.users.append(user_id)
            token = self.http.auth_sign_in(email, password)
            trainer = self.insert("trainers", {
                "display_name": f"{self.config.run_id}_{role}", "slug": f"{self.config.run_id}_{role}",
                "auth_user_id": user_id, "is_admin": role == "admin",
                "metadata": {"validation_run": self.config.run_id},
            })
            actors[role] = {"trainer": trainer, "token": token}
        season = self.insert("seasons", {
            "name": self.config.run_id, "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"validation_run": self.config.run_id},
        })
        self.season_id = season["id"]
        for actor in actors.values():
            actor["player"] = self.insert("season_players", {
                "season_id": self.season_id, "trainer_id": actor["trainer"]["id"],
                "metadata": {"validation_run": self.config.run_id},
            })
        config = self.insert("season_config_versions", {
            "season_id": self.season_id, "version_number": 1, "name": self.config.run_id,
            "effective_from_matchday": 1, "total_matchdays": 4, "division_count": 2,
        })
        matchday = self.insert("matchdays", {
            "season_id": self.season_id, "number": 1, "status": "open",
            "season_config_version_id": config["id"],
        })
        saves = []
        parsed = []
        for index, role in enumerate(("owner", "owner", "other"), start=1):
            save = self.insert("save_files", {
                "season_id": self.season_id, "trainer_id": actors[role]["trainer"]["id"],
                "storage_key": f"{self.config.run_id}/{index}.sav", "original_filename": "validation.sav",
                "sha256": str(index) * 64, "parser_status": "parsed", "parser_version": "phase8c-fixture-v1",
                "metadata": {"validation_run": self.config.run_id},
            })
            pokemon = PrivatePokemon(species="Milotic" if index == 1 else "Crobat", ability="Private ability",
                                     nature="Bold", ivs=StatSpread(hp=31), evs=StatSpread(hp=252),
                                     original_trainer="private-owner", metadata={"private_marker": self.config.run_id})
            payload = {"party": [{"slot_number": slot, "pokemon": to_jsonable(pokemon)} for slot in range(1, 7)]}
            parsed.append(self.insert("parsed_saves", {
                "save_file_id": save["id"], "parser_version": save["parser_version"], "payload": payload,
                "metadata": {"validation_run": self.config.run_id},
            }))
            saves.append(save)
        return {"actors": actors, "matchday": matchday, "saves": saves, "parsed": parsed}

    def validate(self, fx: dict) -> None:
        from fastapi.testclient import TestClient
        from app.api.config import APIConfig
        from app.api.main import create_app
        from app.domain.services.team_locks import snapshots_from_parsed_payload

        owner, other, admin = (fx["actors"][role] for role in ("owner", "other", "admin"))
        save1, save2, other_save = fx["saves"]
        parsed1, parsed2, _ = fx["parsed"]
        public, private = snapshots_from_parsed_payload(parsed1["payload"])
        args = {
            "p_season_id": self.season_id, "p_matchday_id": fx["matchday"]["id"],
            "p_trainer_id": owner["trainer"]["id"], "p_season_player_id": owner["player"]["id"],
            "p_save_file_id": save1["id"], "p_save_sha256": save1["sha256"],
            "p_parsed_save_id": parsed1["id"], "p_parsed_payload": parsed1["payload"],
            "p_public_team_snapshot": public, "p_private_team_snapshot": private,
        }
        for label, auth in (("anon", "anon"), ("authenticated", owner["token"])):
            denied = self.rpc(args, auth=auth)
            require(denied.status in (401, 403) and denied.data.get("code") == "42501", "RPC denial: " + label)
        self.passed("TL09 anon/authenticated RPC execution denied")

        with TestClient(create_app(config=APIConfig(
            supabase_url=self.config.url, supabase_anon_key=self.config.anon_key,
            supabase_service_role_key=self.config.service_role_key,
        ))) as client:
            path = f"/v1/seasons/{self.season_id}/matchdays/{fx['matchday']['id']}/team-lock"

            def put(save_id: str, actor=owner, *, endpoint=path, extra=None):
                return client.put(endpoint, headers={"Authorization": "Bearer " + actor["token"]},
                                  json={"save_file_id": save_id, **(extra or {})})

            response = put(save1["id"])
            require(response.status_code == 200, f"TL01 API first lock HTTP {response.status_code}")
            initial = response.json()
            require(initial["trainer_id"] == owner["trainer"]["id"], "TL01 owner")
            require(initial["save_sha256"] == save1["sha256"], "TL01 authoritative hash")
            self.passed("TL01 first API Team Lock, real JWT and service RPC")
            require(len(initial["private_team_snapshot"]) == len(initial["public_team_snapshot"]) == 6, "TL02 six slots")
            self.patch("parsed_saves", parsed2["id"], {"payload": {"party": parsed2["payload"]["party"][:5]}})
            require(put(save2["id"]).status_code == 409, "TL02 reject five slots")
            self.patch("parsed_saves", parsed2["id"], {"payload": parsed2["payload"]})
            self.passed("TL02 exactly six Pokemon; five rejected")
            event = self.read("activity_events", season_id=self.season_id)
            require(len(event) == 1 and event[0]["type"] == "TEAM_LOCKED", "TL04 event")
            require(event[0]["payload"]["lock_id"] == initial["id"], "TL04 event references lock")
            self.passed("TL04 activity event committed")
            replacement = put(save2["id"])
            require(replacement.status_code == 200, "TL03 replacement")
            require(replacement.json()["id"] == initial["id"], "TL03 stable logical lock")
            require(replacement.json()["save_file_id"] == save2["id"], "TL03 new source")
            require(len(self.read("team_locks", season_id=self.season_id)) == 1, "TL03 one row")
            self.passed("TL03 replacement preserves one logical row")
            require(put(save2["id"]).status_code == 200, "TL05 retry")
            require(self.read("activity_events", season_id=self.season_id) == event, "TL05 first event immutable/deduped")
            self.passed("TL05 repeat and replacement do not duplicate activity")
            require(put(save1["id"], other).status_code == 404, "TL06 other cannot lock owner's save")
            require(put(other_save["id"], other, extra={"trainer_id": owner["trainer"]["id"]}).status_code == 422,
                    "TL06 forged trainer rejected")
            self.passed("TL06 identity cannot be forged through API")
            require(put(other_save["id"]).status_code == 404, "TL07 foreign save")
            self.passed("TL07 foreign save rejected")
            wrong = path.replace(self.season_id, str(uuid4()))
            require(put(save1["id"], endpoint=wrong).status_code == 404, "TL08 wrong season")
            wrong = path.replace(fx["matchday"]["id"], str(uuid4()))
            require(put(save1["id"], endpoint=wrong).status_code == 404, "TL08 wrong matchday")
            self.passed("TL08 wrong season/matchday rejected")

        lock = self.read("team_locks", season_id=self.season_id)[0]
        insert_body = {k: v for k, v in lock.items() if k not in ("created_at", "updated_at")}
        insert_body["id"] = str(uuid4())
        for actor in (owner, admin):
            for method, body, params in (
                ("POST", insert_body, None),
                ("PATCH", {"private_team_snapshot": []}, {"id": "eq." + lock["id"]}),
            ):
                denied = self.http.rest(method, "team_locks", auth=actor["token"], body=body,
                                        params=params, raise_on_error=False)
                require(direct_write_denied(method, denied), f"TL10 direct {method} HTTP {denied.status} must be denied")
                require(self.read("team_locks", season_id=self.season_id) == [lock], "TL10 denied write changed rows")
                print(f"TL10 direct {method}: HTTP {denied.status}, no row changed", flush=True)
        require(self.read("team_locks", season_id=self.season_id) == [lock], "TL10 denied writes unchanged")
        self.passed("TL10 owner/admin direct INSERT and UPDATE denied")
        for actor in (owner, admin):
            for relation in ("team_locks", "current_team_locks"):
                rows = self.read(relation, auth=actor["token"], id=lock["id"])
                require(len(rows) == 1 and rows[0]["private_team_snapshot"] == lock["private_team_snapshot"],
                        "TL11 private read: " + relation)
        self.passed("TL11 owner/admin private and current reads")
        for relation in ("team_locks", "current_team_locks"):
            require(self.read(relation, auth=other["token"], id=lock["id"]) == [], "TL12 private isolation")
        public_rows = self.read("public_team_locks", auth=other["token"], id=lock["id"])
        require(len(public_rows) == 1, "TL12 public projection visible")
        require(not {"private_team_snapshot", "save_file_id", "save_sha256", "metadata"}.intersection(public_rows[0]),
                "TL12 private columns absent")
        for mon in public_rows[0]["public_team_snapshot"]:
            require(not {"ivs", "evs", "nature", "ability", "original_trainer"}.intersection(mon), "TL12 Pokemon privacy")
            require(not mon.get("metadata"), "TL12 arbitrary metadata not public")
        for relation in ("trainers", "team_locks", "public_team_locks", "current_team_locks"):
            denied = self.http.rest("GET", relation, auth="anon", params={"select": "id", "limit": "1"}, raise_on_error=False)
            require(denied.status in (401, 403), "Anon app read denied: " + relation)
        self.passed("TL12 other/public separation and anon denied")

        stale = deepcopy(parsed1["payload"])
        stale["validation_revision"] = 2
        self.patch("parsed_saves", parsed1["id"], {"payload": stale})
        rejected = self.rpc(args)
        require(rejected.status == 409 and rejected.data.get("code") == "PT409", "TL13 stale payload")
        self.patch("parsed_saves", parsed1["id"], {"payload": parsed1["payload"]})
        rejected = self.rpc({**args, "p_save_sha256": "f" * 64})
        require(rejected.status == 409 and rejected.data.get("code") == "PT409", "TL13 stale hash")
        require(self.read("team_locks", season_id=self.season_id) == [lock], "TL13 rejected writes unchanged")
        require(self.read("activity_events", season_id=self.season_id) == event, "TL13 no rejected-write event")
        self.passed("TL13 stale payload/hash rejected without changes")
        print("TL14 NOT RUN remotely: forced post-write failure requires intrusive DDL; local PostgreSQL covers rollback.", flush=True)

    def cleanup(self) -> list[str]:
        remaining = []
        # Scope generated RPC rows by our unique season, even if a response was lost.
        targets = []
        if self.season_id:
            for table in ("activity_events", "team_locks"):
                targets.append((table, {"season_id": "eq." + self.season_id}, self.season_id))
        for table in ("parsed_saves", "save_files", "matchdays", "season_config_versions", "season_players", "seasons", "trainers"):
            targets.extend((table, {"id": "eq." + row_id}, row_id) for row_id in reversed(self.rows.get(table, [])))
        for table, params, row_id in targets:
            try:
                deleted = self.http.rest("DELETE", table, auth="service", params=params, raise_on_error=False)
                result = self.http.rest("GET", table, auth="service", params={**params, "select": "id"}, raise_on_error=False)
                if not deleted.ok or not result.ok or result.data != []:
                    remaining.append(f"{table}:{row_id}")
            except Exception:
                remaining.append(f"{table}:{row_id}")
        if not any(row.startswith("trainers:") for row in remaining):
            for user_id in reversed(self.users):
                try:
                    url = self.http.auth_url + "/admin/users/" + user_id
                    deleted = self.http.request("DELETE", url, auth="service", raise_on_error=False)
                    checked = self.http.request("GET", url, auth="service", raise_on_error=False)
                    if not (deleted.ok or deleted.status == 404) or checked.status != 404:
                        remaining.append("auth.users:" + user_id)
                except Exception:
                    remaining.append("auth.users:" + user_id)
        else:
            remaining.extend("auth.users:" + user_id for user_id in self.users)
        return remaining


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--allow-staging-writes", action="store_true")
    args = parser.parse_args()
    validation = None
    failure = None
    remaining = []
    try:
        config = staging_config(args.env_file, args.allow_staging_writes)
        validation = TeamLockValidation(config)
        print(f"V2 staging={config.url}\nrun_id={config.run_id}\nsecrets=redacted", flush=True)
        validation.validate(validation.setup())
    except Exception as exc:
        # HTTP/library errors can contain sensitive payloads; never echo those.
        failure = str(exc) if isinstance(exc, ValidationError) and not str(exc).startswith("HTTP ") else type(exc).__name__
    finally:
        if validation:
            remaining = validation.cleanup()
            print("CLEANUP " + ("FAIL remaining=" + ",".join(remaining) if remaining else "PASS"), flush=True)
    if failure or remaining:
        print("RESULT failed: " + (failure or "cleanup incomplete"), flush=True)
        return 1
    print(f"RESULT ok checks={len(validation.checks)}; TL14=local-only", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
