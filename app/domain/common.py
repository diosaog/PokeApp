from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

TrainerId: TypeAlias = str
SeasonId: TypeAlias = str
SeasonVersionId: TypeAlias = str
DivisionId: TypeAlias = str
SeasonPlayerId: TypeAlias = str
MatchdayId: TypeAlias = str
MatchId: TypeAlias = str
PurchaseId: TypeAlias = str
RedemptionId: TypeAlias = str
SaveId: TypeAlias = str
TeamLockId: TypeAlias = str
ActivityEventId: TypeAlias = str
SeasonArchiveId: TypeAlias = str
HallOfFameEntryId: TypeAlias = str
CupId: TypeAlias = str
TrialId: TypeAlias = str
PokemonId: TypeAlias = str
ShopItemId: TypeAlias = str
ShopPromotionId: TypeAlias = str
UtcTimestamp: TypeAlias = str


class DomainValidationError(ValueError):
    """Raised when a contract receives structurally invalid data."""


class StringEnum(str, Enum):
    """Enum that serializes naturally to stable JSON strings."""

    def __str__(self) -> str:
        return str(self.value)


class Visibility(StringEnum):
    PUBLIC = "public"
    OWNER = "owner"
    ADMIN = "admin"
    SERVER_ONLY = "server_only"


class CompetitionType(StringEnum):
    LEAGUE = "league"
    CUP = "cup"
    TOURNAMENT = "tournament"
    DOUBLES_CUP = "doubles_cup"


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def require_id(value: str, field_name: str) -> str:
    out = clean_text(value)
    if not out:
        raise DomainValidationError(f"{field_name} must be a non-empty id.")
    return out


def optional_id(value: str | None) -> str:
    return clean_text(value)


def require_positive_int(value: int, field_name: str) -> int:
    try:
        out = int(value)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise DomainValidationError(f"{field_name} must be an integer.") from exc
    if out <= 0:
        raise DomainValidationError(f"{field_name} must be > 0.")
    return out


def require_non_negative_int(value: int, field_name: str) -> int:
    try:
        out = int(value)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise DomainValidationError(f"{field_name} must be an integer.") from exc
    if out < 0:
        raise DomainValidationError(f"{field_name} must be >= 0.")
    return out


def require_non_negative_float(value: float, field_name: str) -> float:
    try:
        out = float(value)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise DomainValidationError(f"{field_name} must be a number.") from exc
    if out < 0:
        raise DomainValidationError(f"{field_name} must be >= 0.")
    return out


def epoch_to_utc_iso(value: int | float | None) -> str:
    if value in (None, ""):
        return ""
    try:
        timestamp = float(value)
    except Exception:
        return ""
    if timestamp <= 0:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_json_object(value: Mapping[str, Any] | None) -> JsonObject:
    if not value:
        return {}
    return {
        str(key): to_jsonable(raw)
        for key, raw in value.items()
        if isinstance(key, str) and to_jsonable(raw) is not ...
    }


def enum_value(value: Any) -> JsonValue:
    if isinstance(value, Enum):
        return value.value
    return value


def to_jsonable(value: Any) -> JsonValue:
    """Convert domain contracts to JSON-safe builtins.

    This is intentionally small and dependency-free so the contracts remain
    usable by tests, scripts, future APIs and migration tooling.
    """

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        out: JsonObject = {}
        for item in fields(value):
            out[item.name] = to_jsonable(getattr(value, item.name))
        return out
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(raw) for key, raw in value.items()}
    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
