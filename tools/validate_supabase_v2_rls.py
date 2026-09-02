from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUCKET = "raw-saves"


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    url: str
    anon_key: str
    service_role_key: str
    email_domain: str
    cleanup: bool
    run_id: str


@dataclass
class HttpResult:
    status: int
    data: Any
    text: str
    headers: dict[str, str]

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@dataclass
class CreatedState:
    auth_user_ids: list[str] = field(default_factory=list)
    storage_paths: list[str] = field(default_factory=list)
    table_rows: dict[str, list[str]] = field(default_factory=dict)
    season_player_ids: list[str] = field(default_factory=list)

    def remember(self, table: str, row_id: str | None) -> None:
        if row_id:
            self.table_rows.setdefault(table, []).append(row_id)


class SupabaseHttp:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.url.rstrip("/")
        self.rest_url = f"{self.base_url}/rest/v1"
        self.auth_url = f"{self.base_url}/auth/v1"
        self.storage_url = f"{self.base_url}/storage/v1"

    def _headers(self, *, auth: str, json_body: bool = True) -> dict[str, str]:
        if auth == "service":
            key = self.config.service_role_key
            bearer = self.config.service_role_key
        elif auth == "anon":
            key = self.config.anon_key
            bearer = self.config.anon_key
        else:
            key = self.config.anon_key
            bearer = auth

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {bearer}",
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def request(
        self,
        method: str,
        url: str,
        *,
        auth: str = "anon",
        body: Any = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
        raise_on_error: bool = True,
    ) -> HttpResult:
        request_headers = self._headers(auth=auth, json_body=raw_body is None)
        if headers:
            request_headers.update(headers)

        data: bytes | None = None
        if raw_body is not None:
            data = raw_body
        elif body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                text = response.read().decode("utf-8", errors="replace")
                parsed = _parse_json(text)
                return HttpResult(response.status, parsed, text, dict(response.headers))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            parsed = _parse_json(text)
            result = HttpResult(exc.code, parsed, text, dict(exc.headers))
            if raise_on_error:
                raise ValidationError(f"HTTP {method} {url} failed with {exc.code}: {_compact_error(parsed, text)}")
            return result

    def rest(
        self,
        method: str,
        relation: str,
        *,
        auth: str = "anon",
        params: dict[str, str] | None = None,
        body: Any = None,
        raise_on_error: bool = True,
        prefer: str = "return=representation",
    ) -> HttpResult:
        url = f"{self.rest_url}/{urllib.parse.quote(relation, safe='')}"
        if params:
            url += "?" + urllib.parse.urlencode(params, safe="*,.()")
        return self.request(
            method,
            url,
            auth=auth,
            body=body,
            headers={"Prefer": prefer},
            raise_on_error=raise_on_error,
        )

    def rpc(self, name: str, *, auth: str) -> Any:
        url = f"{self.rest_url}/rpc/{urllib.parse.quote(name, safe='')}"
        result = self.request("POST", url, auth=auth, body={})
        return result.data

    def auth_create_user(self, email: str, password: str) -> str:
        result = self.request(
            "POST",
            f"{self.auth_url}/admin/users",
            auth="service",
            body={"email": email, "password": password, "email_confirm": True},
        )
        user_id = result.data.get("id") if isinstance(result.data, dict) else None
        if not user_id:
            raise ValidationError(f"Auth user create did not return id for {email}")
        return user_id

    def auth_delete_user(self, user_id: str) -> None:
        self.request(
            "DELETE",
            f"{self.auth_url}/admin/users/{urllib.parse.quote(user_id, safe='')}",
            auth="service",
            raise_on_error=False,
        )

    def auth_sign_in(self, email: str, password: str) -> str:
        result = self.request(
            "POST",
            f"{self.auth_url}/token?grant_type=password",
            auth="anon",
            body={"email": email, "password": password},
        )
        token = result.data.get("access_token") if isinstance(result.data, dict) else None
        if not token:
            raise ValidationError(f"Auth sign-in did not return access_token for {email}")
        return token

    def storage_upload(self, bucket: str, path: str, content: bytes, *, auth: str, raise_on_error: bool = True) -> HttpResult:
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        return self.request(
            "POST",
            f"{self.storage_url}/object/{urllib.parse.quote(bucket, safe='')}/{encoded_path}",
            auth=auth,
            raw_body=content,
            headers={"Content-Type": "application/octet-stream", "x-upsert": "false"},
            raise_on_error=raise_on_error,
        )

    def storage_read(self, bucket: str, path: str, *, auth: str, raise_on_error: bool = True) -> HttpResult:
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        return self.request(
            "GET",
            f"{self.storage_url}/object/{urllib.parse.quote(bucket, safe='')}/{encoded_path}",
            auth=auth,
            headers={},
            raise_on_error=raise_on_error,
        )

    def storage_list(self, bucket: str, prefix: str, *, auth: str, raise_on_error: bool = True) -> HttpResult:
        return self.request(
            "POST",
            f"{self.storage_url}/object/list/{urllib.parse.quote(bucket, safe='')}",
            auth=auth,
            body={"prefix": prefix, "limit": 100, "offset": 0},
            raise_on_error=raise_on_error,
        )

    def storage_remove(self, bucket: str, paths: list[str]) -> None:
        if not paths:
            return
        self.request(
            "POST",
            f"{self.storage_url}/object/{urllib.parse.quote(bucket, safe='')}/remove",
            auth="service",
            body={"prefixes": paths},
            raise_on_error=False,
        )


def _parse_json(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _compact_error(parsed: Any, text: str) -> str:
    if isinstance(parsed, dict):
        for key in ("message", "error_description", "error"):
            value = parsed.get(key)
            if value:
                return str(value)
    return text[:300]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"Env file not found: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _config_from_args(args: argparse.Namespace) -> Config:
    if args.env_file:
        _load_env_file(Path(args.env_file))

    missing = [
        name
        for name in (
            "POKEAPP_V2_SUPABASE_URL",
            "POKEAPP_V2_SUPABASE_ANON_KEY",
            "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY",
        )
        if not os.environ.get(name)
    ]
    if missing:
        raise ValidationError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.supabase-v2-rls.example to a local .env file and fill staging values."
        )

    run_id = args.run_id or f"f71-{int(time.time())}-{secrets.token_hex(3)}"
    return Config(
        url=os.environ["POKEAPP_V2_SUPABASE_URL"],
        anon_key=os.environ["POKEAPP_V2_SUPABASE_ANON_KEY"],
        service_role_key=os.environ["POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY"],
        email_domain=os.environ.get("POKEAPP_V2_TEST_EMAIL_DOMAIN", "example.com"),
        cleanup=not args.keep_fixtures,
        run_id=_slugify(run_id),
    )


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")
    return cleaned[:48] or "f71"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _expect_empty(rows: Any, label: str) -> None:
    _assert(isinstance(rows, list), f"{label}: expected list response, got {type(rows).__name__}")
    _assert(len(rows) == 0, f"{label}: expected 0 rows, got {len(rows)}")


def _expect_count(rows: Any, count: int, label: str) -> None:
    _assert(isinstance(rows, list), f"{label}: expected list response, got {type(rows).__name__}")
    _assert(len(rows) == count, f"{label}: expected {count} rows, got {len(rows)}")


def _blocked(result: HttpResult) -> bool:
    return result.status in {400, 401, 403, 404}


def _expect_write_blocked(result: HttpResult, label: str) -> None:
    if _blocked(result):
        return
    if result.ok and isinstance(result.data, list) and not result.data:
        return
    raise ValidationError(f"{label}: write unexpectedly succeeded with HTTP {result.status}")


def _insert_one(api: SupabaseHttp, state: CreatedState, table: str, body: dict[str, Any]) -> dict[str, Any]:
    result = api.rest("POST", table, auth="service", body=body)
    _expect_count(result.data, 1, f"insert {table}")
    row = result.data[0]
    state.remember(table, row.get("id"))
    return row


def _delete_row(api: SupabaseHttp, table: str, row_id: str) -> None:
    api.rest(
        "DELETE",
        table,
        auth="service",
        params={"id": f"eq.{row_id}"},
        raise_on_error=False,
        prefer="return=minimal",
    )


def _cleanup(api: SupabaseHttp, state: CreatedState) -> list[str]:
    warnings: list[str] = []
    api.storage_remove(DEFAULT_BUCKET, state.storage_paths)

    for season_player_id in state.season_player_ids:
        api.rest(
            "DELETE",
            "season_player_stats",
            auth="service",
            params={"season_player_id": f"eq.{season_player_id}"},
            raise_on_error=False,
            prefer="return=minimal",
        )

    delete_order = [
        "penalties",
        "trial_votes",
        "trial_cases",
        "cup_standings",
        "cup_matches",
        "cup_participants",
        "cups",
        "season_archive_snapshots",
        "hall_of_fame_entries",
        "activity_events",
        "team_locks",
        "parsed_saves",
        "save_files",
        "redemptions",
        "purchases",
        "coin_transactions",
        "shop_promotions",
        "matchday_movements",
        "matchday_snapshots",
        "matches",
        "division_memberships",
        "matchdays",
        "divisions",
        "season_config_versions",
        "pokemon_flags",
        "trainer_flags",
        "season_players",
        "seasons",
        "trainers",
    ]
    for table in delete_order:
        for row_id in reversed(state.table_rows.get(table, [])):
            try:
                _delete_row(api, table, row_id)
            except Exception as exc:  # pragma: no cover - best-effort cleanup only.
                warnings.append(f"cleanup {table}/{row_id} failed: {exc}")

    for user_id in state.auth_user_ids:
        api.auth_delete_user(user_id)
    return warnings


def _create_auth_and_fixtures(api: SupabaseHttp, config: Config, state: CreatedState) -> dict[str, Any]:
    password = "PokeApp!" + secrets.token_urlsafe(24)
    auth_users: dict[str, dict[str, str]] = {}
    for role in ("a", "b", "admin", "orphan"):
        email = f"pokeapp-v2-{config.run_id}-{role}@{config.email_domain}"
        user_id = api.auth_create_user(email, password)
        state.auth_user_ids.append(user_id)
        token = api.auth_sign_in(email, password)
        auth_users[role] = {"email": email, "id": user_id, "token": token}

    trainers: dict[str, dict[str, Any]] = {}
    for role, display_name, is_admin in (
        ("a", "Validation Trainer A", False),
        ("b", "Validation Trainer B", False),
        ("admin", "Validation Admin", True),
    ):
        row = _insert_one(
            api,
            state,
            "trainers",
            {
                "display_name": f"{display_name} {config.run_id}",
                "slug": f"{config.run_id}-{role}",
                "auth_user_id": auth_users[role]["id"],
                "is_admin": is_admin,
                "metadata": {"validation_run": config.run_id, "private_marker": f"secret-{role}"},
            },
        )
        trainers[role] = row

    season = _insert_one(
        api,
        state,
        "seasons",
        {
            "name": f"RLS Validation {config.run_id}",
            "status": "draft",
            "created_by_trainer_id": trainers["admin"]["id"],
            "metadata": {"validation_run": config.run_id},
        },
    )
    season_id = season["id"]

    season_players: dict[str, dict[str, Any]] = {}
    for index, role in enumerate(("a", "b"), start=1):
        row = _insert_one(
            api,
            state,
            "season_players",
            {
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "seed_order": index,
                "metadata": {"validation_run": config.run_id},
            },
        )
        season_players[role] = row
        state.season_player_ids.append(row["id"])
        api.rest(
            "POST",
            "season_player_stats",
            auth="service",
            body={
                "season_player_id": row["id"],
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "badges_count": index,
                "metadata": {"validation_run": config.run_id},
            },
        )

    config_row = _insert_one(
        api,
        state,
        "season_config_versions",
        {
            "season_id": season_id,
            "version_number": 1,
            "name": "RLS validation config",
            "effective_from_matchday": 1,
            "total_matchdays": 4,
            "division_count": 2,
            "promotion_relegation_count": 1,
            "scoring_json": {"1": 9, "2": 8},
            "coin_rewards_json": {"1": 15, "2": 14},
            "rules_json": {"validation_run": config.run_id},
            "created_by_trainer_id": trainers["admin"]["id"],
        },
    )

    division_a = _insert_one(api, state, "divisions", {"season_id": season_id, "code": "A", "name": "Liga A", "tier_order": 1})
    division_b = _insert_one(api, state, "divisions", {"season_id": season_id, "code": "B", "name": "Liga B", "tier_order": 2})
    matchday = _insert_one(
        api,
        state,
        "matchdays",
        {"season_id": season_id, "number": 1, "status": "open", "season_config_version_id": config_row["id"]},
    )

    for role, division in (("a", division_a), ("b", division_b)):
        _insert_one(
            api,
            state,
            "division_memberships",
            {
                "season_id": season_id,
                "season_player_id": season_players[role]["id"],
                "division_id": division["id"],
                "effective_from_matchday_number": 1,
                "reason": "initial",
            },
        )

    match = _insert_one(
        api,
        state,
        "matches",
        {
            "season_id": season_id,
            "matchday_id": matchday["id"],
            "division_id": division_a["id"],
            "player_a_id": season_players["a"]["id"],
            "player_b_id": season_players["b"]["id"],
            "winner_id": season_players["a"]["id"],
            "status": "completed",
        },
    )
    snapshot = _insert_one(
        api,
        state,
        "matchday_snapshots",
        {
            "season_id": season_id,
            "matchday_id": matchday["id"],
            "config_version_id": config_row["id"],
            "closed_at": "2026-01-01T00:00:00Z",
            "snapshot": {"validation_run": config.run_id, "standings": [{"trainer": "A"}]},
            "created_by_trainer_id": trainers["admin"]["id"],
        },
    )
    movement = _insert_one(
        api,
        state,
        "matchday_movements",
        {
            "season_id": season_id,
            "matchday_id": matchday["id"],
            "season_player_id": season_players["b"]["id"],
            "from_division_id": division_b["id"],
            "to_division_id": division_a["id"],
            "movement_type": "promotion",
            "reason": "validation",
        },
    )

    item = api.rest(
        "GET",
        "shop_items",
        auth="service",
        params={"select": "id,base_price,name", "code": "eq.revivir_pokemon"},
    ).data
    _expect_count(item, 1, "seeded shop item revivir_pokemon")
    shop_item = item[0]
    promotion = _insert_one(
        api,
        state,
        "shop_promotions",
        {
            "season_id": season_id,
            "matchday_id": matchday["id"],
            "shop_item_id": shop_item["id"],
            "promotion_type": "normal",
            "status": "active",
            "base_price": shop_item["base_price"],
            "effective_price": max(0, shop_item["base_price"] - 1),
            "stock_total": 2,
            "stock_used": 0,
            "announced_at": "2026-01-01T00:00:00Z",
            "activates_at": "2026-01-01T00:00:00Z",
            "dedupe_key": f"{config.run_id}:promo",
        },
    )

    purchases: dict[str, dict[str, Any]] = {}
    redemptions: dict[str, dict[str, Any]] = {}
    saves: dict[str, dict[str, Any]] = {}
    parsed: dict[str, dict[str, Any]] = {}
    locks: dict[str, dict[str, Any]] = {}

    for index, role in enumerate(("a", "b"), start=1):
        purchase = _insert_one(
            api,
            state,
            "purchases",
            {
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "season_player_id": season_players[role]["id"],
                "shop_item_id": shop_item["id"],
                "promotion_id": promotion["id"],
                "quantity": 1,
                "unit_price": shop_item["base_price"],
                "metadata": {"validation_run": config.run_id, "owner": role},
            },
        )
        purchases[role] = purchase
        redemptions[role] = _insert_one(
            api,
            state,
            "redemptions",
            {
                "purchase_id": purchase["id"],
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "season_player_id": season_players[role]["id"],
                "shop_item_id": shop_item["id"],
                "payload": {"validation_run": config.run_id, "owner": role},
            },
        )
        _insert_one(
            api,
            state,
            "coin_transactions",
            {
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "season_player_id": season_players[role]["id"],
                "amount": 10 + index,
                "transaction_type": "matchday_reward",
                "reference_type": "validation",
                "metadata": {"validation_run": config.run_id, "owner": role},
            },
        )
        sha = (str(index) * 64)[:64]
        storage_key = f"{trainers[role]['id']}/{season_id}/{config.run_id}-{role}.sav"
        saves[role] = _insert_one(
            api,
            state,
            "save_files",
            {
                "season_id": season_id,
                "trainer_id": trainers[role]["id"],
                "storage_key": storage_key,
                "original_filename": f"{config.run_id}-{role}.sav",
                "sha256": sha,
                "parser_status": "parsed",
                "parser_version": "rls-validator",
                "metadata": {"validation_run": config.run_id, "owner": role},
            },
        )
        parsed[role] = _insert_one(
            api,
            state,
            "parsed_saves",
            {
                "save_file_id": saves[role]["id"],
                "parser_version": "rls-validator",
                "payload": {
                    "validation_run": config.run_id,
                    "owner": role,
                    "secret_marker": f"parsed-secret-{role}",
                },
            },
        )
        locks[role] = _insert_one(
            api,
            state,
            "team_locks",
            {
                "season_id": season_id,
                "matchday_id": matchday["id"],
                "trainer_id": trainers[role]["id"],
                "season_player_id": season_players[role]["id"],
                "save_file_id": saves[role]["id"],
                "save_sha256": sha,
                "public_team_snapshot": {
                    "validation_run": config.run_id,
                    "owner": role,
                    "public_marker": f"public-team-{role}",
                },
                "private_team_snapshot": {
                    "validation_run": config.run_id,
                    "owner": role,
                    "private_marker": f"private-team-{role}",
                },
                "metadata": {"validation_run": config.run_id, "owner": role},
            },
        )

    activity: dict[str, dict[str, Any]] = {}
    for visibility, owner_role in (("public", "a"), ("owner", "a"), ("owner", "b"), ("admin", "admin")):
        key = f"{visibility}-{owner_role}"
        activity[key] = _insert_one(
            api,
            state,
            "activity_events",
            {
                "season_id": season_id,
                "type": "SAVE_UPLOADED",
                "actor_trainer_id": trainers[owner_role]["id"],
                "trainer_id": trainers[owner_role]["id"],
                "visibility": visibility,
                "dedupe_key": f"{config.run_id}:activity:{key}",
                "context": {"validation_run": config.run_id, "visibility": visibility},
                "payload": {"private_marker": f"activity-{key}"},
            },
        )

    archive = _insert_one(
        api,
        state,
        "season_archive_snapshots",
        {"season_id": season_id, "snapshot": {"validation_run": config.run_id}, "created_by_trainer_id": trainers["admin"]["id"]},
    )
    hall = _insert_one(
        api,
        state,
        "hall_of_fame_entries",
        {
            "season_id": season_id,
            "competition_type": "league",
            "champion_trainer_id": trainers["a"]["id"],
            "finalist_trainer_id": trainers["b"]["id"],
            "team_snapshot": {"validation_run": config.run_id, "champion": "a"},
        },
    )

    return {
        "auth_users": auth_users,
        "trainers": trainers,
        "season": season,
        "season_players": season_players,
        "config": config_row,
        "division_a": division_a,
        "division_b": division_b,
        "matchday": matchday,
        "match": match,
        "snapshot": snapshot,
        "movement": movement,
        "shop_item": shop_item,
        "promotion": promotion,
        "purchases": purchases,
        "redemptions": redemptions,
        "saves": saves,
        "parsed": parsed,
        "locks": locks,
        "activity": activity,
        "archive": archive,
        "hall": hall,
    }


def _run_checks(api: SupabaseHttp, config: Config, fixtures: dict[str, Any], state: CreatedState) -> list[str]:
    passed: list[str] = []
    token_a = fixtures["auth_users"]["a"]["token"]
    token_b = fixtures["auth_users"]["b"]["token"]
    token_admin = fixtures["auth_users"]["admin"]["token"]
    token_orphan = fixtures["auth_users"]["orphan"]["token"]

    trainer_a = fixtures["trainers"]["a"]
    trainer_b = fixtures["trainers"]["b"]
    trainer_admin = fixtures["trainers"]["admin"]
    season_id = fixtures["season"]["id"]
    match_id = fixtures["match"]["id"]
    matchday_id = fixtures["matchday"]["id"]
    promotion_id = fixtures["promotion"]["id"]

    def mark(label: str) -> None:
        print(f"PASS {label}")
        passed.append(label)

    # Auth helpers with real JWTs.
    _assert(api.rpc("current_auth_uid", auth=token_a) == fixtures["auth_users"]["a"]["id"], "auth.uid mismatch for Trainer A")
    _assert(api.rpc("current_trainer_id", auth=token_a) == trainer_a["id"], "current_trainer_id mismatch for Trainer A")
    _assert(api.rpc("is_current_user_admin", auth=token_a) is False, "Trainer A unexpectedly admin")
    _assert(api.rpc("current_trainer_id", auth=token_b) == trainer_b["id"], "current_trainer_id mismatch for Trainer B")
    _assert(api.rpc("is_current_user_admin", auth=token_admin) is True, "Admin helper did not return true")
    _assert(api.rpc("current_trainer_id", auth=token_orphan) is None, "Orphan auth user unexpectedly mapped to trainer")
    mark("auth.uid and trainer/admin mapping")

    # Anonymous.
    anon_trainers = api.rest("GET", "public_trainers", auth="anon", params={"select": "*"}, raise_on_error=False)
    _assert(_blocked(anon_trainers), "anon unexpectedly read public_trainers")
    mark("anon app access blocked")

    # Public trainer projection.
    public_trainers = api.rest(
        "GET",
        "public_trainers",
        auth=token_a,
        params={"select": "*", "slug": f"eq.{trainer_b['slug']}"},
    ).data
    _expect_count(public_trainers, 1, "Trainer A public view of Trainer B")
    _assert("auth_user_id" not in public_trainers[0], "public_trainers exposed auth_user_id")
    _assert("metadata" not in public_trainers[0], "public_trainers exposed metadata")
    _assert("is_admin" not in public_trainers[0], "public_trainers exposed is_admin")
    public_trainers_bad_column = api.rest(
        "GET",
        "public_trainers",
        auth=token_a,
        params={"select": "auth_user_id"},
        raise_on_error=False,
    )
    _assert(_blocked(public_trainers_bad_column), "public_trainers allowed auth_user_id selection")
    mark("public_trainers hides auth identity and private metadata")

    # Owner reads and private isolation.
    a_saves = api.rest("GET", "save_files", auth=token_a, params={"select": "id,trainer_id,storage_key"}).data
    _expect_count(a_saves, 1, "Trainer A save_files")
    _assert(a_saves[0]["trainer_id"] == trainer_a["id"], "Trainer A saw wrong save owner")
    b_save_from_a = api.rest(
        "GET",
        "save_files",
        auth=token_a,
        params={"select": "*", "id": f"eq.{fixtures['saves']['b']['id']}"},
    ).data
    _expect_empty(b_save_from_a, "Trainer A cannot read B save metadata")

    a_parsed = api.rest("GET", "parsed_saves", auth=token_a, params={"select": "id,payload"}).data
    _expect_count(a_parsed, 1, "Trainer A parsed_saves")
    _assert(a_parsed[0]["payload"]["secret_marker"] == "parsed-secret-a", "Trainer A parsed payload mismatch")
    b_parsed_known = api.rest(
        "GET",
        "parsed_saves",
        auth=token_a,
        params={"select": "*", "id": f"eq.{fixtures['parsed']['b']['id']}"},
    ).data
    _expect_empty(b_parsed_known, "Trainer A cannot read B parsed save by known UUID")
    b_parsed_unfiltered = api.rest("GET", "current_parsed_saves", auth=token_a, params={"select": "*"}).data
    _expect_count(b_parsed_unfiltered, 1, "Trainer A current_parsed_saves")
    mark("ParsedSave owner isolation")

    # TeamLock public/private.
    public_locks = api.rest(
        "GET",
        "public_team_locks",
        auth=token_a,
        params={"select": "*", "season_id": f"eq.{season_id}"},
    ).data
    _expect_count(public_locks, 2, "Trainer A public team locks")
    _assert(all("private_team_snapshot" not in row for row in public_locks), "public_team_locks exposed private snapshot")
    _assert(any(row["public_team_snapshot"]["public_marker"] == "public-team-b" for row in public_locks), "Trainer A did not see B public snapshot")
    private_locks_a = api.rest("GET", "current_team_locks", auth=token_a, params={"select": "*"}).data
    _expect_count(private_locks_a, 1, "Trainer A private team locks")
    _assert(private_locks_a[0]["private_team_snapshot"]["private_marker"] == "private-team-a", "Trainer A private TeamLock mismatch")
    b_lock_known = api.rest(
        "GET",
        "team_locks",
        auth=token_a,
        params={"select": "*", "id": f"eq.{fixtures['locks']['b']['id']}"},
    ).data
    _expect_empty(b_lock_known, "Trainer A cannot read B private TeamLock via base table")
    mark("TeamLock public/private split")

    # Economy.
    for table, source in (("purchases", "purchases"), ("redemptions", "redemptions"), ("coin_transactions", None)):
        rows_a = api.rest("GET", table, auth=token_a, params={"select": "*"}).data
        _expect_count(rows_a, 1, f"Trainer A {table}")
        if source:
            b_id = fixtures[source]["b"]["id"]
            rows_b = api.rest("GET", table, auth=token_a, params={"select": "*", "id": f"eq.{b_id}"}).data
        else:
            rows_b = api.rest("GET", table, auth=token_a, params={"select": "*", "trainer_id": f"eq.{trainer_b['id']}"}).data
        _expect_empty(rows_b, f"Trainer A cannot read B {table}")
    balances = api.rest("GET", "public_coin_balances", auth=token_a, params={"select": "*", "season_id": f"eq.{season_id}"}).data
    _expect_count(balances, 2, "public coin balances")
    _assert(all(set(row) <= {"season_id", "trainer_id", "balance"} for row in balances), "public_coin_balances exposed extra columns")
    mark("economy owner isolation and public aggregate")

    # Activity visibility.
    current_activity_a = api.rest("GET", "current_activity_events", auth=token_a, params={"select": "visibility,trainer_id"}).data
    markers_a = {(row["visibility"], row["trainer_id"]) for row in current_activity_a}
    _assert(("public", trainer_a["id"]) in markers_a, "Trainer A missing public activity")
    _assert(("owner", trainer_a["id"]) in markers_a, "Trainer A missing own owner activity")
    _assert(("owner", trainer_b["id"]) not in markers_a, "Trainer A saw B owner activity")
    _assert(("admin", trainer_admin["id"]) not in markers_a, "Trainer A saw admin activity")
    current_activity_b = api.rest("GET", "current_activity_events", auth=token_b, params={"select": "visibility,trainer_id"}).data
    markers_b = {(row["visibility"], row["trainer_id"]) for row in current_activity_b}
    _assert(("owner", trainer_b["id"]) in markers_b, "Trainer B missing own owner activity")
    _assert(("owner", trainer_a["id"]) not in markers_b, "Trainer B saw A owner activity")
    admin_activity = api.rest("GET", "current_activity_events", auth=token_admin, params={"select": "*"}).data
    _assert(len(admin_activity) >= 4, "Admin did not see all activity events")
    mark("activity event visibility")

    # League reads and direct writes blocked for trainers.
    league_views = {
        "public_seasons": {"id": f"eq.{season_id}"},
        "public_divisions": {"season_id": f"eq.{season_id}"},
        "public_division_memberships": {"season_id": f"eq.{season_id}"},
        "public_matchdays": {"season_id": f"eq.{season_id}"},
        "public_matches": {"season_id": f"eq.{season_id}"},
        "public_matchday_snapshots": {"season_id": f"eq.{season_id}"},
        "public_matchday_movements": {"season_id": f"eq.{season_id}"},
    }
    for view, filter_params in league_views.items():
        params = {"select": "*", **filter_params}
        rows = api.rest("GET", view, auth=token_a, params=params).data
        _assert(isinstance(rows, list) and rows, f"Trainer A could not read {view}")
    _expect_write_blocked(
        api.rest("PATCH", "matches", auth=token_a, params={"id": f"eq.{match_id}"}, body={"status": "void"}, raise_on_error=False),
        "Trainer A update match",
    )
    _expect_write_blocked(
        api.rest("PATCH", "matchdays", auth=token_a, params={"id": f"eq.{matchday_id}"}, body={"status": "closed"}, raise_on_error=False),
        "Trainer A update matchday",
    )
    _expect_write_blocked(
        api.rest("POST", "matchday_snapshots", auth=token_a, body={
            "season_id": season_id,
            "matchday_id": matchday_id,
            "config_version_id": fixtures["config"]["id"],
            "closed_at": "2026-01-02T00:00:00Z",
            "snapshot": {"hack": True},
        }, raise_on_error=False),
        "Trainer A insert snapshot",
    )
    mark("league read allowed and trainer direct mutations blocked")

    # Shop reads and direct writes blocked.
    _assert(api.rest("GET", "public_shop_items", auth=token_a, params={"select": "*"}).data, "Trainer A could not read shop catalog")
    _assert(api.rest("GET", "public_shop_promotions", auth=token_a, params={"select": "*", "id": f"eq.{promotion_id}"}).data, "Trainer A could not read visible promo")
    _expect_write_blocked(
        api.rest("POST", "purchases", auth=token_a, body={
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "shop_item_id": fixtures["shop_item"]["id"],
            "quantity": 1,
            "unit_price": 1,
        }, raise_on_error=False),
        "Trainer A insert purchase",
    )
    _expect_write_blocked(
        api.rest("POST", "redemptions", auth=token_a, body={
            "purchase_id": fixtures["purchases"]["a"]["id"],
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "shop_item_id": fixtures["shop_item"]["id"],
        }, raise_on_error=False),
        "Trainer A insert redemption",
    )
    _expect_write_blocked(
        api.rest("POST", "coin_transactions", auth=token_a, body={
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "amount": 1,
            "transaction_type": "admin_adjustment",
        }, raise_on_error=False),
        "Trainer A insert coin transaction",
    )
    _expect_write_blocked(
        api.rest("PATCH", "shop_promotions", auth=token_a, params={"id": f"eq.{promotion_id}"}, body={"stock_used": 1}, raise_on_error=False),
        "Trainer A update stock",
    )
    mark("shop visible reads and direct critical writes blocked")

    # Admin behavior. Admin can read private rows but is still not service_role for API-only ledger/purchases.
    _expect_count(api.rest("GET", "parsed_saves", auth=token_admin, params={"select": "*"}).data, 2, "Admin parsed saves")
    admin_season_update = api.rest(
        "PATCH",
        "seasons",
        auth=token_admin,
        params={"id": f"eq.{season_id}"},
        body={"name": fixtures["season"]["name"]},
        raise_on_error=False,
    )
    _assert(admin_season_update.ok, "Admin could not update admin-managed season state")
    _expect_write_blocked(
        api.rest("POST", "coin_transactions", auth=token_admin, body={
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "amount": 1,
            "transaction_type": "admin_adjustment",
        }, raise_on_error=False),
        "Admin insert coin transaction direct",
    )
    _expect_write_blocked(
        api.rest("POST", "purchases", auth=token_admin, body={
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "shop_item_id": fixtures["shop_item"]["id"],
            "quantity": 1,
            "unit_price": 1,
        }, raise_on_error=False),
        "Admin insert purchase direct",
    )
    mark("admin access and API-only economy writes")

    # Service role.
    _expect_count(api.rest("GET", "parsed_saves", auth="service", params={"select": "*"}).data, 2, "service parsed saves")
    service_insert = _insert_one(
        api,
        state,
        "coin_transactions",
        {
            "season_id": season_id,
            "trainer_id": trainer_a["id"],
            "season_player_id": fixtures["season_players"]["a"]["id"],
            "amount": 1,
            "transaction_type": "admin_adjustment",
            "reference_type": "service_validation",
            "metadata": {"validation_run": config.run_id, "service_role": True},
        },
    )
    _assert(service_insert["id"], "service_role failed to insert backend ledger row")
    mark("service_role backend access")

    # Storage.
    bucket = api.request("GET", f"{api.storage_url}/bucket/{DEFAULT_BUCKET}", auth="service")
    _assert(isinstance(bucket.data, dict), "raw-saves bucket response was not an object")
    _assert(bucket.data.get("public") is False, "raw-saves bucket is not private")
    path_a = f"{trainer_a['id']}/{season_id}/{config.run_id}-a-upload.sav"
    path_b = f"{trainer_b['id']}/{season_id}/{config.run_id}-b-upload.sav"
    state.storage_paths.extend([path_a, path_b])
    content_a = f"pokeapp validation A {config.run_id}".encode("utf-8")
    content_b = f"pokeapp validation B {config.run_id}".encode("utf-8")
    upload_a = api.storage_upload(DEFAULT_BUCKET, path_a, content_a, auth=token_a)
    _assert(upload_a.ok, "Trainer A own storage upload failed")
    upload_a_to_b = api.storage_upload(DEFAULT_BUCKET, path_b, b"bad", auth=token_a, raise_on_error=False)
    _assert(_blocked(upload_a_to_b), "Trainer A uploaded into Trainer B namespace")
    upload_b_service = api.storage_upload(DEFAULT_BUCKET, path_b, content_b, auth="service")
    _assert(upload_b_service.ok, "service_role upload to Trainer B namespace failed")
    read_own = api.storage_read(DEFAULT_BUCKET, path_a, auth=token_a)
    _assert(read_own.text.encode("utf-8") == content_a or read_own.text == content_a.decode("utf-8"), "Trainer A own storage read mismatch")
    read_b_from_a = api.storage_read(DEFAULT_BUCKET, path_b, auth=token_a, raise_on_error=False)
    _assert(_blocked(read_b_from_a), "Trainer A read Trainer B raw save")
    list_b_from_a = api.storage_list(DEFAULT_BUCKET, trainer_b["id"], auth=token_a, raise_on_error=False)
    _assert(_blocked(list_b_from_a) or list_b_from_a.data == [], "Trainer A listed Trainer B raw-saves namespace")
    read_a_anon = api.storage_read(DEFAULT_BUCKET, path_a, auth="anon", raise_on_error=False)
    _assert(_blocked(read_a_anon), "anon read raw save")
    read_b_service = api.storage_read(DEFAULT_BUCKET, path_b, auth="service")
    _assert(read_b_service.ok, "service_role could not read raw save")
    mark("raw-saves private bucket and storage policies")

    # Column exposure.
    sensitive_checks = [
        ("public_team_locks", "private_team_snapshot"),
        ("public_trainers", "auth_user_id"),
        ("public_trainers", "metadata"),
    ]
    for view, column in sensitive_checks:
        result = api.rest("GET", view, auth=token_a, params={"select": column}, raise_on_error=False)
        _assert(_blocked(result), f"{view} exposed sensitive column {column}")
    _expect_empty(api.rest("GET", "app_settings", auth=token_a, params={"select": "*"}).data, "Trainer A app_settings")
    _expect_empty(
        api.rest("GET", "season_archive_snapshots", auth=token_a, params={"select": "*", "id": f"eq.{fixtures['archive']['id']}"}).data,
        "Trainer A archive audit",
    )
    mark("sensitive column exposure")

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Supabase V2 RLS/Auth/Storage against a real clean Supabase staging project."
    )
    parser.add_argument("--env-file", help="Optional local env file with PokeApp V2 Supabase staging credentials.")
    parser.add_argument("--run-id", help="Optional validation run id. Defaults to a unique value.")
    parser.add_argument("--keep-fixtures", action="store_true", help="Do not clean up validation rows/Auth users/storage objects.")
    args = parser.parse_args()

    try:
        config = _config_from_args(args)
        api = SupabaseHttp(config)
        state = CreatedState()

        print("PokeApp Supabase V2 real RLS validation")
        print(f"staging_url={config.url}")
        print(f"run_id={config.run_id}")
        print("secrets=redacted")

        try:
            fixtures = _create_auth_and_fixtures(api, config, state)
            passed = _run_checks(api, config, fixtures, state)
        finally:
            if config.cleanup:
                warnings = _cleanup(api, state)
                for warning in warnings:
                    print(f"WARN {warning}")

        print(f"RESULT ok checks={len(passed)}")
        return 0
    except ValidationError as exc:
        print(f"RESULT failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
