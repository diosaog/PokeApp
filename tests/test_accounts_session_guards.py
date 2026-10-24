"""Issued and refreshed sessions must respect guards regardless of the UI flag."""

from dataclasses import replace
import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import AuthBackendError, InvalidSessionError
from app.auth.models import SupabaseAuthUser
from test_api_phase8b import (
    AUTH_USER_ID,
    FakePinAuthBridge,
    FakePrincipalRepository,
    FakeSessionRefresher,
    FakeTokenVerifier,
)


class Guard:
    def __init__(self, enabled, allowed=True):
        self.enabled, self.allowed = enabled, allowed
        self.calls = []

    def valid_session(self, uid, token):
        self.calls.append((uid, token))
        if isinstance(self.allowed, Exception):
            raise self.allowed
        return self.allowed

    def throttle(self, *args):
        pass


class LoginRepository(FakePrincipalRepository):
    def find_for_login(self, identifier):
        return self.trainer


class AccountSessionGuardTests(unittest.TestCase):
    def client(self, flag, allowed=True, *, enabled=True, admin=True, expired=False):
        self.guard = Guard(flag, allowed)
        self.repo = LoginRepository()
        self.repo.trainer = replace(
            self.repo.trainer, globally_enabled=enabled, is_admin=admin
        )
        self.verifier = FakeTokenVerifier(
            fail=InvalidSessionError() if expired else None
        )
        return self.enterContext(
            TestClient(
                create_app(
                    container=ApiContainer(
                        auth_bridge=FakePinAuthBridge(),
                        session_refresher=FakeSessionRefresher(),
                        token_verifier=self.verifier,
                        principal_repository=self.repo,
                        trainer_repository=self.repo,
                        account_service=self.guard,
                    )
                )
            )
        )

    def issued(self, client, path):
        return client.post(
            path,
            json=(
                {"refresh_token": "synthetic-refresh"}
                if path.endswith("refresh")
                else {"trainer_identifier": "anto", "pin": "0071"}
            ),
        )

    def test_revoked_sessions_fail_with_feature_on_and_off(self):
        for flag in (False, True):
            client = self.client(flag, False)
            self.assertEqual(
                client.get(
                    "/v1/me", headers={"Authorization": "Bearer revoked"}
                ).status_code,
                401,
            )
            for path in ("/v1/auth/pin-login", "/v1/auth/refresh"):
                with self.subTest(flag=flag, path=path):
                    result = self.issued(client, path)
                    self.assertEqual(result.status_code, 401)
                    self.assertNotIn("refresh_token", result.text)
            self.assertEqual(self.guard.calls[-1], (AUTH_USER_ID, "new-access-token"))

    def test_valid_issued_sessions_keep_identity_and_work_with_flag_off(self):
        for flag in (False, True):
            client = self.client(flag)
            for path in ("/v1/auth/pin-login", "/v1/auth/refresh"):
                response = self.issued(client, path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["session"]["user_id"], AUTH_USER_ID)

    def test_disabled_account_cannot_receive_login_or_refresh_session(self):
        for flag in (False, True):
            client = self.client(flag, enabled=False)
            for path in ("/v1/auth/pin-login", "/v1/auth/refresh"):
                self.assertEqual(self.issued(client, path).status_code, 403)

    def test_expired_token_cannot_reach_guard(self):
        for flag in (False, True):
            client = self.client(flag, expired=True)
            self.assertEqual(self.issued(client, "/v1/auth/refresh").status_code, 401)
            self.assertEqual(self.guard.calls, [])

    def test_guard_outage_is_unavailable_not_access(self):
        for flag in (False, True):
            client = self.client(flag, AuthBackendError("synthetic backend outage"))
            self.assertEqual(self.issued(client, "/v1/auth/refresh").status_code, 503)

    def test_refresh_cannot_link_an_unprovisioned_auth_user(self):
        for flag in (False, True):
            client = self.client(flag)
            self.repo.trainer = None
            self.assertEqual(self.issued(client, "/v1/auth/refresh").status_code, 401)

    def test_admin_checks_remain_after_session_checks(self):
        client = self.client(True, admin=False)
        response = client.get(
            "/v1/admin/accounts", headers={"Authorization": "Bearer valid"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.guard.calls, [(AUTH_USER_ID, "valid")])

    def test_returned_user_must_match_verified_token(self):
        client = self.client(False)
        other = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        self.repo.trainer = replace(self.repo.trainer, auth_user_id=other)
        self.verifier.get_user = lambda **kw: SupabaseAuthUser(user_id=other)
        self.assertEqual(self.issued(client, "/v1/auth/refresh").status_code, 401)
