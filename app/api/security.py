from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error, invalid_session_error, unavailable_error
from app.api.models import AuthenticatedPrincipal
from app.auth.errors import AuthError

bearer_scheme = HTTPBearer(auto_error=False)


def require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise invalid_session_error()
    return credentials.credentials


def require_principal(
    token: str = Depends(require_bearer_token),
    container: ApiContainer = Depends(get_api_container),
) -> AuthenticatedPrincipal:
    if container.token_verifier is None or container.principal_repository is None:
        raise unavailable_error()
    try:
        user = container.token_verifier.get_user(access_token=token)
    except AuthError as exc:
        from app.api.errors import map_session_error

        raise map_session_error(exc) from exc
    try:
        trainer = container.principal_repository.find_by_auth_user_id(user.user_id)
    except AuthError as exc:
        raise unavailable_error() from exc
    if trainer is None:
        raise invalid_session_error()
    return AuthenticatedPrincipal.from_trainer(trainer)


def require_enabled_principal(
    principal: AuthenticatedPrincipal = Depends(require_principal),
) -> AuthenticatedPrincipal:
    if not principal.globally_enabled:
        raise api_error(403, "TRAINER_DISABLED", "Trainer is disabled.")
    return principal
