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
