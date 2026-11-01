"""Portable native-intent DTOs shared by server verification and local writes."""
from dataclasses import dataclass
import json
import re
from uuid import NAMESPACE_URL, uuid5

GAMES = frozenset(("X", "Y", "OR", "AS", "SN", "MN", "US", "UM"))


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class WriteSafetyError(Exception):
    """A stable local code, never a pathname or native/parser diagnostic."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class WriteIntent:
    expected_sha256: str
    game: str
    trainer_key: str
    mutation: dict

    @classmethod
    def create(
        cls, *, expected_sha256: str, game: str, trainer_key: str, mutation: dict
    ):
        if (
            game not in GAMES
            or not re.fullmatch("[0-9a-f]{64}", expected_sha256)
            or not re.fullmatch("[0-9a-f]{64}", trainer_key)
            or not isinstance(mutation, dict)
        ):
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        # Deep-copy removes caller-owned mutable references from the authorized intent.
        clean = json.loads(_json(mutation))
        if len(_json(clean)) > 4096:
            raise WriteSafetyError("INVALID_WRITE_INTENT")
        return cls(expected_sha256, game, trainer_key, clean)

    def to_payload(self) -> dict:
        return {
            "expected_sha256": self.expected_sha256,
            "game": self.game,
            "trainer_key": self.trainer_key,
            "mutation": json.loads(_json(self.mutation)),
        }

    @property
    def operation_id(self) -> str:
        return str(
            uuid5(NAMESPACE_URL, "pokeapp-local-write/1:" + _json(self.to_payload()))
        )


@dataclass(frozen=True)
class PreparedNative:
    output: bytes
    game: str
    trainer_key: str
    source_hash: str
    output_hash: str
    semantic_diff: dict
    contract: dict
