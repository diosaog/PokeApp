from dataclasses import asdict, fields

from app.domain.redemptions import RedemptionReceipt, RedemptionRequest
from app.repositories.errors import PersistenceError, RedemptionRejectedError


REJECTIONS = {
    'trainer_disabled':403, 'participant_inactive':403,
    'season_not_found':404, 'purchase_not_found':404,
    'invalid_redemption_request':409, 'purchase_already_redeemed':409,
    'purchase_not_redeemable':409, 'idempotency_conflict':409,
    'redemption_not_supported':409, 'pokemon_not_owned':409,
    'pokemon_identity_ambiguous':409, 'pokemon_target_stale':409,
    'pokemon_not_revivable':409, 'pokemon_already_shielded':409,
    'invalid_pokemon_target':409,
}


class SupabaseRedemptionRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, service_role_key):
        from supabase import create_client
        return cls(create_client(url, service_role_key))

    def redeem_purchase(self, request: RedemptionRequest) -> RedemptionReceipt:
        try:
            # Only a server-observed version is sent. SQL rechecks it under the identity lock.
            rows = self._client.table('pokemon_identity_revisions').select('id').eq(
                'season_id', request.season_id).eq('trainer_id', request.trainer_id).order(
                'revision_number', desc=True).limit(1).execute().data
            args = {'p_' + key:value for key,value in asdict(request).items()}
            args['p_expected_revision_id'] = rows[0]['id'] if rows else None
            data = self._client.rpc('api_redeem_purchase', args).execute().data
        except Exception as exc:
            message = str(getattr(exc, 'message', ''))
            status = REJECTIONS.get(message)
            if status and str(getattr(exc, 'code', '')) == f'PT{status}':
                raise RedemptionRejectedError(message.upper(), status) from exc
            raise PersistenceError('Redemption backend unavailable.') from exc
        try:
            receipt = RedemptionReceipt(**{f.name:data[f.name] for f in fields(RedemptionReceipt)})
            if any(getattr(receipt, key) != getattr(request, key) for key in ('season_id','trainer_id','purchase_id')):
                raise ValueError('Receipt scope mismatch')
            if receipt.target_pokemon_entity_id != request.pokemon_entity_id:
                raise ValueError('Receipt target mismatch')
            return receipt
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise PersistenceError('Invalid redemption receipt.') from exc
