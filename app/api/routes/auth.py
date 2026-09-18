from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import (
    invalid_session_error,
    map_pin_login_error,
    map_session_error,
    rate_limited_error,
    unavailable_error,
)
from app.api.rate_limit import RateLimitExceeded
from app.api.schemas import (
    AuthSessionResponse,
    MeResponse,
    PinLoginRequest,
    RefreshRequest,
    RefreshResponse,
    SessionResponse,
)
from app.api.security import require_principal
from app.auth.errors import AuthError
from app.auth.models import PinAuthResult, SupabaseAuthSession

router = APIRouter(prefix="/v1/auth", tags=["auth"])
me_router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/pin-login", response_model=AuthSessionResponse)
def pin_login(
    payload: PinLoginRequest,
    request: Request,
    container: ApiContainer = Depends(get_api_container),
) -> AuthSessionResponse:
    if container.auth_bridge is None:
        raise unavailable_error()
    _check_pin_login_rate_limit(container, request, payload.trainer_identifier)
    try:
        result = container.auth_bridge.authenticate(
            trainer_identifier=payload.trainer_identifier,
            pin=payload.pin,
        )
    except AuthError as exc:
        raise map_pin_login_error(exc) from exc
    return _auth_response(result)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_session(
    payload: RefreshRequest,
    container: ApiContainer = Depends(get_api_container),
) -> RefreshResponse:
    if container.session_refresher is None:
        raise unavailable_error()
    try:
        session = container.session_refresher.refresh_session(refresh_token=payload.refresh_token)
    except AuthError as exc:
        raise map_session_error(exc) from exc
    if not session.access_token:
        raise invalid_session_error()
    return RefreshResponse(session=_session_response(session))


@me_router.get("/me", response_model=MeResponse)
def me(principal=Depends(require_principal)) -> MeResponse:
    return MeResponse(
        trainer_id=principal.trainer_id,
        display_name=principal.display_name,
        is_admin=principal.is_admin,
        globally_enabled=principal.globally_enabled,
    )


def _check_pin_login_rate_limit(container: ApiContainer, request: Request, trainer_identifier: str) -> None:
    if container.rate_limiter is None:
        return
    client_host = request.client.host if request.client else "unknown"
    key = f"pin-login:{client_host}:{trainer_identifier.strip().lower()}"
    try:
        container.rate_limiter.check(key=key)
    except RateLimitExceeded as exc:
        raise rate_limited_error() from exc


def _auth_response(result: PinAuthResult) -> AuthSessionResponse:
    return AuthSessionResponse(
        trainer_id=result.trainer_id,
        auth_user_id=result.auth_user_id,
        session=_session_response(result.session),
    )


def _session_response(session: SupabaseAuthSession) -> SessionResponse:
    return SessionResponse(
        user_id=session.user_id,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=session.expires_at,
        expires_in=session.expires_in,
    )
