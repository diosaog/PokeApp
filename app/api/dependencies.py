from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.api.config import APIConfig
from app.api.ports import AccessTokenVerifierPort, SessionRefreshPort, TrainerPrincipalRepository
from app.api.rate_limit import InMemoryWindowRateLimiter, RateLimiter
from app.auth.ports import TrainerAuthRepository
from app.auth.service import PinAuthBridge


@dataclass(frozen=True)
class ApiContainer:
    auth_bridge: PinAuthBridge | None = None
    session_refresher: SessionRefreshPort | None = None
    token_verifier: AccessTokenVerifierPort | None = None
    trainer_repository: TrainerAuthRepository | None = None
    principal_repository: TrainerPrincipalRepository | None = None
    rate_limiter: RateLimiter | None = None


def get_api_container(request: Request) -> ApiContainer:
    return request.app.state.api_container


def create_default_container(config: APIConfig | None = None) -> ApiContainer:
    config = config or APIConfig.from_env()
    rate_limiter = InMemoryWindowRateLimiter(
        limit=config.pin_login_limit,
        window_seconds=config.pin_login_window_seconds,
    )
    auth_client = None
    trainer_repo = None

    if config.supabase_url and config.supabase_anon_key:
        from app.auth.supabase_adapter import SupabaseAuthClient

        auth_client = SupabaseAuthClient.from_url_key(config.supabase_url, config.supabase_anon_key)

    if config.supabase_url and config.supabase_service_role_key:
        from app.api.supabase_repository import SupabaseTrainerAuthRepository

        trainer_repo = SupabaseTrainerAuthRepository.from_url_key(
            config.supabase_url,
            config.supabase_service_role_key,
        )

    auth_bridge = None
    if auth_client is not None and trainer_repo is not None and config.auth_pin_pepper:
        auth_bridge = PinAuthBridge(trainers=trainer_repo, auth=auth_client, pepper=config.auth_pin_pepper)

    return ApiContainer(
        auth_bridge=auth_bridge,
        session_refresher=auth_client,
        token_verifier=auth_client,
        trainer_repository=trainer_repo,
        principal_repository=trainer_repo,
        rate_limiter=rate_limiter,
    )
