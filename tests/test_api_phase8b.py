from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.rate_limit import InMemoryWindowRateLimiter
from app.auth.errors import InvalidCredentialsError, InvalidSessionError
from app.auth.models import PinAuthResult, SupabaseAuthSession, SupabaseAuthUser, TrainerAuthIdentity


TRAINER_ID = "11111111-1111-1111-1111-111111111111"
AUTH_USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class FakePinAuthBridge:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def authenticate(self, *, trainer_identifier: str, pin: str) -> PinAuthResult:
        self.calls.append((trainer_identifier, pin))
        if self.fail is not None:
            raise self.fail
        return PinAuthResult(
            trainer_id=TRAINER_ID,
            auth_user_id=AUTH_USER_ID,
            session=SupabaseAuthSession(
                user_id=AUTH_USER_ID,
                access_token="access-token",
                refresh_token="refresh-token",
                expires_at=123,
                expires_in=3600,
            ),
        )


class FakeSessionRefresher:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def refresh_session(self, *, refresh_token: str) -> SupabaseAuthSession:
        self.calls.append(refresh_token)
        if self.fail is not None:
            raise self.fail
        return SupabaseAuthSession(
            user_id=AUTH_USER_ID,
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            expires_at=456,
            expires_in=3600,
        )


class FakeTokenVerifier:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def get_user(self, *, access_token: str) -> SupabaseAuthUser:
        self.calls.append(access_token)
        if self.fail is not None:
            raise self.fail
        return SupabaseAuthUser(user_id=AUTH_USER_ID)


class FakePrincipalRepository:
    def __init__(self, *, trainer: TrainerAuthIdentity | None = None) -> None:
        self.trainer = trainer or TrainerAuthIdentity(
            id=TRAINER_ID,
            display_name="Antonio",
            slug="anto",
            globally_enabled=True,
            auth_user_id=AUTH_USER_ID,
            is_admin=True,
        )
        self.calls: list[str] = []

    def find_by_auth_user_id(self, auth_user_id: str) -> TrainerAuthIdentity | None:
        self.calls.append(auth_user_id)
        return self.trainer if self.trainer and self.trainer.auth_user_id == auth_user_id else None


def _client(
    *,
    auth_bridge=None,
    session_refresher=None,
    token_verifier=None,
    principal_repository=None,
    rate_limiter=None,
) -> TestClient:
    container = ApiContainer(
        auth_bridge=auth_bridge,
        session_refresher=session_refresher,
        token_verifier=token_verifier,
        principal_repository=principal_repository,
        rate_limiter=rate_limiter,
    )
    return TestClient(create_app(container=container))


class Phase8BApiTests(unittest.TestCase):
    def test_health_is_minimal_and_unauthenticated(self) -> None:
        client = _client()

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "pokeapp-api", "status": "ok"})

    def test_pin_login_uses_body_and_returns_sanitized_session(self) -> None:
        bridge = FakePinAuthBridge()
        client = _client(auth_bridge=bridge)

        response = client.post("/v1/auth/pin-login", json={"trainer_identifier": "anto", "pin": "0042"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(bridge.calls, [("anto", "0042")])
        self.assertEqual(body["trainer_id"], TRAINER_ID)
        self.assertEqual(body["session"]["access_token"], "access-token")
        self.assertNotIn("pin", str(body).lower())
        self.assertNotIn("pepper", str(body).lower())
        self.assertNotIn("password", str(body).lower())
        self.assertNotIn("auth.pokeapp.invalid", str(body))

    def test_pin_login_does_not_accept_pin_from_query(self) -> None:
        bridge = FakePinAuthBridge()
        client = _client(auth_bridge=bridge)

        response = client.post("/v1/auth/pin-login?trainer_identifier=anto&pin=0042")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(bridge.calls, [])

    def test_pin_login_failures_are_generic(self) -> None:
        bridge = FakePinAuthBridge(fail=InvalidCredentialsError())
        client = _client(auth_bridge=bridge)

        response = client.post("/v1/auth/pin-login", json={"trainer_identifier": "anto", "pin": "0043"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_CREDENTIALS")
        self.assertNotIn("anto", str(response.json()).lower())

    def test_pin_login_is_rate_limited(self) -> None:
        bridge = FakePinAuthBridge()
        client = _client(
            auth_bridge=bridge,
            rate_limiter=InMemoryWindowRateLimiter(limit=1, window_seconds=60),
        )

        first = client.post("/v1/auth/pin-login", json={"trainer_identifier": "anto", "pin": "0042"})
        second = client.post("/v1/auth/pin-login", json={"trainer_identifier": "anto", "pin": "0042"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()["detail"]["code"], "RATE_LIMITED")

    def test_refresh_returns_sanitized_session(self) -> None:
        refresher = FakeSessionRefresher()
        client = _client(session_refresher=refresher)

        response = client.post("/v1/auth/refresh", json={"refresh_token": "refresh-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(refresher.calls, ["refresh-token"])
        self.assertEqual(response.json()["session"]["access_token"], "new-access-token")

    def test_invalid_refresh_token_is_generic_invalid_session(self) -> None:
        refresher = FakeSessionRefresher(fail=InvalidSessionError())
        client = _client(session_refresher=refresher)

        response = client.post("/v1/auth/refresh", json={"refresh_token": "bad"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_SESSION")
        self.assertNotIn("bad", str(response.json()))

    def test_me_uses_token_verifier_and_returns_principal(self) -> None:
        verifier = FakeTokenVerifier()
        repo = FakePrincipalRepository()
        client = _client(token_verifier=verifier, principal_repository=repo)

        response = client.get("/v1/me", headers={"Authorization": "Bearer opaque-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(verifier.calls, ["opaque-token"])
        self.assertEqual(repo.calls, [AUTH_USER_ID])
        self.assertEqual(
            response.json(),
            {
                "trainer_id": TRAINER_ID,
                "display_name": "Antonio",
                "is_admin": True,
                "globally_enabled": True,
            },
        )

    def test_me_rejects_missing_or_invalid_session(self) -> None:
        verifier = FakeTokenVerifier(fail=InvalidSessionError())
        repo = FakePrincipalRepository()
        client = _client(token_verifier=verifier, principal_repository=repo)

        missing = client.get("/v1/me")
        invalid = client.get("/v1/me", headers={"Authorization": "Bearer bad-token"})

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["detail"]["code"], "INVALID_SESSION")
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.json()["detail"]["code"], "INVALID_SESSION")
        self.assertEqual(repo.calls, [])

    def test_me_does_not_return_auth_private_fields(self) -> None:
        client = _client(token_verifier=FakeTokenVerifier(), principal_repository=FakePrincipalRepository())

        response = client.get("/v1/me", headers={"Authorization": "Bearer opaque-token"})
        body_text = str(response.json()).lower()

        self.assertNotIn("auth_user_id", body_text)
        self.assertNotIn("email", body_text)
        self.assertNotIn("pin", body_text)
        self.assertNotIn("pepper", body_text)
        self.assertNotIn("metadata", body_text)


if __name__ == "__main__":
    unittest.main()
