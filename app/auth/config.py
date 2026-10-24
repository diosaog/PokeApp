from __future__ import annotations

import os
from collections.abc import Mapping

from app.auth.errors import MissingAuthPepperError

AUTH_PIN_PEPPER_ENV = "POKEAPP_AUTH_PIN_PEPPER"


def auth_pin_pepper_from_env(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    pepper = str(source.get(AUTH_PIN_PEPPER_ENV, "") or "")
    if not pepper:
        raise MissingAuthPepperError()
    return pepper


def credential_keyring_from_env(environ: Mapping[str, str]):
    """Load SEC-PIN-01 configuration only from the explicitly supplied mapping.

    APIConfig invokes this when versioned settings are present. Partial/invalid
    configuration fails rather than reverting to an unversioned credential path.
    """
    from datetime import datetime

    from app.auth.keyring import CredentialKeyring, KeyringConfigurationError

    try:
        deadline = datetime.fromisoformat(environ["POKEAPP_AUTH_PIN_V1_DEADLINE"])
    except (KeyError, TypeError, ValueError):
        raise KeyringConfigurationError() from None
    return CredentialKeyring(
        legacy_deadline=deadline,
        v1_pepper=environ.get(AUTH_PIN_PEPPER_ENV),
        v2_pepper=environ.get("POKEAPP_AUTH_PIN_PEPPER_V2"),
        intent_key=environ.get("POKEAPP_ACCOUNT_INTENT_KEY_V2"),
        throttle_key=environ.get("POKEAPP_ACCOUNT_THROTTLE_KEY"),
    )
