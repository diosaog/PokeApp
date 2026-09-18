from __future__ import annotations

import uuid


def canonical_trainer_uuid(trainer_id: str | uuid.UUID) -> str:
    return str(uuid.UUID(str(trainer_id)))
