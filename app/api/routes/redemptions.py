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
from app.domain.item_use_status import physical_state


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
    result = RedemptionResponse.model_validate(receipt, from_attributes=True)
    current = None
    if receipt.effect_code in ('revive','steal') and container.item_use_repository is not None:
        try:
            current = next((a for a in container.item_use_repository.list(str(season_id), principal.trainer_id)
                            if a['purchase_id'] == str(purchase_id)), None)
        except PersistenceError:
            return result.model_copy(update={'physical_state':'UNKNOWN'})
    state = physical_state(receipt.effect_code, current, used=True)
    if receipt.effect_code in ('revive','steal') and container.item_use_repository is None:
        state = 'UNKNOWN'
    return result.model_copy(update={'physical_state':state})
