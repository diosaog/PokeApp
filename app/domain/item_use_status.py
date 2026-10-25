"""Current physical state, separate from immutable competitive receipt snapshots."""

from datetime import UTC, datetime


def physical_state(effect, authorization=None, *, used=False, now=None):
    if effect not in ("revive", "steal", "revivir_pokemon", "robar_pokemon"):
        return "NOT_REQUIRED"
    if authorization is None:
        return "LEGACY_PENDING" if used else "AVAILABLE"
    state = authorization.get("status")
    if state == "APPLIED_VERIFIED":
        return "APPLIED_VERIFIED"
    if state in ("RECOVERY_REQUIRED", "BLOCKED_UNCERTAIN", "FAILED_RECOVERABLE"):
        return state
    if state not in ("PREPARED", "PENDING_APPLICATION"):
        return "UNKNOWN"
    try:
        if datetime.fromisoformat(authorization["expires_at"]) <= (
            now or datetime.now(UTC)
        ):
            return "EXPIRED"
    except (KeyError, TypeError, ValueError):
        return "UNKNOWN"
    return state
