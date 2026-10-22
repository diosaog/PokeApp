import io
import threading
import unittest
from uuid import uuid4

from PIL import Image
from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.accounts import AccountError, AccountService
from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import AuthBackendError, InvalidCredentialsError
from app.auth.models import SupabaseAuthSession
from test_api_phase8b import (
    AUTH_USER_ID,
    TRAINER_ID,
    FakePrincipalRepository,
    FakeTokenVerifier,
)


class ProfileRepository:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows = {
            TRAINER_ID: dict(
                id=TRAINER_ID,
                display_name="Antonio",
                slug="anto",
                auth_user_id=AUTH_USER_ID,
                globally_enabled=True,
                is_admin=True,
                photo_key=None,
                profile_revision=0,
            )
        }
        self.operations = {}
        self.guards = {}
        self.photos = {}

    def trainer(self, tid):
        return self.rows.get(tid)

    def trainers(self, offset):
        return list(self.rows.values())[offset : offset + 50]

    def photo_urls(self, keys):
        return {k: "https://example.invalid/signed" for k in keys}

    def upload_photo(self, key, data):
        self.photos[key] = data

    def pin_operation(self, op):
        return self.operations.get(op)

    def rate_check(self, *args):
        return True

    def profile_update(self, actor, operation, digest, revision, name, slug, photo):
        row = self.rows[actor]
        if row["profile_revision"] != revision:
            raise AccountError("ACCOUNT_STALE")
        if name:
            row.update(display_name=name, slug=slug)
        if photo:
            row["photo_key"] = photo
        row["profile_revision"] += 1
        return dict(trainer_id=actor, revision=row["profile_revision"])

    def rpc(self, name, params):
        with self.lock:
            if name == "account_session_allowed":
                return not self.guards.get(TRAINER_ID, False)
            op = params["p_operation"]
            if name == "account_pin_begin":
                row = dict(
                    actor_id=params["p_actor"],
                    target_id=params["p_target"],
                    request_hash=params["p_hash"],
                    stage="prepared",
                )
                self.operations[op] = row
                self.guards[row["target_id"]] = True
                return row
            row = self.operations[op]
            if name == "account_pin_claim":
                if row["stage"] != "prepared":
                    return False
                row["stage"] = "updating"
                return True
            if name == "account_pin_finish":
                row["stage"] = "complete"
                self.guards[row["target_id"]] = False
                return dict(status="changed", sign_in_required=True)
            raise AssertionError(name)


class PasswordAuth:
    def __init__(self):
        self.credential = build_internal_auth_credential(
            TRAINER_ID, "0017", "test-pepper"
        )
        self.current = self.credential.password
        self.updates = 0
        self.revocations = 0
        self.lost = False
        self.fail_before = False
        self.fail_revoke = False

    def verify(self, email, password):
        if email != self.credential.email or password != self.current:
            raise InvalidCredentialsError()
        return SupabaseAuthSession(
            user_id=AUTH_USER_ID,
            access_token="verified-temporary-token",
            refresh_token="",
        )

    def password(self, uid, password):
        assert uid == AUTH_USER_ID
        self.updates += 1
        if self.fail_before:
            raise AuthBackendError()
        self.current = password
        if self.lost:
            raise AuthBackendError()

    def revoke(self, token):
        if self.fail_revoke:
            raise AuthBackendError()
        self.revocations += 1


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.repo = ProfileRepository()
        self.auth = PasswordAuth()
        self.service = AccountService(
            self.repo, self.auth, pepper="test-pepper", enabled=True
        )
        self.operation = uuid4()

    def change(self, **kw):
        values = dict(
            actor=TRAINER_ID,
            operation=self.operation,
            current_pin="0017",
            new_pin="0028",
            confirmation="0028",
        )
        values.update(kw)
        return self.service.change_pin(**values)

    def test_public_allowlist_and_rename_keeps_identity(self):
        self.service.rename(TRAINER_ID, uuid4(), 0, "Nuevo nombre")
        profile = self.service.profile(TRAINER_ID, str(uuid4()))
        self.assertEqual(
            set(profile), {"trainer_id", "display_name", "photo_url", "revision"}
        )
        self.assertIsNone(profile["revision"])
        self.assertEqual(self.repo.rows[TRAINER_ID]["auth_user_id"], AUTH_USER_ID)
        self.assertTrue(self.repo.rows[TRAINER_ID]["is_admin"])

    def test_photo_reencodes_and_uses_own_content_address(self):
        data = io.BytesIO()
        Image.new("RGB", (1000, 1600), "blue").save(data, "PNG")
        result = self.service.photo(TRAINER_ID, self.operation, 0, data.getvalue())
        key, stored = next(iter(self.repo.photos.items()))
        self.assertTrue(key.startswith("portraits/" + TRAINER_ID + "/"))
        with Image.open(io.BytesIO(stored)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (500, 800))
            self.assertFalse(image.getexif())
        self.assertEqual(result["revision"], 1)

    def test_photo_rejects_unsafe_oversize_and_animation(self):
        animation = io.BytesIO()
        Image.new("RGB", (10, 10)).save(animation, "GIF")
        for data in (
            b"<svg onload='secret'>",
            b"x" * (5 * 1024 * 1024 + 1),
            animation.getvalue(),
        ):
            with self.assertRaises(AccountError):
                self.service.photo(TRAINER_ID, self.operation, 0, data)
        self.assertEqual(self.repo.photos, {})

    def test_pin_requires_current_and_no_journal_on_failure(self):
        with self.assertRaises(InvalidCredentialsError):
            self.change(current_pin="9999")
        self.assertEqual(self.repo.operations, {})

    def test_pin_changes_once_revokes_sessions_and_replays(self):
        result = self.change()
        self.assertEqual(self.change(), result)
        self.assertEqual(self.auth.updates, 1)
        self.assertEqual(self.auth.revocations, 1)
        self.assertFalse(self.repo.guards[TRAINER_ID])

    def test_lost_password_response_reconciles_without_second_update(self):
        self.auth.lost = True
        self.change()
        self.change()
        self.assertEqual(self.auth.updates, 1)

    def test_revoke_failure_remains_blocked_then_exact_resume_finishes(self):
        self.auth.fail_revoke = True
        with self.assertRaises(AuthBackendError):
            self.change()
        self.assertTrue(self.repo.guards[TRAINER_ID])
        self.auth.fail_revoke = False
        self.change(actor=None, resume=True)
        self.assertEqual(self.auth.updates, 1)
        self.assertFalse(self.repo.guards[TRAINER_ID])

    def test_ambiguous_before_update_never_reissues_or_enables(self):
        self.auth.fail_before = True
        with self.assertRaises(AccountError):
            self.change()
        self.auth.fail_before = False
        with self.assertRaises(AccountError):
            self.change(actor=None, resume=True)
        self.assertEqual(self.auth.updates, 1)
        self.assertTrue(self.repo.guards[TRAINER_ID])

    def test_resume_cannot_originate_or_change_intent(self):
        with self.assertRaises(AccountError):
            self.change(actor=None, resume=True)
        self.change()
        with self.assertRaises(AccountError):
            self.change(current_pin="0099")

    def test_api_owner_only_and_private_fields_rejected(self):
        client = TestClient(
            create_app(
                container=ApiContainer(
                    account_service=self.service,
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=FakePrincipalRepository(),
                )
            )
        )
        headers = {"Authorization": "Bearer dummy", "Idempotency-Key": str(uuid4())}
        self.assertEqual(
            client.put(
                "/v1/account/name",
                json={"display_name": "Other", "expected_revision": 0},
                headers=headers,
            ).status_code,
            200,
        )
        bad = client.put(
            "/v1/account/name",
            json={
                "display_name": "Other",
                "expected_revision": 1,
                "trainer_id": str(uuid4()),
                "is_admin": True,
            },
            headers=headers,
        )
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(
            client.put(
                "/v1/account/name",
                json={"display_name": "Other", "expected_revision": 1},
            ).status_code,
            401,
        )
        profile = client.get(f"/v1/accounts/{TRAINER_ID}", headers=headers).json()
        self.assertNotIn("auth_user_id", profile)
        self.assertNotIn("is_admin", profile)
        self.repo.guards[TRAINER_ID] = True
        self.assertEqual(client.get("/v1/me", headers=headers).status_code, 401)
