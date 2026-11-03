"""The API never keeps or renews a trainer's Supabase session by itself.

Production, 2026-10-28 .. 2026-11-02: the API's shared Supabase client stored
every session it refreshed or signed in and, 10 s before that access token
expired, refreshed it again on a background timer (twice: get_session() and
the timer). The trainer's own Launcher or web still held the previous refresh
token; its next renewal was taken as token reuse and Supabase revoked the whole
session. Four sessions (Anto x3, Iker x1) ended exactly 3590 s after their last
own renewal, and the Launcher stopped syncing until the trainer signed in again.
"""

import base64
import json
import time
import unittest
from unittest.mock import patch

import httpx

from app.auth.errors import InvalidSessionError
from app.auth.supabase_adapter import SupabaseAuthClient
from app.repositories.supabase import http

URL = "https://example.supabase.co"
USER_ID = "5f3b8b8e-3a41-4b8e-9a52-6a0f0c1d2e3f"


def _part(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


ANON = _part({"alg": "HS256", "typ": "JWT"}) + "." + _part({"role": "anon"}) + ".s"


class GoTrue:
    """Supabase Auth double: every grant rotates the refresh token."""

    def __init__(self, expires_in=3600):
        self.expires_in, self.grants, self.issued = expires_in, [], 0

    def __call__(self, request):
        if request.url.path != "/auth/v1/token":
            return httpx.Response(404, json={"msg": "unexpected"})
        body = json.loads(request.content)
        self.grants.append((request.url.params["grant_type"], body.get("refresh_token")))
        self.issued += 1
        return httpx.Response(
            200,
            json={
                "access_token": f"access-{self.issued}",
                "refresh_token": f"refresh-{self.issued}",
                "token_type": "bearer",
                "expires_in": self.expires_in,
                "expires_at": int(time.time()) + self.expires_in,
                "user": {
                    "id": USER_ID,
                    "aud": "authenticated",
                    "role": "authenticated",
                    "email": "trainer@pokeapp.invalid",
                    "app_metadata": {},
                    "user_metadata": {},
                    "created_at": "2026-11-03T00:00:00Z",
                },
            },
        )


class ServerAuthSessionTests(unittest.TestCase):
    def client(self, gotrue):
        pool = httpx.Client(transport=httpx.MockTransport(gotrue))
        self.addCleanup(pool.close)
        patcher = patch.object(http, "_auth_session", pool)
        patcher.start()
        self.addCleanup(patcher.stop)
        auth = SupabaseAuthClient(http.create_client(URL, ANON))
        gotrue_client = auth._client.auth

        def stop_timer():
            # A red run must not leave a renewal thread behind.
            if gotrue_client._refresh_token_timer is not None:
                gotrue_client._refresh_token_timer.cancel()

        self.addCleanup(stop_timer)
        return auth, gotrue_client

    def assert_nothing_kept(self, gotrue_client):
        self.assertIsNone(gotrue_client._refresh_token_timer)
        self.assertFalse(gotrue_client._auto_refresh_token)
        self.assertFalse(gotrue_client._persist_session)
        self.assertIsNone(gotrue_client._storage.get_item(gotrue_client._storage_key))

    def test_refreshing_a_trainer_session_schedules_no_server_renewal(self):
        gotrue = GoTrue()
        auth, gotrue_client = self.client(gotrue)
        session = auth.refresh_session(refresh_token="launcher-token")
        self.assertEqual(session.refresh_token, "refresh-1")
        self.assertEqual(gotrue.grants, [("refresh_token", "launcher-token")])
        self.assert_nothing_kept(gotrue_client)

    def test_pin_sign_in_schedules_no_server_renewal(self):
        gotrue = GoTrue()
        auth, gotrue_client = self.client(gotrue)
        session = auth.sign_in_with_password(email="t@pokeapp.invalid", password="pin")
        self.assertEqual(session.refresh_token, "refresh-1")
        self.assertEqual([g[0] for g in gotrue.grants], ["password"])
        self.assert_nothing_kept(gotrue_client)

    def test_a_short_lived_session_is_never_renewed_in_the_background(self):
        """The production failure, compressed: with a 1 s token the old client
        renewed the trainer's session on its own within a second."""
        gotrue = GoTrue(expires_in=1)
        auth, gotrue_client = self.client(gotrue)
        auth.refresh_session(refresh_token="launcher-token")
        time.sleep(1.5)
        self.assertEqual(gotrue.grants, [("refresh_token", "launcher-token")])
        self.assert_nothing_kept(gotrue_client)

    def test_an_empty_token_never_falls_back_to_another_trainers_session(self):
        gotrue = GoTrue()
        auth, _ = self.client(gotrue)
        auth.refresh_session(refresh_token="other-trainer-token")
        for empty in ("", None):
            with self.assertRaises(InvalidSessionError):
                auth.get_user(access_token=empty)
        self.assertEqual(len(gotrue.grants), 1)

    def test_an_empty_refresh_token_never_renews_another_trainers_session(self):
        """Without a token the SDK refreshes the session it last kept in
        memory and returns it: a new session of another trainer."""
        gotrue = GoTrue()
        auth, _ = self.client(gotrue)
        auth.refresh_session(refresh_token="other-trainer-token")
        for empty in ("", None):
            with self.assertRaises(InvalidSessionError):
                auth.refresh_session(refresh_token=empty)
        self.assertEqual(gotrue.grants, [("refresh_token", "other-trainer-token")])


if __name__ == "__main__":
    unittest.main()
