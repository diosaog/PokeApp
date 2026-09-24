from __future__ import annotations

from fastapi import FastAPI

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer, create_default_container
from app.api.routes import auth, matchdays, participant_status, purchases, redemptions, season_admin, system, team_locks
from app.api.routes import season_lifecycle
from app.api.routes import trials


def create_app(
    *,
    container: ApiContainer | None = None,
    config: APIConfig | None = None,
) -> FastAPI:
    api = FastAPI(
        title="PokeApp API",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    api.state.api_container = container or create_default_container(config)
    api.include_router(system.router)
    api.include_router(auth.router)
    api.include_router(auth.me_router)
    api.include_router(team_locks.router)
    api.include_router(purchases.router)
    api.include_router(redemptions.router)
    api.include_router(season_admin.router)
    api.include_router(matchdays.router)
    api.include_router(participant_status.router)
    api.include_router(season_lifecycle.router)
    api.include_router(trials.router)
    return api


app = create_app()
