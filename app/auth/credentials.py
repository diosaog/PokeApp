from __future__ import annotations

import base64
import hashlib
import hmac
import uuid

from app.auth.errors import MissingAuthPepperError
from app.auth.identifiers import canonical_trainer_uuid
from app.auth.models import InternalAuthCredential

AUTH_EMAIL_DOMAIN = "auth.pokeapp.invalid"
AUTH_HMAC_CONTEXT = "pokeapp-v2-auth"
PASSWORD_COMPLEXITY_PREFIX = "PokeAuth9!"


def _require_pepper(pepper: str) -> str:
    if not isinstance(pepper, str) or not pepper:
        raise MissingAuthPepperError()
    return pepper


def _encode_digest_letters_only(digest: bytes) -> str:
    encoded = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    return encoded.translate(str.maketrans({"2": "g", "3": "h", "4": "j", "5": "k", "6": "m", "7": "n"}))


def derive_supabase_password(trainer_id: str, pin: str, pepper: str) -> str:
    if not isinstance(pin, str):
        raise TypeError("PIN must be provided as a string.")

    canonical_id = canonical_trainer_uuid(trainer_id)
    server_pepper = _require_pepper(pepper)
    message = f"{AUTH_HMAC_CONTEXT}:{canonical_id}:{pin}".encode("utf-8")
    digest = hmac.new(server_pepper.encode("utf-8"), message, hashlib.sha256).digest()
    return PASSWORD_COMPLEXITY_PREFIX + _encode_digest_letters_only(digest)


def synthetic_auth_email(trainer_id: str | uuid.UUID) -> str:
    return f"trainer-{canonical_trainer_uuid(trainer_id)}@{AUTH_EMAIL_DOMAIN}"


def build_internal_auth_credential(
    trainer_id: str,
    pin: str,
    pepper: str,
) -> InternalAuthCredential:
    canonical_id = canonical_trainer_uuid(trainer_id)
    return InternalAuthCredential(
        trainer_id=canonical_id,
        email=synthetic_auth_email(canonical_id),
        password=derive_supabase_password(canonical_id, pin, pepper),
    )
