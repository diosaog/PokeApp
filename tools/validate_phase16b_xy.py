"""Actual byte IPC -> local cache/outbox, using synthetic native fixtures only.

Run after PokeApp.Parser.Checks has built/exported the fixture directory. No SDK
build, PostgreSQL, production save, credentials or hosted API call in this runner.
"""
# ruff: noqa: E402 -- standalone runner adds repository root.

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.launcher.core import LauncherCore
from app.launcher.backup import PhysicalWritesDisabled
from app.launcher.discovery import FolderProvider
from app.launcher.cloud_store import CloudStore, deliver
from app.launcher.runtime import LauncherRuntime
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.cloud import CloudObservation
from app.save_parser.files import SaveSource
from app.save_parser.models import ErrorCode, SaveError


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--fixtures", type=Path, required=True)
    cli.add_argument("--evidence", type=Path, required=True)
    args = cli.parse_args()
    parser = PkhexProcessParser(
        ROOT / "companion/parser/PokeApp.Parser/bin/Release/net8.0/PokeApp.Parser.exe"
    )
    inspector = SaveInspector(parser)
    evidence = {
        "status": "PASS",
        "games": {},
        "old_generations": [],
        "remote_writes": 0,
    }
    for generation in (3, 4, 5):
        source = SaveSource.enroll(args.fixtures / f"gen{generation}.sav")
        original = source.path.read_bytes()
        obs = inspector.inspect(source).observation
        assert obs.generation == generation and len(obs.identity_observations()) == 2
        assert source.path.read_bytes() == original
        evidence["old_generations"].append(generation)
    for game in ("X", "Y"):
        source = SaveSource.enroll(args.fixtures / "xy" / game / "main")
        original = source.path.read_bytes()
        assert source.path in [
            candidate.path
            for candidate in FolderProvider(source.path.parent).candidates()
        ]
        samples, values = [], []
        for _ in range(5):
            start = time.perf_counter()
            parsed = inspector.inspect(source)
            samples.append((time.perf_counter() - start) * 1000)
            values.append(parsed.observation.model_dump_json())
        assert len(set(values)) == 1
        obs = parsed.observation
        assert obs.game == game and obs.generation == 6 and len(obs.boxes) == 31
        assert (
            obs.party[5].species_id == 655 and obs.boxes[30].slots[29].species_id == 657
        )
        assert obs.progress is None
        with tempfile.TemporaryDirectory(
            prefix="profile-", dir=args.evidence
        ) as folder:
            profile = Path(folder)
            core = LauncherCore(profile, inspector)
            core.select(source.path)
            synced = core.manual_sync()
            assert synced.status == "SYNCED"
            assert core.manual_sync().status == "NO_CHANGE"
            local = core.journal.head(source)
            envelope = CloudObservation(
                fingerprint=local.fingerprint,
                parser_version=local.parser_version,
                observation=local.observation,
            )
            store = CloudStore(core.journal)
            tid, sid = (
                "11111111-1111-4111-8111-111111111111",
                "22222222-2222-4222-8222-222222222222",
            )
            origin = "https://fixture.invalid"
            oid = store.enqueue(origin, tid, sid, envelope)
            assert store.enqueue(origin, tid, sid, envelope) == oid
            row = store.pending(origin, tid)
            calls = []
            accepted = dict(
                id=oid,
                trainer_id=tid,
                season_id=sid,
                payload_digest=envelope.digest(),
                received_at="2026-10-13T12:00:00Z",
                trust="client_observed",
                competitive_authority=False,
            )

            class LostReply:
                def request(self, method, path, **kwargs):
                    calls.append(method)
                    if method == "GET":
                        return None
                    assert kwargs["body"] == envelope.model_dump(mode="json")
                    raise TimeoutError("synthetic lost reply")

            try:
                deliver(LostReply(), store, row)
                raise AssertionError("lost reply not exercised")
            except TimeoutError:
                pass
            restarted = LauncherCore(profile, inspector)
            store = CloudStore(restarted.journal)
            assert restarted.journal.head(source) == local

            class ReceiptOnly:
                def request(self, method, path, **kwargs):
                    calls.append(method)
                    assert method == "GET"
                    return accepted

            deliver(ReceiptOnly(), store, store.pending(origin, tid))
            assert calls == ["GET", "PUT", "GET"] and store.pending(origin, tid) is None
            runtime = LauncherRuntime(profile, inspector, start=False)
            try:
                cached = runtime.state()
                assert cached["local_status"] == "CACHED" and cached[
                    "observation"
                ] == obs.model_dump(mode="json")
                assert cached["cloud_status"] == "OFFLINE"
            finally:
                runtime.close()
            # A corrupt candidate may neither replace the local head nor enqueue.
            bad = profile / "main"
            bad.write_bytes(original[:1024])
            restarted.select(bad)
            assert restarted.manual_sync().status == "INVALID"
            assert restarted.journal.head(SaveSource.enroll(bad)) is None
            assert store.pending(origin, tid) is None
            try:
                restarted.backups.apply(None, source)
                raise AssertionError("physical write unexpectedly supported")
            except PhysicalWritesDisabled as error:
                assert str(error) == "PHYSICAL_WRITES_DISABLED"

            # File changes after parsing still fail the stable-read gate.
            class RacingParser:
                version = parser.version

                def parse(self, data):
                    parsed = parser.parse(data)
                    bad.write_bytes(b"changed synthetic fixture")
                    return parsed

            bad.write_bytes(original)
            try:
                SaveInspector(RacingParser()).inspect(SaveSource.enroll(bad))
                raise AssertionError("unstable save accepted")
            except SaveError as error:
                assert error.code == ErrorCode.SAVE_CHANGED_DURING_READ
        assert source.path.read_bytes() == original
        evidence["games"][game] = dict(
            parse_ms=samples,
            median_parse_ms=statistics.median(samples),
            source_sha256=hashlib.sha256(original).hexdigest(),
            source_unchanged=True,
            party_slots=6,
            box_count=31,
            cloud_bytes=len(envelope.model_dump_json().encode()),
            cache_restart=True,
            lost_reply_calls=calls,
            corrupt_not_queued=True,
            physical_write_denied=True,
            stable_read_guard=True,
        )
    (args.evidence / "native-integration.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
