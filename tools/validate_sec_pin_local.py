"""SEC-PIN-01: disposable loopback PostgreSQL with in-memory synthetic Auth."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import threading
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.accounts import AccountError
from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import (
    AuthBackendError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.auth.keyring import CredentialKeyring, CredentialRenewalRequired
from app.auth.models import TrainerAuthIdentity, SupabaseAuthSession, SupabaseAuthUser
from app.auth.service import PinAuthBridge
from app.auth.versioned_accounts import VersionedAccountService
from app.repositories.supabase.accounts import SupabaseAccountRepository
from tools.validate_accounts_local import LocalPG, p4, reset_gate


def literal(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


class Repository:
    profile_update = SupabaseAccountRepository.profile_update

    def __init__(self, pg):
        self.pg = pg
        self.fail_before = None
        self.fail_after = None
        self.photos = {}

    def upload_photo(self, key, data):
        if key in self.photos:
            assert self.photos[key] == data
        self.photos[key] = data

    def photo_urls(self, keys):
        return {
            k: "https://synthetic.invalid/portrait" for k in keys if k in self.photos
        }

    def trainers(self, offset):
        return json.loads(
            self.pg.sql(
                f"select coalesce(jsonb_agg(t),'[]') from (select * from trainers where globally_enabled order by slug,id limit 50 offset {int(offset)}) t;"
            ).stdout
        )

    def rpc(self, name, params):
        if name == self.fail_before:
            self.fail_before = None
            raise AuthBackendError("Synthetic failure before RPC")
        query = (
            f"select to_jsonb(public.{name}("
            + ",".join(f"{k}=>{literal(v)}" for k, v in params.items())
            + "));"
        )
        result = self.pg.sql("set role service_role;" + query, ok=False)
        if result.returncode:
            for code in (
                "account_conflict",
                "account_renewal_required",
                "account_reconciliation_required",
                "account_forbidden",
            ):
                if code in result.stderr:
                    raise AccountError(code.upper())
            raise AuthBackendError(result.stderr)
        value = json.loads(result.stdout.strip() or "null")
        if name == self.fail_after:
            self.fail_after = None
            raise AuthBackendError("Synthetic lost RPC response")
        return value

    def row(self, table, column, key):
        value = self.pg.sql(
            f"select to_jsonb(t) from public.{table} t where {column}={literal(key)};"
        ).stdout.strip()
        return json.loads(value) if value else None

    def trainer(self, key):
        return self.row("trainers", "id", key)

    def credential_intent(self, kind, key):
        return self.row(
            *{
                "pin": ("account_pin_changes", "operation_id"),
                "grant": ("account_renewal_grants", "token_hash"),
            }[kind],
            key,
        )

    def find_for_login(self, key):
        row = self.row("trainers", "slug", key)
        return self._identity(row)

    def find_by_auth_user_id(self, key):
        return self._identity(self.row("trainers", "auth_user_id", key))

    def _identity(self, row):
        return (
            TrainerAuthIdentity(
                **{
                    k: row[k]
                    for k in (
                        "id",
                        "display_name",
                        "slug",
                        "auth_user_id",
                        "globally_enabled",
                        "is_admin",
                    )
                }
            )
            if row
            else None
        )


class Auth:
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.password_calls = 0
        self.creations = 0
        self.fail_create_after = False
        self.fail_password = None
        self.fail_revoke = False
        self.lock = threading.Lock()

    def lookup(self, uid):
        return self.users.get(uid)

    def create(self, uid, email, password, marker):
        with self.lock:
            if uid in self.users:
                raise AuthBackendError("Synthetic existing identity")
            self.users[uid] = dict(
                id=uid,
                email=email,
                password=password,
                marker=marker,
                role="authenticated",
            )
            self.creations += 1
        if self.fail_create_after:
            self.fail_create_after = False
            raise AuthBackendError("Synthetic response lost")

    def verify(self, email, password):
        with self.lock:
            row = next(
                (
                    u
                    for u in self.users.values()
                    if u["email"] == email and u["password"] == password
                ),
                None,
            )
            if row is None:
                raise InvalidCredentialsError()
            payload = (
                base64.urlsafe_b64encode(
                    json.dumps(
                        {"iat": int(datetime.now(timezone.utc).timestamp()) + 2}
                    ).encode()
                )
                .decode()
                .rstrip("=")
            )
            token = f"synthetic.{payload}.{uuid4()}"
            self.sessions[token] = row["id"]
            return SupabaseAuthSession(
                user_id=row["id"], access_token=token, refresh_token=token
            )

    def sign_in_with_password(self, *, email, password):
        return self.verify(email, password)

    def password(self, uid, password):
        with self.lock:
            self.password_calls += 1
            if self.fail_password == "before":
                self.fail_password = None
                raise AuthBackendError("Synthetic refusal before update")
            self.users[uid]["password"] = password
            if self.fail_password == "after":
                self.fail_password = None
                raise AuthBackendError("Synthetic response lost after update")

    def revoke(self, token):
        if self.fail_revoke:
            self.fail_revoke = False
            raise AuthBackendError("Synthetic revoke failure")
        uid = self.sessions[token]
        self.sessions = {k: v for k, v in self.sessions.items() if v != uid}

    def get_user(self, *, access_token):
        if access_token not in self.sessions:
            raise InvalidSessionError()
        return SupabaseAuthUser(user_id=self.sessions[access_token])

    def refresh_session(self, *, refresh_token):
        self.get_user(access_token=refresh_token)
        uid = self.sessions[refresh_token]
        row = self.users[uid]
        return self.verify(row["email"], row["password"])


def expect_error(
    action, types=(AccountError, AuthBackendError, InvalidCredentialsError)
):
    try:
        action()
    except types:
        return
    raise AssertionError("Expected fail-closed result")


def http_journey(pg, repo, auth, service, bridge):
    """Real API + journal/profile SQL; Auth and object transport are substitutes."""
    from PIL import Image

    def new_key(token=None):
        return {
            "Idempotency-Key": str(uuid4()),
            **({"Authorization": "Bearer " + token} if token else {}),
        }

    container = ApiContainer(
        auth_bridge=bridge,
        token_verifier=auth,
        session_refresher=auth,
        principal_repository=repo,
        trainer_repository=repo,
        account_service=service,
    )
    with TestClient(create_app(config=APIConfig(), container=container)) as client:
        assert client.get("/v1/auth/account-capabilities").json()[
            "registration_enabled"
        ]
        body = dict(
            trainer_name="HTTP New",
            pin="0042",
            confirmation="0042",
            access_code="wrong",
        )
        headers = new_key()
        assert (
            client.post("/v1/auth/register", headers=headers, json=body).status_code
            == 400
        )
        body["access_code"] = "synthetic-invitation"
        response = client.post("/v1/auth/register", headers=headers, json=body)
        assert response.status_code == 200
        tid = response.json()["trainer_id"]
        assert (
            client.post("/v1/auth/register", headers=headers, json=body).json()
            == response.json()
        )
        aid = repo.trainer(tid)["auth_user_id"]
        assert (
            pg.sql(
                f"select count(*) from season_players where trainer_id='{tid}';"
            ).stdout.strip()
            == "0"
        )

        def login(name, pin):
            r = client.post(
                "/v1/auth/pin-login", json={"trainer_identifier": name, "pin": pin}
            )
            assert r.status_code == 200
            return r.json()["session"]["access_token"]

        token = login("http-new", "0042")
        own = client.get(f"/v1/accounts/{tid}", headers=new_key(token)).json()
        assert own["revision"] == 0 and set(own) == {
            "trainer_id",
            "display_name",
            "photo_url",
            "revision",
        }
        assert (
            client.put(
                "/v1/account/name",
                headers=new_key(token),
                json={"display_name": "HTTP Renamed", "expected_revision": 0},
            ).status_code
            == 200
        )
        image = io.BytesIO()
        Image.new("RGB", (8, 8)).save(image, format="PNG")
        assert (
            client.put(
                "/v1/account/photo?expected_revision=1",
                headers={**new_key(token), "Content-Type": "image/png"},
                content=image.getvalue(),
            ).status_code
            == 200
        )
        assert client.get(f"/v1/accounts/{tid}", headers=new_key(token)).json()[
            "photo_url"
        ]
        # No alternate subject or economic fields accepted by the editing API.
        assert (
            client.put(
                "/v1/account/name",
                headers=new_key(token),
                json={
                    "display_name": "Forbidden",
                    "expected_revision": 2,
                    "trainer_id": str(uuid4()),
                    "coins": 999,
                },
            ).status_code
            == 422
        )
        assert (
            client.get("/v1/admin/accounts", headers=new_key(token)).status_code == 403
        )
        assert (
            client.post(
                "/v1/account/pin",
                headers=new_key(token),
                json={"current_pin": "0042", "new_pin": "0053", "confirmation": "0053"},
            ).status_code
            == 200
        )
        assert client.get("/v1/me", headers=new_key(token)).status_code == 401
        assert (
            client.post("/v1/auth/refresh", json={"refresh_token": token}).status_code
            == 401
        )
        token = login("http-renamed", "0053")
        assert (
            repo.trainer(tid)["auth_user_id"] == aid
            and not repo.trainer(tid)["is_admin"]
        )
        # Independent synthetic admin; no replacement identity or role editor.
        admin = service.register(
            uuid4(), "HTTP Admin", "0017", "0017", "synthetic-invitation"
        )["trainer_id"]
        pg.sql(f"update trainers set is_admin=true where id='{admin}';")
        admin_token = login("http-admin", "0017")
        listed = client.get("/v1/admin/accounts", headers=new_key(admin_token))
        assert listed.status_code == 200 and any(
            r["trainer_id"] == tid for r in listed.json()["items"]
        )
        reset_path = f"/v1/admin/accounts/{tid}/reset-pin"
        assert (
            client.post(
                reset_path,
                headers=new_key(admin_token),
                json={"new_pin": "0064", "confirmation": "0064"},
            ).status_code
            == 403
        )
        grant = uuid4().hex + uuid4().hex
        repo.rpc(
            "sec_pin_authorize_renewal",
            dict(
                p_hash=hashlib.sha256(grant.encode()).hexdigest(),
                p_target=tid,
                p_auth=aid,
                p_reference="synthetic independent verification",
                p_expires=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            ),
        )
        assert (
            client.post(
                reset_path,
                headers=new_key(admin_token),
                json={
                    "new_pin": "0064",
                    "confirmation": "0064",
                    "renewal_token": grant,
                },
            ).status_code
            == 200
        )
        login("http-renamed", "0064")
        assert (
            client.put(
                f"/v1/admin/accounts/{tid}/status",
                headers=new_key(admin_token),
                json={"expected_revision": 2, "enabled": False},
            ).status_code
            == 200
        )
        assert client.get("/v1/me", headers=new_key(token)).status_code in (401, 403)
        assert repo.trainer(tid)["auth_user_id"] == aid
    return True


def gates(pg):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=3)
    pg.sql(
        f"insert into account_credential_policy(legacy_deadline) values({literal(cutoff.isoformat())});"
    )
    ring = CredentialKeyring(
        cutoff,
        "synthetic-password-v2-secret-00001",
        "synthetic-journal-key-secret-00002",
        "synthetic-throttle-key-secret-0003",
        "synthetic-old-pepper",
    )
    repo = Repository(pg)
    auth = Auth()
    service = VersionedAccountService(
        repo, auth, keyring=ring, enabled=True, access_code="synthetic-invitation"
    )
    bridge = PinAuthBridge(
        trainers=repo, auth=auth, pepper="", credential_provider=service.credential
    )

    def register(name=None, op=None):
        return service.register(
            op or uuid4(),
            name or "User " + uuid4().hex[:12],
            "0017",
            "0017",
            "synthetic-invitation",
        )["trainer_id"]

    def change(tid, op=None):
        return service.change_pin(tid, op or uuid4(), "0017", "0028", "0028")

    def grant(tid):
        token = uuid4().hex + uuid4().hex
        repo.rpc(
            "sec_pin_authorize_renewal",
            dict(
                p_hash=hashlib.sha256(token.encode()).hexdigest(),
                p_target=tid,
                p_auth=repo.trainer(tid)["auth_user_id"],
                p_reference="synthetic independent verification",
                p_expires=(now + timedelta(hours=2)).isoformat(),
            ),
        )
        return token

    def allowed(tid, iat=9999999999):
        return repo.rpc(
            "account_session_allowed",
            dict(p_auth=repo.trainer(tid)["auth_user_id"], p_iat=iat),
        )

    # Concurrent registration, response lost after Auth creation, no membership.
    op = uuid4()
    auth.fail_create_after = True
    with ThreadPoolExecutor(4) as pool:
        ids = list(pool.map(lambda _: register("Concurrent New", op), range(4)))
    assert len(set(ids)) == 1 and auth.creations == 1
    tid = ids[0]
    before = repo.trainer(tid)
    assert not before["is_admin"]
    assert (
        pg.sql(
            f"select count(*) from season_players where trainer_id='{tid}';"
        ).stdout.strip()
        == "0"
    )
    expect_error(
        lambda: service.register(
            op, "Concurrent New", "0099", "0099", "synthetic-invitation"
        )
    )
    expect_error(
        lambda: service.register(uuid4(), "Wrong Code", "0017", "0017", "wrong")
    )
    assert (
        bridge.authenticate(trainer_identifier=before["slug"], pin="0017").trainer_id
        == tid
    )

    # Interruption before claiming leaves a bound, resumable request; one Auth write.
    op = uuid4()
    repo.fail_before = "sec_pin_claim"
    expect_error(lambda: change(tid, op))
    assert not allowed(tid)
    calls = auth.password_calls
    service.change_pin(None, op, "0017", "0028", "0028", resume=True)
    assert auth.password_calls == calls + 1 and allowed(tid) and not allowed(tid, 1)
    service.change_pin(None, op, "0017", "0028", "0028", resume=True)
    assert auth.password_calls == calls + 1
    expect_error(
        lambda: service.change_pin(None, op, "0017", "0039", "0039", resume=True)
    )
    after = repo.trainer(tid)
    assert all(
        before[k] == after[k]
        for k in ("id", "auth_user_id", "is_admin", "globally_enabled")
    )

    # Real competing journal claims: only one may issue an Auth mutation.
    target = register()
    op = str(uuid4())
    prepared = repo.rpc(
        "sec_pin_prepare",
        dict(
            p_actor=target,
            p_target=target,
            p_operation=op,
            p_grant=None,
            p_hash="a" * 64,
            p_expires=(now + timedelta(hours=1)).isoformat(),
        ),
    )
    repo.rpc("sec_pin_bind", dict(p_kind="pin", p_operation=op, p_hash="a" * 64))
    with ThreadPoolExecutor(4) as pool:
        claims = list(
            pool.map(
                lambda _: repo.rpc(
                    "sec_pin_claim", dict(p_operation=op, p_hash="a" * 64)
                ),
                range(4),
            )
        )
    assert claims.count(True) == 1 and claims.count(False) == 3
    # No invented success receipt; this deliberately unfinished synthetic attempt stays blocked.
    assert not allowed(target)

    target = register()
    op = uuid4()
    repo.fail_after = "sec_pin_prepare"
    expect_error(lambda: change(target, op))
    assert not allowed(target)
    assert repo.credential_intent("pin", str(op))["request_hash"] != "0" * 64
    service.change_pin(None, op, "0017", "0028", "0028", resume=True)
    assert allowed(target)

    target = register()
    op = uuid4()
    repo.fail_before = "sec_pin_claim"
    expect_error(lambda: change(target, op))
    pg.sql(
        f"update account_pin_changes set expires_at=clock_timestamp()-interval '1 second' where operation_id='{op}';"
    )
    calls = auth.password_calls
    expect_error(
        lambda: service.change_pin(None, op, "0017", "0028", "0028", resume=True)
    )
    assert auth.password_calls == calls and not allowed(target)

    # Password accepted with lost response, then failed revoke and lost finish.
    for failure in ("password_after", "revoke", "finish_after"):
        target = register()
        op = uuid4()
        calls = auth.password_calls
        if failure == "password_after":
            auth.fail_password = "after"
        if failure == "revoke":
            auth.fail_revoke = True
        if failure == "finish_after":
            repo.fail_after = "sec_pin_finish"
        try:
            change(target, op)
        except AuthBackendError:
            pass
        service.change_pin(None, op, "0017", "0028", "0028", resume=True)
        assert auth.password_calls == calls + 1 and allowed(target)

    # Unknown/failed outbound mutation is never blindly retried, even at restart.
    target = register()
    op = uuid4()
    calls = auth.password_calls
    auth.fail_password = "before"
    expect_error(lambda: change(target, op))
    assert not allowed(target)
    restarted = VersionedAccountService(repo, auth, keyring=ring, enabled=False)
    expect_error(
        lambda: restarted.change_pin(None, op, "0017", "0028", "0028", resume=True)
    )
    assert auth.password_calls == calls + 1 and not allowed(target)

    # Existing trainer stays the same identity through operator-authorized renewal.
    legacy = str(uuid4())
    aid = str(uuid4())
    season = str(uuid4())
    pg.sql(f"""insert into trainers(id,display_name,slug,auth_user_id,is_admin) values('{legacy}','Legacy Owner','legacy-owner','{aid}',true);
      insert into account_credentials values('{legacy}',1,false);
      insert into seasons(id,name,created_by_trainer_id) values('{season}','Preserved History','{legacy}');
      insert into season_players(season_id,trainer_id) values('{season}','{legacy}');""")
    history = pg.sql(
        f"select to_jsonb(t) from season_players t where season_id='{season}';"
    ).stdout
    old = build_internal_auth_credential(legacy, "0017", ring.v1_pepper)
    auth.create(aid, old.email, old.password, "legacy")
    assert (
        bridge.authenticate(trainer_identifier="legacy-owner", pin="0017").auth_user_id
        == aid
    )
    expect_error(
        lambda: change(legacy)
    )  # Old PIN/session alone cannot authorize migration.
    token = grant(legacy)
    op = uuid4()
    auth.fail_revoke = True
    expect_error(lambda: service.renew_pin(op, token, "0039", "0039"))
    assert not allowed(legacy)
    service.renew_pin(op, token, "0039", "0039")
    assert (
        bridge.authenticate(trainer_identifier="legacy-owner", pin="0039").auth_user_id
        == aid
    )
    expect_error(lambda: auth.verify(old.email, old.password))
    expect_error(lambda: service.renew_pin(uuid4(), token, "0040", "0040"))
    assert (
        repo.trainer(legacy)["is_admin"]
        and history
        == pg.sql(
            f"select to_jsonb(t) from season_players t where season_id='{season}';"
        ).stdout
    )
    expect_error(
        lambda: repo.rpc(
            "sec_pin_prepare",
            dict(
                p_actor=legacy,
                p_target=tid,
                p_operation=str(uuid4()),
                p_grant=None,
                p_hash="a" * 64,
                p_expires=(now + timedelta(hours=1)).isoformat(),
            ),
        )
    )

    # Existing rate attempts remain counted; new credential key cannot clear them.
    identity = "synthetic-rate-target"
    scope = "login-account"
    legacy_key = (
        __import__("hmac")
        .new(
            ring.v1_pepper.encode(),
            json.dumps([scope, identity], sort_keys=True).encode(),
            hashlib.sha256,
        )
        .hexdigest()
    )
    repo.rpc("account_rate_check", dict(p_key=legacy_key, p_limit=2, p_seconds=900))
    pg.sql(
        f"update account_rate_windows set started_at=(select activated_at-interval '1 minute' from account_credential_policy) where key_hash='{legacy_key}';"
    )
    service.throttle(scope, identity, 2, 900)
    expect_error(lambda: service.throttle(scope, identity, 2, 900))
    replaced = VersionedAccountService(
        repo,
        auth,
        keyring=replace(ring, v2_pepper="synthetic-different-password-00004"),
    )
    expect_error(lambda: replaced.throttle(scope, identity, 2, 900))
    removed = VersionedAccountService(repo, auth, keyring=replace(ring, v1_pepper=None))
    expect_error(lambda: removed.throttle("unseen-scope", "unseen", 8, 900))

    assert http_journey(pg, repo, auth, service, bridge)

    # SQL/RLS reject v1 at cutoff even with profiles OFF; v2 continues to work.
    old_id = str(uuid4())
    old_auth = str(uuid4())
    pg.sql(f"""insert into trainers(id,display_name,slug,auth_user_id) values('{old_id}','Unrenewed','unrenewed','{old_auth}');
      insert into account_credentials values('{old_id}',1,false);
      update account_credential_policy set legacy_deadline=clock_timestamp()-interval '1 second';""")
    assert not allowed(old_id) and allowed(legacy)
    expect_error(
        lambda: service.credential(old_id, "0017"), (CredentialRenewalRequired,)
    )
    retired = VersionedAccountService(
        repo, auth, keyring=replace(ring, v1_pepper=None), enabled=False
    )
    assert (
        retired.credential(legacy, "0039").password
        == service.credential(legacy, "0039").password
    )
    assert pg.sql(
        f"update account_credentials set version=1 where trainer_id='{legacy}';",
        ok=False,
    ).returncode
    pg.sql(f"update trainers set globally_enabled=false where id='{legacy}';")
    assert not allowed(legacy)
    expect_error(lambda: retired.credential(legacy, "0039"))

    # Actual FastAPI guards with synthetic verified tokens and real SQL.
    for flag in (False, True):
        service.enabled = flag
        revoked_token = auth.verify(old.email, auth.users[aid]["password"]).access_token
        with TestClient(
            create_app(
                config=APIConfig(),
                container=ApiContainer(
                    auth_bridge=bridge,
                    token_verifier=auth,
                    session_refresher=auth,
                    principal_repository=repo,
                    trainer_repository=repo,
                    account_service=service,
                ),
            )
        ) as client:
            assert client.get(
                "/v1/me", headers={"Authorization": "Bearer " + revoked_token}
            ).status_code in (401, 403)
            assert client.post(
                "/v1/auth/refresh", json={"refresh_token": revoked_token}
            ).status_code in (401, 403)
            assert (
                client.post(
                    "/v1/auth/pin-renewal",
                    headers={"Idempotency-Key": str(uuid4())},
                    json={
                        "renewal_token": "x" * 64,
                        "new_pin": "0099",
                        "confirmation": "0099",
                    },
                ).status_code
                == 403
            )

    # Private functions/tables, legacy bypass, SQL rollback and RLS cutoff.
    for role in ("anon", "authenticated"):
        for statement in (
            "select * from account_credentials;",
            "select * from account_renewal_grants;",
            "select sec_pin_context(gen_random_uuid());",
            "select sec_pin_authorize_renewal(repeat('a',64),gen_random_uuid(),gen_random_uuid(),'forged',now()+interval '1 hour');",
        ):
            result = pg.sql(f"set role {role};" + statement, ok=False)
            assert result.returncode and "permission denied" in result.stderr
    assert pg.sql(
        "set role service_role;select account_pin_claim(gen_random_uuid(),repeat('a',64));",
        ok=False,
    ).returncode
    denied = pg.sql(
        f"set role authenticated;set request.jwt.claim.sub='{old_auth}';set request.jwt.claims='{{\"iat\":9999999999}}';select current_auth_uid() is null;"
    )
    assert denied.stdout.strip() == "t"
    catalog = pg.sql("""select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and proname like 'sec_pin_%'
      and (has_function_privilege('anon',p.oid,'execute') or has_function_privilege('authenticated',p.oid,'execute') or proconfig is null);""")
    assert catalog.stdout.strip() == "0"
    assert (
        pg.sql(
            "select count(*) from information_schema.columns where table_schema='public' and table_name like 'account_%' and column_name in ('pin','pins','password','pepper','secret');"
        ).stdout.strip()
        == "0"
    )
    assert (
        "0017"
        not in pg.sql("select request_context from account_registrations;").stdout
    )
    rollback_op = str(uuid4())
    pg.sql(
        f"begin; select sec_pin_registration_prepare('{rollback_op}','Rollback User','rollback-user',repeat('a',64),clock_timestamp()+interval '1 hour'); rollback;"
    )
    assert (
        pg.sql(
            f"select count(*) from account_registrations where operation_id='{rollback_op}';"
        ).stdout.strip()
        == "0"
    )
    return dict(
        concurrent_registration=4,
        creation_effects=1,
        interruption_groups=5,
        concurrent_pin_claims=4,
        one_claim_winner=True,
        atomic_bound_intent_recovery=True,
        expired_intent_denied=True,
        sql_rollback=True,
        verified_renewal=True,
        legacy_retirement_api_rls=True,
        old_pin_alone_denied=True,
        stable_identity_roles_history=True,
        private_permissions=True,
        rate_transition=True,
        api_refresh_flag_on_off=True,
        real_http_profile_admin_journey=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--parity", action="store_true")
    args = parser.parse_args()
    pg = LocalPG(args.bin, 55481)
    started = False
    result = {"status": "FAIL"}
    try:
        pg.start()
        started = True
        result["gates"] = gates(pg)
        if args.parity:
            result["parity"] = p4(pg)
            result["reset"] = reset_gate(pg)
        result["status"] = "PASS"
    finally:
        if started:
            pg.stop()
        result["cluster"] = str(pg.root)
        result["cleanup"] = (
            "owned database dropped; cluster stopped"
            if started
            else "startup not confirmed"
        )
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
