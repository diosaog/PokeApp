from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.errors import (
    AuthBackendError,
    AuthError,
    AuthIdentityMismatchError,
    AuthNotProvisionedError,
    InvalidCredentialsError,
    InvalidSessionError,
)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def invalid_credentials_error() -> HTTPException:
    return api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Invalid credentials.")


def invalid_session_error() -> HTTPException:
    return api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_SESSION", "Invalid session.")


def rate_limited_error() -> HTTPException:
    return api_error(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", "Too many login attempts.")


def unavailable_error() -> HTTPException:
    return api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "AUTH_UNAVAILABLE", "Authentication is unavailable.")


def map_pin_login_error(exc: AuthError) -> HTTPException:
    if isinstance(
        exc,
        (
            InvalidCredentialsError,
            AuthNotProvisionedError,
            AuthIdentityMismatchError,
        ),
    ):
        return invalid_credentials_error()
    if isinstance(exc, AuthBackendError):
        return unavailable_error()
    return invalid_credentials_error()


def map_session_error(exc: AuthError) -> HTTPException:
    if isinstance(exc, InvalidSessionError):
        return invalid_session_error()
    if isinstance(exc, AuthBackendError):
        return unavailable_error()
    return invalid_session_error()
