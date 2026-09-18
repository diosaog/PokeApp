from __future__ import annotations

from dataclasses import dataclass

from app.auth.models import TrainerAuthIdentity


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    trainer_id: str
    display_name: str
    is_admin: bool
    globally_enabled: bool

    @classmethod
    def from_trainer(cls, trainer: TrainerAuthIdentity) -> "AuthenticatedPrincipal":
        return cls(
            trainer_id=trainer.id,
            display_name=trainer.display_name or trainer.slug or trainer.id,
            is_admin=bool(trainer.is_admin),
            globally_enabled=bool(trainer.globally_enabled),
        )
