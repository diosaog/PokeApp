from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
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

    def __post_init__(self):
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or (parsed.scheme == 'http' and not local) or parsed.path
                    or parsed.query or parsed.fragment or parsed.username or parsed.password
                    or '*' in origin):
                raise ValueError('CORS requires explicit HTTPS origins (HTTP only for localhost).')

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "APIConfig":
        source = os.environ if environ is None else environ
        return cls(
            supabase_url=_first(source, "POKEAPP_V2_SUPABASE_URL", "SUPABASE_URL"),
            supabase_anon_key=_first(source, "POKEAPP_V2_SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY"),
            supabase_service_role_key=_first(
                source,
                "POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY",
                "SUPABASE_SERVICE_ROLE_KEY",
            ),
            auth_pin_pepper=_first(source, AUTH_PIN_PEPPER_ENV),
            pin_login_limit=_int_value(source, "POKEAPP_API_PIN_LOGIN_LIMIT", 8),
            pin_login_window_seconds=_int_value(source, "POKEAPP_API_PIN_LOGIN_WINDOW_SECONDS", 300),
            cors_origins=tuple(x.strip() for x in source.get('POKEAPP_API_CORS_ORIGINS', '').split(',') if x.strip()),
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
