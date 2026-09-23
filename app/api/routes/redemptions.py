from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.api.models import AuthenticatedPrincipal
from app.api.routes.purchases import IdempotencyHeader
from app.api.schemas import RedemptionBody, RedemptionResponse
from app.api.security import require_enabled_principal
from app.application.redemptions import redeem_purchase_v2
from app.repositories.errors import PersistenceError, RedemptionRejectedError


router = APIRouter(prefix='/v1/seasons', tags=['redemptions'])


@router.post('/{season_id}/shop/purchases/{purchase_id}/redemptions', response_model=RedemptionResponse)
def post_redemption(
    season_id: UUID, purchase_id: UUID, payload: RedemptionBody, idempotency_key: IdempotencyHeader,
    principal: AuthenticatedPrincipal = Depends(require_enabled_principal),
    container: ApiContainer = Depends(get_api_container),
) -> RedemptionResponse:
    if container.redemption_repository is None:
        raise api_error(503, 'REDEMPTION_UNAVAILABLE', 'Redemption backend is unavailable.')
    try:
        receipt = redeem_purchase_v2(container.redemption_repository, season_id=str(season_id),
            trainer_id=principal.trainer_id, purchase_id=str(purchase_id),
            pokemon_entity_id=str(payload.pokemon_entity_id), idempotency_key=idempotency_key)
    except RedemptionRejectedError as exc:
        raise api_error(exc.status, exc.code, 'Redemption cannot be completed in the current state.') from exc
    except PersistenceError as exc:
        raise api_error(503, 'REDEMPTION_UNAVAILABLE', 'Redemption backend is unavailable.') from exc
    return RedemptionResponse.model_validate(receipt, from_attributes=True)
