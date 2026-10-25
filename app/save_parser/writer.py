"""Bounded bytes-only bridge to the pinned native writer; never opens a save."""

from __future__ import annotations

import base64
import binascii
import json
import subprocess
import threading
from hashlib import sha256
from pathlib import Path

from app.launcher.write_engine import PreparedNative, WriteIntent

WRITER_VERSION = "pokeapp-writer/1;pkhex/24.11.11"
NATIVE_SIZES = {
    "X": 415232,
    "Y": 415232,
    "OR": 483328,
    "AS": 483328,
    "SN": 441856,
    "MN": 441856,
    "US": 445440,
    "UM": 445440,
}
MAX_REQUEST = 2 * 1024 * 1024
MAX_RESPONSE = 1024 * 1024
MAX_STDERR = 16384
ERRORS = frozenset(
    {
        "INVALID_REQUEST",
        "UNSUPPORTED_FORMAT",
        "CORRUPT_SAVE",
        "STALE_SOURCE",
        "WRONG_GAME",
        "WRONG_TRAINER",
        "UNSAFE_TARGET",
        "STALE_MUTATION",
        "UNEXPECTED_DIFF",
        "VERIFICATION_FAILED",
        "WRITE_PREPARATION_FAILED",
    }
)
RESPONSE_KEYS = frozenset(
    {
        "schema_version",
        "writer_version",
        "status",
        "error",
        "game",
        "trainer_key",
        "source_sha256",
        "output_sha256",
        "output_base64",
        "semantic_diff",
    }
)


class NativeWriteError(Exception):
    """Sanitized failure only; child output and private bytes never escape."""

    def __init__(self, code="NATIVE_WRITER_FAILURE"):
        self.code = code if code in ERRORS else "NATIVE_WRITER_FAILURE"
        super().__init__(self.code)


def _strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_native_key")
        value[key] = item
    return value


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


class PkhexProcessWriter:
    """Local fixed executable, no shell, bounded pipes and hard child timeout."""

    version = WRITER_VERSION

    def validate_original(self, source: bytes, intent: WriteIntent) -> None:
        # Reuse the native read boundary; restore never runs a new mutation.
        from app.save_parser.adapter import PkhexProcessParser

        observed = PkhexProcessParser(self.executable).parse(source)
        trainer = observed.trainer
        key = _digest(
            "\0".join(
                (
                    observed.game,
                    trainer.name,
                    str(trainer.tid),
                    str(trainer.sid),
                    str(trainer.gender),
                    str(trainer.language),
                )
            ).encode()
        )
        if (
            _digest(source) != intent.expected_sha256
            or observed.game != intent.game
            or key != intent.trainer_key
        ):
            raise NativeWriteError("WRONG_TRAINER")

    def __init__(self, executable: Path, *, timeout: float = 30):
        self.executable = executable.resolve(strict=True)
        if not self.executable.is_file() or not 0 < timeout <= 120:
            raise ValueError("native_writer_executable_or_timeout_invalid")
        self.timeout = timeout

    def _run(self, mode: str, request: dict) -> dict:
        raw = json.dumps(request, ensure_ascii=True, separators=(",", ":")).encode()
        if len(raw) > MAX_REQUEST:
            raise NativeWriteError("INVALID_REQUEST")
        process = None
        threads = []
        output = bytearray()
        errors = []

        def abort():
            errors.append(True)
            if process is not None:
                try:
                    process.kill()
                except OSError:
                    pass

        def drain(stream, limit, destination=None):
            size = 0
            try:
                while chunk := stream.read(8192):
                    size += len(chunk)
                    if size > limit:
                        abort()
                        return
                    if destination is not None:
                        destination.extend(chunk)
            except OSError:
                abort()
            finally:
                stream.close()

        def send():
            try:
                process.stdin.write(raw)
                process.stdin.flush()
            except (OSError, ValueError):
                abort()
            finally:
                try:
                    process.stdin.close()
                except OSError:
                    pass

        try:
            process = subprocess.Popen(
                [str(self.executable), mode],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for target, arguments in (
                (drain, (process.stdout, MAX_RESPONSE, output)),
                (drain, (process.stderr, MAX_STDERR)),
                (send, ()),
            ):
                thread = threading.Thread(target=target, args=arguments, daemon=True)
                threads.append(thread)
                thread.start()
            process.wait(timeout=self.timeout)
            for thread in threads:
                thread.join(timeout=1)
            if errors or any(thread.is_alive() for thread in threads):
                raise NativeWriteError()
            # Rejections may use a nonzero exit; only an exact, sanitized failure
            # envelope is accepted below. Successful replies require exit zero.
            response = json.loads(output, object_pairs_hook=_strict_object)
            if (
                not isinstance(response, dict)
                or set(response) != RESPONSE_KEYS
                or type(response["schema_version"]) is not int
                or response["schema_version"] != 1
                or response["writer_version"] != self.version
            ):
                raise NativeWriteError()
            if response["status"] == "rejected":
                code = response["error"]
                if code not in ERRORS or any(
                    response[key] is not None
                    for key in RESPONSE_KEYS
                    - {"schema_version", "writer_version", "status", "error"}
                ):
                    raise NativeWriteError()
                raise NativeWriteError(code)
            if process.returncode != 0 or response["error"] is not None:
                raise NativeWriteError()
            return response
        except NativeWriteError:
            raise
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
            raise NativeWriteError() from None
        finally:
            if process is not None:
                if process.poll() is None:
                    try:
                        process.kill()
                    except OSError:
                        pass
                try:
                    process.wait(timeout=2)
                except (OSError, subprocess.SubprocessError):
                    pass
                for thread in threads:
                    thread.join(timeout=1)

    @staticmethod
    def _input(source: bytes, intent: WriteIntent) -> dict:
        if type(source) is not bytes or not isinstance(intent, WriteIntent):
            raise NativeWriteError("INVALID_REQUEST")
        payload = intent.to_payload()
        if len(source) != NATIVE_SIZES.get(payload["game"]):
            raise NativeWriteError("UNSUPPORTED_FORMAT")
        if _digest(source) != payload["expected_sha256"]:
            raise NativeWriteError("STALE_SOURCE")
        return {
            "schema_version": 1,
            "source_base64": base64.b64encode(source).decode("ascii"),
            "intent": payload,
        }

    @staticmethod
    def _validate(response, source, output, intent, status):
        payload = intent.to_payload()
        expected_diff = payload["mutation"] | {
            "preserved_unrelated": True,
            "checksums_valid": True,
            "signature_valid": True,
        }
        actual_diff = response["semantic_diff"]
        if (
            response["status"] != status
            or response["game"] != payload["game"]
            or response["trainer_key"] != payload["trainer_key"]
            or response["source_sha256"] != _digest(source)
            or response["output_sha256"] != _digest(output)
            or len(output) != len(source)
            or output == source
            or not isinstance(actual_diff, dict)
            or actual_diff != expected_diff
            or any(
                type(actual_diff.get(key)) is not type(value)
                for key, value in expected_diff.items()
            )
        ):
            raise NativeWriteError("VERIFICATION_FAILED")

    def plan_transfer(
        self,
        source,
        destination,
        *,
        pair_id,
        box_index,
        slot_index,
        target_pid,
        target_ec,
    ):
        """Private planner seam; never expose peer bytes or this plan as authority."""
        request = {
            "schema_version": 1,
            "source_base64": base64.b64encode(source).decode("ascii"),
            "destination_base64": base64.b64encode(destination).decode("ascii"),
            "pair_id": pair_id,
            "box_index": box_index,
            "slot_index": slot_index,
            "target_pid": target_pid,
            "target_ec": target_ec,
        }
        response = self._run("--plan-transfer", request)
        if response["status"] != "planned" or response["source_sha256"] != _digest(
            source
        ):
            raise NativeWriteError("VERIFICATION_FAILED")
        plans = {
            side: WriteIntent.create(**response["semantic_diff"][side])
            for side in ("source", "destination")
        }
        if plans["source"].expected_sha256 != _digest(source) or plans[
            "destination"
        ].expected_sha256 != _digest(destination):
            raise NativeWriteError("VERIFICATION_FAILED")
        return plans

    def prepare(self, source: bytes, intent: WriteIntent) -> PreparedNative:
        request = self._input(source, intent)
        response = self._run("--prepare-write", request)
        try:
            encoded = response["output_base64"]
            if not isinstance(encoded, str):
                raise ValueError("invalid_native_output")
            output = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError, binascii.Error):
            raise NativeWriteError("VERIFICATION_FAILED") from None
        self._validate(response, source, output, intent, "prepared")
        prepared = PreparedNative(
            output=output,
            game=response["game"],
            trainer_key=response["trainer_key"],
            source_hash=response["source_sha256"],
            output_hash=response["output_sha256"],
            semantic_diff=response["semantic_diff"],
            contract={"schema_version": 1, "writer_version": self.version},
        )
        self.verify(source, output, intent, prepared)
        return prepared

    def verify(
        self,
        original: bytes,
        persisted: bytes,
        intent: WriteIntent,
        prepared: PreparedNative,
    ) -> None:
        request = self._input(original, intent)
        if (
            type(persisted) is not bytes
            or not isinstance(prepared, PreparedNative)
            # Recovery reconstructs the receipt without duplicating candidate
            # bytes in the journal. The native verifier independently derives
            # and checks the mutation from the original backup in either case.
            or (prepared.output and prepared.output != persisted)
            or len(persisted) != len(original)
            or prepared.source_hash != _digest(original)
            or prepared.output_hash != _digest(persisted)
            or prepared.game != intent.game
            or prepared.trainer_key != intent.trainer_key
            or prepared.contract
            != {"schema_version": 1, "writer_version": self.version}
        ):
            raise NativeWriteError("VERIFICATION_FAILED")
        request["output_base64"] = base64.b64encode(persisted).decode("ascii")
        response = self._run("--verify-write", request)
        if response["output_base64"] is not None:
            raise NativeWriteError("VERIFICATION_FAILED")
        self._validate(response, original, persisted, intent, "verified")
        if response["semantic_diff"] != prepared.semantic_diff:
            raise NativeWriteError("VERIFICATION_FAILED")
