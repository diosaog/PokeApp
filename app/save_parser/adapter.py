"""Trusted, locally configured worker executable. Bytes in, neutral DTO out."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from pydantic import ValidationError

from app.save_parser.files import MAX_SAVE_BYTES, SaveSnapshot, SaveSource, SnapshotReader
from app.save_parser.models import ErrorCode, ObservedSave, ParserResponse, SaveError, SaveParser


class PkhexProcessParser:
    version = "pokeapp-reader/1;pkhex/24.11.11"

    def __init__(self, executable: Path, *, timeout: float = 20):
        self.executable = executable.resolve(strict=True)
        if not self.executable.is_file():
            raise ValueError("parser_executable_required")
        self.timeout = timeout

    def parse(self, data: bytes) -> ObservedSave:
        if not data:
            raise SaveError(ErrorCode.TRUNCATED_SAVE)
        if len(data) > MAX_SAVE_BYTES:
            raise SaveError(ErrorCode.UNSUPPORTED_VERSION)
        try:
            result = subprocess.run([str(self.executable)], input=data, capture_output=True,
                timeout=self.timeout, shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode != 0 or len(result.stdout) > 4 * 1024 * 1024:
                raise SaveError(ErrorCode.PARSER_FAILURE)
            parsed = ParserResponse.model_validate_json(result.stdout)
            if parsed.parser_version != self.version:
                raise SaveError(ErrorCode.UNSUPPORTED_VERSION)
            if parsed.error:
                raise SaveError(parsed.error)
            assert parsed.observation is not None
            return parsed.observation
        except (OSError, subprocess.SubprocessError, ValidationError, ValueError):
            raise SaveError(ErrorCode.PARSER_FAILURE) from None


@dataclass(frozen=True)
class ParseResult:
    snapshot: SaveSnapshot
    observation: ObservedSave
    parser_version: str


class SaveInspector:
    def __init__(self, parser: SaveParser, reader: SnapshotReader | None = None):
        self.parser, self.reader = parser, reader or SnapshotReader()

    def inspect(self, source: SaveSource, snapshot: SaveSnapshot | None = None) -> ParseResult:
        snapshot = snapshot or self.reader.read(source)
        try:
            observation = self.parser.parse(snapshot.data)
        except SaveError:
            raise
        except Exception:
            raise SaveError(ErrorCode.PARSER_FAILURE) from None
        self.reader.verify(snapshot)
        return ParseResult(snapshot, observation, self.parser.version)
