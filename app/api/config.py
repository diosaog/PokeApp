from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.auth.config import AUTH_PIN_PEPPER_ENV


@dataclass(frozen=True)
class APIConfig:
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    auth_pin_pepper: str = ""
    pin_login_limit: int = 8
    pin_login_window_seconds: int = 300
    cors_origins: tuple[str, ...] = ()
    account_management_enabled: bool = False
    item_verification_transport_enabled: bool = False
    item_verification_trainers: tuple[str, ...] = ()
    transfer_engineering_enabled: bool = False
    transfer_engineering_trainers: tuple[str, ...] = ()
    # Phase 28: only after migration 062 is applied to that database.
    admin_incidents_enabled: bool = False
    # «Aaron Avisa!»: the URL carries the webhook token; server secret only.
    discord_webhook_url: str = field(default="", repr=False)
    registration_access_code: str = field(default="", repr=False)
    registration_bootstrap_hash: str = field(default="", repr=False)
    credential_keyring: object | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.item_verification_transport_enabled:
            from uuid import UUID

            if not self.item_verification_trainers or any(
                str(UUID(t)) != t for t in self.item_verification_trainers
            ):
                raise ValueError(
                    "Restricted verifier acceptance needs exact trainer UUIDs"
                )
        if self.transfer_engineering_enabled:
            from uuid import UUID

            if not self.transfer_engineering_trainers or any(
                str(UUID(t)) != t for t in self.transfer_engineering_trainers
            ):
                raise ValueError(
                    "Engineering transfers need an exact trainer UUID cohort"
                )
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or (parsed.scheme == "http" and not local)
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or "*" in origin
            ):
                raise ValueError(
                    "CORS requires explicit HTTPS origins (HTTP only for localhost)."
                )

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "APIConfig":
        source = os.environ if environ is None else environ
        from app.auth.config import credential_keyring_from_env

        versioned = any(
            source.get(k)
            for k in (
                "POKEAPP_AUTH_PIN_PEPPER_V2",
                "POKEAPP_ACCOUNT_INTENT_KEY_V2",
                "POKEAPP_ACCOUNT_THROTTLE_KEY",
                "POKEAPP_AUTH_PIN_V1_DEADLINE",
            )
        )
        return cls(
            item_verification_transport_enabled=source.get(
                "POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED"
            )
            == "true",
            item_verification_trainers=tuple(
                t.strip()
                for t in source.get("POKEAPP_ITEM_VERIFICATION_TRAINERS", "").split(",")
                if t.strip()
            ),
            transfer_engineering_enabled=source.get(
                "POKEAPP_TRANSFER_ENGINEERING_ENABLED"
            )
            == "true",
            admin_incidents_enabled=source.get("POKEAPP_ADMIN_INCIDENTS_ENABLED")
            == "true",
            transfer_engineering_trainers=tuple(
                t.strip()
                for t in source.get("POKEAPP_TRANSFER_ENGINEERING_TRAINERS", "").split(
                    ","
                )
                if t.strip()
            ),
            credential_keyring=credential_keyring_from_env(source)
            if versioned
            else None,
            discord_webhook_url=source.get("POKEAPP_DISCORD_WEBHOOK_URL", "").strip(),
            registration_access_code=source.get("POKEAPP_REGISTRATION_ACCESS_CODE", ""),
            registration_bootstrap_hash=source.get(
                "POKEAPP_REGISTRATION_BOOTSTRAP_HASH", ""
            ),
            supabase_url=_first(source, "POKEAPP_V2_SUPABASE_URL", "SUPABASE_URL"),
            supabase_anon_key=_first(
                source, "POKEAPP_V2_SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY"
            ),
            supabase_service_role_key=_first(
                source,
                "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY",
                "SUPABASE_SERVICE_ROLE_KEY",
            ),
            auth_pin_pepper=_first(source, AUTH_PIN_PEPPER_ENV),
            account_management_enabled=source.get("POKEAPP_ACCOUNT_MANAGEMENT_ENABLED")
            == "true",
            pin_login_limit=_int_value(source, "POKEAPP_API_PIN_LOGIN_LIMIT", 8),
            pin_login_window_seconds=_int_value(
                source, "POKEAPP_API_PIN_LOGIN_WINDOW_SECONDS", 300
            ),
            cors_origins=tuple(
                x.strip()
                for x in source.get("POKEAPP_API_CORS_ORIGINS", "").split(",")
                if x.strip()
            ),
        )


def _first(source: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = source.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _int_value(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(str(raw))
    except ValueError:
        return default
    return value if value > 0 else default
