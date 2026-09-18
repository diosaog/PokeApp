from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.auth.identifiers import canonical_trainer_uuid


@dataclass(frozen=True)
class TrainerAuthIdentity:
    id: str
    display_name: str
    slug: str
    globally_enabled: bool = True
    auth_user_id: str | None = None
    is_admin: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", canonical_trainer_uuid(self.id))
        if self.auth_user_id:
            object.__setattr__(self, "auth_user_id", canonical_trainer_uuid(self.auth_user_id))


@dataclass(frozen=True)
class InternalAuthCredential:
    trainer_id: str
    email: str
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "trainer_id", canonical_trainer_uuid(self.trainer_id))


@dataclass(frozen=True)
class SupabaseAuthSession:
    user_id: str
    access_token: str = field(repr=False)
    refresh_token: str = field(default="", repr=False)
    expires_at: int | None = None
    expires_in: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", canonical_trainer_uuid(self.user_id))

    def to_public_dict(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "expires_in": self.expires_in,
        }


@dataclass(frozen=True)
class SupabaseAuthUser:
    user_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", canonical_trainer_uuid(self.user_id))


@dataclass(frozen=True)
class PinAuthResult:
    trainer_id: str
    auth_user_id: str
    session: SupabaseAuthSession

    def __post_init__(self) -> None:
        object.__setattr__(self, "trainer_id", canonical_trainer_uuid(self.trainer_id))
        object.__setattr__(self, "auth_user_id", canonical_trainer_uuid(self.auth_user_id))

    def to_public_dict(self) -> dict[str, object]:
        return {
            "trainer_id": self.trainer_id,
            "auth_user_id": self.auth_user_id,
            "session": self.session.to_public_dict(),
        }


class AuthProvisioningStatus(str, Enum):
    PROVISIONED = "provisioned"
    ALREADY_PROVISIONED = "already_provisioned"


@dataclass(frozen=True)
class AuthProvisioningResult:
    status: AuthProvisioningStatus
    trainer_id: str
    auth_user_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "trainer_id", canonical_trainer_uuid(self.trainer_id))
        object.__setattr__(self, "auth_user_id", canonical_trainer_uuid(self.auth_user_id))
