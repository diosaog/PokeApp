from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer, create_default_container
from app.api.routes import (
    auth,
    matchdays,
    participant_status,
    purchases,
    redemptions,
    season_admin,
    system,
    team_locks,
)
from app.api.routes import season_lifecycle
from app.api.routes import trials
from app.api.routes import cups
from app.api.routes import reads
from app.api.routes import initial_assignment
from app.api.routes import wipe_revivals
from app.api.routes import launcher
from app.api.routes import saves
from app.api.routes import personal_saves
from app.api.routes import accounts, incidents, item_delivery, item_use, transfers
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def create_app(
    *,
    container: ApiContainer | None = None,
    config: APIConfig | None = None,
) -> FastAPI:
    config = config or APIConfig.from_env()

    @asynccontextmanager
    async def lifespan(api):
        announcer = getattr(api.state.api_container, "announcer", None)
        if announcer is not None:
            announcer.start()
        try:
            yield
        finally:
            if announcer is not None:
                announcer.stop()

    api = FastAPI(
        title="PokeApp API",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    api.state.api_container = container or create_default_container(config)

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo malformed credential bodies (including unexpected fields).
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": e["loc"], "type": e["type"], "msg": "Invalid input."}
                    for e in exc.errors()
                ]
            },
        )

    @api.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @api.middleware("http")
    async def announce_confirmed_facts(request, call_next):
        # Confirmed facts queue their announcement in the same transaction;
        # this only wakes the delivery thread once the response is ready.
        response = await call_next(request)
        announcer = getattr(request.app.state.api_container, "announcer", None)
        if announcer is not None and request.url.path.startswith("/v1/"):
            announcer.kick(
                mutation=request.method not in ("GET", "HEAD", "OPTIONS")
                and response.status_code < 400
            )
        return response

    if config.cors_origins:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            max_age=600,
        )
    api.include_router(system.router)
    api.include_router(auth.router)
    api.include_router(auth.me_router)
    api.include_router(team_locks.router)
    api.include_router(purchases.router)
    api.include_router(redemptions.router)
    api.include_router(season_admin.router)
    api.include_router(matchdays.router)
    api.include_router(matchdays.participant_router)
    api.include_router(participant_status.router)
    api.include_router(season_lifecycle.router)
    api.include_router(season_lifecycle.participant_router)
    api.include_router(trials.router)
    api.include_router(cups.router)
    api.include_router(reads.router)
    api.include_router(initial_assignment.router)
    api.include_router(wipe_revivals.router)
    api.include_router(launcher.router)
    api.include_router(saves.router)
    api.include_router(personal_saves.router)
    api.include_router(personal_saves.public_router)
    api.include_router(accounts.router)
    api.include_router(item_use.router)
    api.include_router(item_delivery.router)
    api.include_router(transfers.router)
    api.include_router(incidents.router)
    return api


app = create_app()
