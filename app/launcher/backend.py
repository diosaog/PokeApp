"""Existing PokeApp identity only. No service keys, database clients or save writes."""

from __future__ import annotations

from dataclasses import dataclass, field
import time

import httpx
from pydantic import Field, ValidationError

from app.launcher.config import backend_origin
from app.save_parser.models import WireModel


class BackendError(Exception):
    pass


class SessionTokens(WireModel):
    user_id: str = Field(min_length=1, max_length=128)
    access_token: str = Field(min_length=1, max_length=16384, repr=False)
    refresh_token: str = Field(default="", max_length=16384, repr=False)
    expires_at: int | None = None
    expires_in: int | None = None


class LoginResponse(WireModel):
    trainer_id: str
    auth_user_id: str
    session: SessionTokens = Field(repr=False)


class RefreshResponse(WireModel):
    session: SessionTokens = Field(repr=False)


class BackendPrincipal(WireModel):
    trainer_id: str = Field(min_length=1)
    display_name: str
    is_admin: bool
    globally_enabled: bool


class BackendClient:
    def __init__(self, origin: str, *, transport=None):
        self.origin = backend_origin(origin)
        self._http = httpx.Client(
            base_url=self.origin,
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def close(self):
        self._http.close()

    def _request(self, method, path, model, *, body=None, token=None):
        try:
            response = self._http.request(
                method,
                path,
                json=body,
                headers={"Authorization": "Bearer " + token} if token else {},
                follow_redirects=False,
            )
            if response.status_code in (401, 403):
                raise BackendError("SESSION_REJECTED")
            if response.status_code == 429:
                raise BackendError("RATE_LIMITED")
            if response.status_code != 200 or len(response.content) > 65536:
                raise BackendError("BACKEND_UNAVAILABLE")
            return model.model_validate_json(response.content)
        except (httpx.HTTPError, ValidationError, ValueError):
            raise BackendError("BACKEND_UNAVAILABLE") from None

    def login(self, trainer_identifier: str, pin: str) -> LoginResponse:
        return self._request(
            "POST",
            "/v1/auth/pin-login",
            LoginResponse,
            body={"trainer_identifier": trainer_identifier, "pin": pin},
        )

    def refresh(self, refresh_token: str) -> SessionTokens:
        return self._request(
            "POST",
            "/v1/auth/refresh",
            RefreshResponse,
            body={"refresh_token": refresh_token},
        ).session

    def me(self, access_token: str) -> BackendPrincipal:
        return self._request("GET", "/v1/me", BackendPrincipal, token=access_token)


@dataclass
class LauncherSession:
    client: BackendClient = field(repr=False)
    _tokens: SessionTokens | None = field(default=None, init=False, repr=False)
    _principal: BackendPrincipal | None = field(default=None, init=False, repr=False)

    def logout(self):
        self._tokens = self._principal = None

    def login(self, trainer_identifier: str, pin: str) -> BackendPrincipal:
        self.logout()
        result = self.client.login(trainer_identifier, pin)
        principal = self.client.me(result.session.access_token)
        if (
            not principal.globally_enabled
            or principal.trainer_id != result.trainer_id
            or result.auth_user_id != result.session.user_id
        ):
            raise BackendError("SESSION_REJECTED")
        self._tokens, self._principal = result.session, principal
        return principal

    def principal(self) -> BackendPrincipal:
        if not self._tokens or not self._principal:
            raise BackendError("LOGIN_REQUIRED")
        try:
            if (
                self._tokens.expires_at is None
                or self._tokens.expires_at <= time.time() + 30
            ):
                if not self._tokens.refresh_token:
                    raise BackendError("LOGIN_REQUIRED")
                refreshed = self.client.refresh(self._tokens.refresh_token)
                if refreshed.user_id != self._tokens.user_id:
                    raise BackendError("SESSION_REJECTED")
                self._tokens = refreshed
            principal = self.client.me(self._tokens.access_token)
            if (
                not principal.globally_enabled
                or principal.trainer_id != self._principal.trainer_id
            ):
                raise BackendError("SESSION_REJECTED")
            self._principal = principal
            return principal
        except BackendError:
            self.logout()
            raise
