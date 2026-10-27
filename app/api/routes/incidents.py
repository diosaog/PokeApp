"""Admin incident center: cancel or refund purchases, correct coins (Phase 28)
and cancel a still-reversible robbery (Phase 29, migration 064).

Off unless the deployment enables it after applying migration 062. Every
command needs an administrator, a reason and an Idempotency-Key (UUID); the
request hash binds that key to this exact command, and the database keeps the
receipt so a retry never repeats the effect.
"""

import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import ValidationError

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.incident_models import (
    CoinAdjustBody,
    IncidentOverview,
    IncidentReceipt,
    PurchaseResolveBody,
    RobberyCancelBody,
)
from app.api.models import AuthenticatedPrincipal
from app.api.security import require_admin_principal
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

router = APIRouter(prefix="/v1/admin/seasons/{season_id}/incidents", tags=["admin"])
Admin = Annotated[AuthenticatedPrincipal, Depends(require_admin_principal)]
Container = Annotated[ApiContainer, Depends(get_api_container)]
Operation = Annotated[UUID, Header(alias="Idempotency-Key")]


def digest(kind, season_id, target, body):
    canonical = json.dumps(
        {"kind": kind, "season": str(season_id), "target": str(target), **body},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _call(container, action):
    repository = getattr(container, "incident_repository", None)
    if repository is None:
        raise api_error(
            503, "INCIDENTS_UNAVAILABLE", "The incident center is not enabled."
        )
    try:
        return action(repository)
    except SeasonAdminRejected as exc:
        raise api_error(exc.status, exc.code, "Incident operation rejected.") from exc
    except (PersistenceError, ValidationError, ValueError, TypeError) as exc:
        raise api_error(
            503, "INCIDENTS_UNAVAILABLE", "The incident center is unavailable."
        ) from exc


def _receipt(
    raw, *, season_id, operation, kind, trainer=None, purchase=None, authorization=None
):
    receipt = IncidentReceipt.model_validate(raw)
    if (
        receipt.season_id != season_id
        or receipt.operation_id != operation
        or receipt.kind != kind
        or (trainer is not None and receipt.trainer_id != trainer)
        or (purchase is not None and receipt.purchase_id != purchase)
        or (authorization is not None and receipt.authorization_id != authorization)
    ):
        raise ValueError("Incident receipt scope mismatch")
    return receipt


@router.get("", response_model=IncidentOverview)
def overview(season_id: UUID, principal: Admin, container: Container):
    def read(repository):
        result = IncidentOverview.model_validate(
            repository.read(str(principal.trainer_id), str(season_id))
        )
        if result.season_id != season_id:
            raise ValueError("Incident read scope mismatch")
        return result

    return _call(container, read)


@router.post("/purchases/{purchase_id}", response_model=IncidentReceipt)
def resolve_purchase(
    season_id: UUID,
    purchase_id: UUID,
    payload: PurchaseResolveBody,
    operation: Operation,
    principal: Admin,
    container: Container,
):
    kind = "purchase_cancel" if payload.action == "cancel" else "purchase_refund"
    body = payload.model_dump(mode="json")
    return _call(
        container,
        lambda repository: _receipt(
            repository.resolve_purchase(
                str(principal.trainer_id),
                str(season_id),
                str(purchase_id),
                kind,
                str(operation),
                digest(kind, season_id, purchase_id, body),
                payload.reason,
            ),
            season_id=season_id,
            operation=operation,
            kind=kind,
            purchase=purchase_id,
        ),
    )


@router.post("/robberies/{authorization_id}/cancel", response_model=IncidentReceipt)
def cancel_robbery(
    season_id: UUID,
    authorization_id: UUID,
    payload: RobberyCancelBody,
    operation: Operation,
    principal: Admin,
    container: Container,
):
    body = payload.model_dump(mode="json")
    return _call(
        container,
        lambda repository: _receipt(
            repository.cancel_robbery(
                str(principal.trainer_id),
                str(season_id),
                str(authorization_id),
                str(operation),
                digest("robbery_cancel", season_id, authorization_id, body),
                payload.reason,
            ),
            season_id=season_id,
            operation=operation,
            kind="robbery_cancel",
            authorization=authorization_id,
        ),
    )


@router.post("/coins", response_model=IncidentReceipt)
def adjust_coins(
    season_id: UUID,
    payload: CoinAdjustBody,
    operation: Operation,
    principal: Admin,
    container: Container,
):
    body = payload.model_dump(mode="json")
    return _call(
        container,
        lambda repository: _receipt(
            repository.adjust_coins(
                str(principal.trainer_id),
                str(season_id),
                str(payload.trainer_id),
                payload.amount,
                str(operation),
                digest("coin_adjustment", season_id, payload.trainer_id, body),
                payload.reason,
            ),
            season_id=season_id,
            operation=operation,
            kind="coin_adjustment",
            trainer=payload.trainer_id,
        ),
    )
