import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.accounts import AccountError, AccountService, account_name
from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import AuthBackendError
from app.auth.errors import InvalidCredentialsError
from app.auth.models import TrainerAuthIdentity, SupabaseAuthSession
from app.auth.service import PinAuthBridge
from app.repositories.supabase.accounts import SupabaseAccountAuth


class Repository:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows, self.names, self.trainers, self.rates = {}, {}, {}, {}
        self.fail_complete = False

    def reserve(self, op, digest, name, slug):
        with self.lock:
            if op in self.rows:
                if self.rows[op]["request_hash"] != digest:
                    raise AccountError("ACCOUNT_CONFLICT")
                return copy.copy(self.rows[op])
            if slug in self.names:
                raise AccountError("ACCOUNT_CONFLICT")
            row = dict(
                trainer_id=str(uuid4()),
                auth_user_id=str(uuid4()),
                request_hash=digest,
                status="pending",
            )
            self.rows[op], self.names[slug] = row, op
            self.trainers[row["trainer_id"]] = dict(
                enabled=False, admin=False, auth_id=None
            )
            return copy.copy(row)

    def complete(self, op, digest, auth_id):
        with self.lock:
            if self.fail_complete:
                raise AuthBackendError()
            row = self.rows[op]
            assert row["request_hash"] == digest and row["auth_user_id"] == auth_id
            if row["status"] != "complete":
                row["status"] = "complete"
                self.trainers[row["trainer_id"]].update(enabled=True, auth_id=auth_id)
            return row["trainer_id"]

    def rate_check(self, key, limit, seconds):
        with self.lock:
            self.rates[key] = self.rates.get(key, 0) + 1
            return self.rates[key] <= limit


class Auth:
    def __init__(self):
        self.lock = threading.Lock()
        self.users, self.passwords = {}, {}
        self.unknown_after_create = False
        self.unavailable = False

    def lookup(self, uid):
        if self.unavailable:
            raise AuthBackendError()
        return self.users.get(uid)

    def create(self, uid, email, password, marker):
        with self.lock:
            if uid in self.users:
                raise AuthBackendError()
            self.users[uid] = dict(
                id=uid, email=email, marker=marker, role="authenticated"
            )
            self.passwords[uid] = password
        if self.unknown_after_create:
            raise AuthBackendError()


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.auth = Repository(), Auth()
        self.service = AccountService(
            self.repo, self.auth, pepper="test-only-pepper", enabled=True, access_code="synthetic-invitation"
        )
        self.key = uuid4()

    def register(self, **kw):
        data = dict(
            operation=self.key,
            name="New Trainer",
            pin="0061",
            confirmation="0061",
            access_code="synthetic-invitation",
        )
        data.update(kw)
        return self.service.register(**data)

    def test_registration_stable_identity_credential_and_no_admin(self):
        result = self.register()
        row = self.repo.rows[str(self.key)]
        credential = build_internal_auth_credential(
            result["trainer_id"], "0061", "test-only-pepper"
        )
        self.assertEqual(self.auth.passwords[row["auth_user_id"]], credential.password)
        self.assertEqual(
            self.auth.users[row["auth_user_id"]]["email"], credential.email
        )
        self.assertFalse(self.repo.trainers[result["trainer_id"]]["admin"])
        self.assertNotIn("0061", str(self.repo.rows))

    def test_registered_identity_uses_existing_login_bridge(self):
        result = self.register()
        tid = result["trainer_id"]
        row = self.repo.rows[str(self.key)]
        repository, auth = self.repo, self.auth

        class TrainerLookup:
            def find_for_login(self, identifier):
                t = repository.trainers[tid]
                return TrainerAuthIdentity(
                    id=tid,
                    display_name="New Trainer",
                    slug="new-trainer",
                    auth_user_id=t["auth_id"],
                    globally_enabled=t["enabled"],
                    is_admin=t["admin"],
                )

        class PasswordAuth:
            def sign_in_with_password(self, *, email, password):
                uid = row["auth_user_id"]
                if auth.users[uid]["email"] != email or auth.passwords[uid] != password:
                    raise InvalidCredentialsError()
                return SupabaseAuthSession(
                    user_id=uid,
                    access_token="test-session",
                    refresh_token="test-refresh",
                )

        bridge = PinAuthBridge(
            trainers=TrainerLookup(), auth=PasswordAuth(), pepper="test-only-pepper"
        )
        self.assertEqual(
            bridge.authenticate(
                trainer_identifier="new-trainer", pin="0061"
            ).trainer_id,
            tid,
        )
        with self.assertRaises(InvalidCredentialsError):
            bridge.authenticate(trainer_identifier="new-trainer", pin="0062")
        repository.trainers[tid]["enabled"] = False
        with self.assertRaises(InvalidCredentialsError):
            bridge.authenticate(trainer_identifier="new-trainer", pin="0061")

    def test_wrong_invitation_and_pin_are_side_effect_free(self):
        for kwargs in (
            {"access_code": "wrong"},
            {"pin": "0062"},
            {"pin": "１２３４", "confirmation": "１２３４"},
        ):
            with self.assertRaises(AccountError):
                self.register(**kwargs)
        self.assertEqual(self.repo.rows, {})

    def test_normalized_name_duplicate_and_unsafe_names(self):
        self.assertEqual(account_name("  José  Pérez "), ("José Pérez", "jose-perez"))
        self.register()
        with self.assertRaises(AccountError):
            self.register(operation=uuid4(), name=" NEW TRAINER ")
        for name in ("<script>", "../admin", "", "a" * 49, str(uuid4())):
            with self.assertRaises(AccountError):
                account_name(name)

    def test_same_request_replays_and_changed_body_does_not(self):
        self.assertEqual(self.register(), self.register())
        with self.assertRaises(AccountError):
            self.register(pin="0062", confirmation="0062")
        self.assertEqual(len(self.auth.users), 1)

    def test_response_lost_after_auth_create_reconciles(self):
        self.auth.unknown_after_create = True
        result = self.register()
        self.assertEqual(self.register(), result)
        self.assertEqual(len(self.auth.users), 1)

    def test_partial_mapping_failure_keeps_disabled_then_recovers(self):
        self.repo.fail_complete = True
        with self.assertRaises(AuthBackendError):
            self.register()
        self.assertFalse(next(iter(self.repo.trainers.values()))["enabled"])
        self.repo.fail_complete = False
        self.register()
        self.assertEqual(len(self.auth.users), 1)

    def test_mismatched_existing_auth_never_activated_or_recreated(self):
        self.repo.fail_complete = True
        with self.assertRaises(AuthBackendError):
            self.register()
        self.repo.fail_complete = False
        next(iter(self.auth.users.values()))["marker"] = "wrong"
        with self.assertRaises(AccountError):
            self.register()
        self.assertFalse(next(iter(self.repo.trainers.values()))["enabled"])

    def test_disabled_complete_account_not_reenabled_on_retry(self):
        result = self.register()
        self.repo.trainers[result["trainer_id"]]["enabled"] = False
        self.register()
        self.assertFalse(self.repo.trainers[result["trainer_id"]]["enabled"])

    def test_concurrent_same_name_and_same_key(self):
        def call(key):
            try:
                return self.register(operation=key)
            except AccountError:
                return None

        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(call, [self.key] * 4))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual(len(self.auth.users), 1)
        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(call, [uuid4() for _ in range(4)]))
        self.assertEqual(results, [None] * 4)

    def test_api_strict_body_and_validation_never_echo_credentials(self):
        client = TestClient(
            create_app(container=ApiContainer(account_service=self.service))
        )
        body = dict(
            trainer_name="New Trainer",
            pin="0061",
            confirmation="0061",
            access_code="synthetic-invitation",
        )
        headers = {"Idempotency-Key": str(self.key)}
        response = client.post("/v1/auth/register", json=body, headers=headers)
        self.assertEqual(response.status_code, 200)
        for changed in (
            {**body, "is_admin": True},
            {**body, "pin": "PRIVATE" * 100},
            {**body, "pin": {"secret": "PRIVATE"}},
        ):
            response = client.post("/v1/auth/register", json=changed, headers=headers)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("PRIVATE", response.text)
        response = client.post(
            "/v1/auth/register", json={**body, "access_code": "wrong"}, headers=headers
        )
        self.assertEqual(response.status_code, 400)

    def test_disabled_by_default_and_rate_limits_fail_closed(self):
        self.service.enabled = False
        with self.assertRaises(AccountError):
            self.register()
        self.service.enabled = True
        self.service.throttle("test", "same", 1)
        with self.assertRaises(AccountError) as caught:
            self.service.throttle("test", "same", 1)
        self.assertEqual(caught.exception.status, 429)

    def test_admin_lookup_does_not_treat_outage_as_absence(self):
        class Broken:
            def get_user_by_id(self, uid):
                raise RuntimeError("secret")

        with self.assertRaises(AuthBackendError) as caught:
            SupabaseAccountAuth(Broken()).lookup(str(uuid4()))
        self.assertNotIn("secret", str(caught.exception))
