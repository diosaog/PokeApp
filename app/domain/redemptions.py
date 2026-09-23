from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.normal_purchases import validate_idempotency_key


@dataclass(frozen=True)
class RedemptionRequest:
    season_id: str
    trainer_id: str
    purchase_id: str
    pokemon_entity_id: str
    idempotency_key: str

    def __post_init__(self):
        for value in (self.season_id, self.trainer_id, self.purchase_id, self.pokemon_entity_id):
            UUID(value)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True)
class RedemptionReceipt:
    redemption_id: str
    purchase_id: str
    season_id: str
    trainer_id: str
    shop_item_id: str
    effect_code: str
    target_pokemon_entity_id: str
    target_owner_trainer_id: str
    purchase_status: str
    redemption_status: str
    physical_effect_status: str
    requested_at: str
    redeemed_at: str
    physical_effect_completed_at: None
    activity_event_id: str
    gift_purchase_id: None

    def __post_init__(self):
        for key in ('redemption_id','purchase_id','season_id','trainer_id','shop_item_id',
                    'target_pokemon_entity_id','target_owner_trainer_id','activity_event_id'):
            UUID(getattr(self, key))
        for value in (self.requested_at, self.redeemed_at):
            if datetime.fromisoformat(value).tzinfo is None:
                raise ValueError('invalid_redemption_date')
        if (self.purchase_status != 'used' or self.redemption_status != 'applied'
                or (self.effect_code, self.physical_effect_status) not in
                    (('shield','not_required'), ('revive','pending'))
                or self.physical_effect_completed_at is not None or self.gift_purchase_id is not None
                or self.target_owner_trainer_id != self.trainer_id):
            raise ValueError('invalid_redemption_receipt')
