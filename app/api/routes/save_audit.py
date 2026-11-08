"""Administración › Avisos (migration 084): informative notices, administrator only.

Every command needs an administrator; a status change also carries an
Idempotency-Key whose request hash binds it to this exact change, and the
database keeps the history. Nothing here can touch a save, the points or any
trainer: a notice is a suspicion for the administrator to judge.
"""

import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import ValidationError

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.save_audit_models import (
    NoticeStatusBody,
    SaveAuditNotice,
    SaveAuditOverview,
    SaveAuditRunResult,
    SaveAuditSummary,
)
from app.api.security import require_admin_principal
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix="/v1/admin/seasons/{season_id}/notices", tags=["admin"])
Admin = Annotated[AuthenticatedPrincipal, Depends(require_admin_principal)]
Container = Annotated[ApiContainer, Depends(get_api_container)]
Operation = Annotated[UUID, Header(alias="Idempotency-Key")]


def digest(season_id, notice_id, body):
    canonical = json.dumps(
        {"season": str(season_id), "notice": str(notice_id), **body},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _call(container, action):
    repository = getattr(container, "save_audit_repository", None)
    if repository is None:
        raise api_error(503, "NOTICES_UNAVAILABLE", "Los avisos no están disponibles.")
    try:
        return action(repository)
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Operación de avisos rechazada.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(503, "NOTICES_UNAVAILABLE", "Los avisos no están disponibles.") from exc


@router.get("", response_model=SaveAuditOverview)
def overview(season_id: UUID, principal: Admin, container: Container):
    def read(repository):
        result = SaveAuditOverview.model_validate(
            repository.read(str(principal.trainer_id), str(season_id))
        )
        if result.season_id != season_id:
            raise ValueError("Notice read scope mismatch")
        return result

    return _call(container, read)


@router.get("/summary", response_model=SaveAuditSummary)
def summary(season_id: UUID, principal: Admin, container: Container):
    return _call(
        container,
        lambda repository: SaveAuditSummary.model_validate(
            repository.summary(str(principal.trainer_id), str(season_id))
        ),
    )


@router.post("/analyze", response_model=SaveAuditRunResult)
def analyze_pending(season_id: UUID, principal: Admin, container: Container):
    audit = getattr(container, "save_audit", None)
    if audit is None:
        raise api_error(503, "NOTICES_UNAVAILABLE", "El análisis no está disponible.")

    def run(repository):
        outcome = audit.run(str(season_id))
        pending = repository.read(str(principal.trainer_id), str(season_id))["pending_saves"]
        return SaveAuditRunResult.model_validate(outcome | {"pending_saves": pending})

    return _call(container, run)


@router.post("/{notice_id}/status", response_model=SaveAuditNotice)
def update_status(
    season_id: UUID,
    notice_id: UUID,
    payload: NoticeStatusBody,
    operation: Operation,
    principal: Admin,
    container: Container,
):
    body = payload.model_dump(mode="json")
    return _call(
        container,
        lambda repository: SaveAuditNotice.model_validate(
            repository.update(
                str(principal.trainer_id),
                str(season_id),
                str(notice_id),
                payload.status,
                payload.note,
                str(operation),
                digest(season_id, notice_id, body),
            )
        ),
    )
