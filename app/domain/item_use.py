from dataclasses import dataclass
import re
from uuid import UUID

from app.domain.normal_purchases import validate_idempotency_key


@dataclass(frozen=True)
class ItemUsePrepareRequest:
    season_id: str
    trainer_id: str
    purchase_id: str
    pokemon_entity_id: str
    save_file_id: str
    save_sha256: str
    idempotency_key: str
    operation_id: str

    def __post_init__(self):
        for value in (
            self.season_id,
            self.trainer_id,
            self.purchase_id,
            self.pokemon_entity_id,
            self.save_file_id,
        ):
            UUID(value)
        if not isinstance(self.save_sha256, str) or not re.fullmatch(
            r"[a-f0-9]{64}", self.save_sha256
        ):
            raise ValueError("invalid_save_hash")
        validate_idempotency_key(self.idempotency_key)
        validate_idempotency_key(self.operation_id)
