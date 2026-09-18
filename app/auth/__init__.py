from __future__ import annotations

from app.auth.config import AUTH_PIN_PEPPER_ENV, auth_pin_pepper_from_env
from app.auth.credentials import (
    build_internal_auth_credential,
    derive_supabase_password,
    synthetic_auth_email,
)
from app.auth.models import (
    AuthProvisioningResult,
    AuthProvisioningStatus,
    InternalAuthCredential,
    PinAuthResult,
    SupabaseAuthSession,
    SupabaseAuthUser,
    TrainerAuthIdentity,
)
from app.auth.service import PinAuthBridge, TrainerAuthProvisioner

__all__ = [
    "AuthProvisioningResult",
    "AuthProvisioningStatus",
    "InternalAuthCredential",
    "PinAuthBridge",
    "PinAuthResult",
    "SupabaseAuthSession",
    "SupabaseAuthUser",
    "TrainerAuthIdentity",
    "TrainerAuthProvisioner",
    "AUTH_PIN_PEPPER_ENV",
    "auth_pin_pepper_from_env",
    "build_internal_auth_credential",
    "derive_supabase_password",
    "synthetic_auth_email",
]
