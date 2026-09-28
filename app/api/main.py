from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer, create_default_container
from app.api.routes import auth, matchdays, participant_status, purchases, redemptions, season_admin, system, team_locks
from app.api.routes import season_lifecycle
from app.api.routes import trials
from app.api.routes import cups
from app.api.routes import reads


def create_app(
    *,
    container: ApiContainer | None = None,
    config: APIConfig | None = None,
) -> FastAPI:
    config = config or APIConfig.from_env()
    api = FastAPI(
        title="PokeApp API",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    api.state.api_container = container or create_default_container(config)

    @api.middleware('http')
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith('/v1/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
    if config.cors_origins:
        api.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origins),
            allow_credentials=False, allow_methods=['GET','POST','PUT','OPTIONS'],
            allow_headers=['Authorization','Content-Type','Idempotency-Key'], max_age=600)
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
    api.include_router(cups.router)
    api.include_router(reads.router)
    return api


app = create_app()
