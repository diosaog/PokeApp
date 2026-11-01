"""Real native writer + NTFS journal, with a synthetic exactly-once server.

Only the eight exported synthetic NativeTraining checks fixtures are accepted.
Optionally executes the FINAL packaged Python bytecode instead of checkout code.
"""

import argparse
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--native", type=Path, required=True)
    cli.add_argument("--fixtures", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--packaged-core", type=Path)
    cli.add_argument("--trace-native", action="store_true", help="retain bounded native pipes for these synthetic fixtures")
    cli.add_argument("--diagnostic", action="store_true", help="record checks without treating this run as release acceptance")
    cli.add_argument("--case", action="append", choices=[f"{game}:{effect}" for game in
                     ("X", "Y", "OR", "AS", "SN", "MN", "US", "UM") for effect in ("mint", "silver", "gold")],
                     help="run only selected isolated handoffs; excludes the full recovery matrix")
    cli.add_argument("--repeat", type=int, default=1, help="fresh isolated copies per selected case (1-32)")
    args = cli.parse_args()
    if not 1 <= args.repeat <= 32 or args.repeat != 1 and not args.case:
        cli.error("--repeat must be 1-32 and repetitions require --case")
    output = args.out.resolve()
    if output.exists():
        raise ValueError("Use a fresh isolated evidence directory")
    output.mkdir(parents=True)
    report = {"status": "RUNNING", "checks": [], "packaged": bool(args.packaged_core),
              "acceptance_gate": not (args.diagnostic or args.case),
              "scope": "focused handoffs" if args.case else "full matrix",
              "native_files_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in
                  (args.native, args.native.with_suffix(".dll"), args.native.parent / "PKHeX.Core.dll") if p.is_file()}}
    if args.packaged_core:
        from tools.validate_shop_delivery_package import PackagedApplication, portable_code
        importer = PackagedApplication(args.packaged_core)
        for name in ("app.launcher.training", "app.launcher.write_engine", "app.launcher.write_files",
                     "app.launcher.write_control", "app.launcher.runtime", "app.save_parser.writer", "app.save_parser.write_models"):
            source = Path(__file__).resolve().parents[1] / (name.replace(".", "/") + ".py")
            assert portable_code(importer.archive.extract(name)) == portable_code(compile(source.read_bytes(), str(source), "exec")), name
        sys.meta_path.insert(0, importer)
    if args.trace_native:
        trace = output / "native-trace"
        trace.mkdir()
        original_popen = subprocess.Popen
        counter = 0

        class Tee:
            def __init__(self, stream, file, limit):
                self.stream, self.sink, self.remaining = stream, file.open("wb"), limit

            def capture(self, data):
                self.sink.write(data[:self.remaining])
                self.remaining = max(0, self.remaining - len(data))
                self.sink.flush()

            def read(self, *values):
                data = self.stream.read(*values)
                self.capture(data)
                return data

            def write(self, data):
                size = self.stream.write(data)
                self.capture(data[:size])
                return size

            def close(self):
                try:
                    self.stream.close()
                finally:
                    self.sink.close()

            def __getattr__(self, name):
                return getattr(self.stream, name)

        def traced_popen(command, *values, **options):
            nonlocal counter
            counter += 1
            mode = command[1].lstrip("-") if len(command) > 1 else "read-save"
            prefix = f"{counter:05d}-{mode}"
            if os.environ.get("DOTNET_EnableEventPipe") == "1":
                # PIDs can be reused: bind each trace to its unique invocation.
                environment = dict(options.get("env") or os.environ)
                environment["DOTNET_EventPipeOutputPath"] = str(trace / (prefix + ".nettrace"))
                options["env"] = environment
            child = original_popen(command, *values, **options)
            (trace / (prefix + ".process.json")).write_text(json.dumps(
                {"pid": child.pid, "command": command}), encoding="utf8")
            for name, extension, limit in (("stdin", "request.json", 2 * 1024 * 1024),
                                           ("stdout", "response.json", 4 * 1024 * 1024),
                                           ("stderr", "stderr.txt", 16384)):
                stream = getattr(child, name)
                if stream is not None:
                    setattr(child, name, Tee(stream, trace / (prefix + "." + extension), limit))
            return child

        # Preserve the packaged adapter's own framing, limits and validation;
        # tee only the actual process pipes, never substitute native responses.
        subprocess.Popen = traced_popen
    from app.launcher.backend import BackendError
    from app.launcher.training import LauncherTraining
    from app.launcher.save_activity import SaveActivityGate
    from app.launcher.write_control import LocalWriteController
    from app.launcher.write_engine import LocalWriteEngine, PairedApplyPermit, WriteIntent
    from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
    from app.save_parser.writer import PkhexProcessWriter

    failure_sequence = 0

    class RecordedWriter(PkhexProcessWriter):
        """Keep real validation intact; retain the lost AS failure boundary."""
        def _run(self, mode, request):
            nonlocal failure_sequence
            self.proof_stage = "native_process:" + mode
            try:
                response = super()._run(mode, request)
            except Exception as error:
                if args.trace_native:
                    failure_sequence += 1
                    (output / f"native-process-failure-{failure_sequence:03d}.json").write_text(
                        json.dumps(dict(stage=self.proof_stage, error_type=type(error).__name__,
                            error_code=getattr(error, "code", None), intent=request.get("intent")), indent=2), encoding="utf8")
                raise
            self.proof_response = {k: v for k, v in response.items() if k != "output_base64"}
            return response

        def _validate(self, response, source, output, intent, status):
            self.proof_stage = "response_contract"
            super()._validate(response, source, output, intent, status)
            self.proof_stage = "semantic_proof"

        def verify(self, original, persisted, intent, prepared):
            nonlocal failure_sequence
            self.proof_stage, self.proof_response = "preflight", None
            try:
                return super().verify(original, persisted, intent, prepared)
            except Exception as error:
                if args.trace_native:
                    failure_sequence += 1
                    detail = dict(stage=self.proof_stage, error_type=type(error).__name__,
                        error_code=getattr(error, "code", None), intent=intent.to_payload(),
                        source_sha256=sha256(original).hexdigest(), persisted_sha256=sha256(persisted).hexdigest(),
                        prepared_source_sha256=prepared.source_hash, prepared_output_sha256=prepared.output_hash,
                        prepared_contract=prepared.contract, prepared_semantic_diff=prepared.semantic_diff,
                        native_response=self.proof_response)
                    (output / f"verification-failure-{failure_sequence:03d}.json").write_text(
                        json.dumps(detail, indent=2), encoding="utf8")
                raise

    def check(ok, label):
        if not ok:
            raise AssertionError(label)
        report["checks"].append(label)
        print("PASS " + label, flush=True)

    class Server:
        def __init__(self, source, template):
            self.sid, self.tid, self.purchase, self.entity = (str(uuid4()) for _ in range(4))
            self.source, self.template = source, template
            self.operations, self.consumed, self.lost_reserve, self.lost_complete = {}, 0, False, False
            self.writer = RecordedWriter(args.native)

        def reserve(self, op, request):
            if self.consumed:
                raise BackendError("OBSERVATION_REJECTED", status=409, detail="PURCHASE_NOT_REDEEMABLE")
            assert request["purchase_id"] == self.purchase and request["pokemon_entity_id"] == self.entity
            assert request["source_sha256"] == sha256(self.source).hexdigest()
            bound = json.loads(json.dumps(self.template))
            bound["mutation"]["attempt"] = op
            row = dict(operation_id=op, season_id=self.sid, trainer_id=self.tid, purchase_id=self.purchase,
                       pokemon_entity_id=self.entity, status="RESERVED", intent=bound)
            self.operations[op] = row
            if self.lost_reserve:
                self.lost_reserve = False
                raise BackendError("BACKEND_UNAVAILABLE")
            return dict(row)

        def release(self, op):
            row = self.operations.get(op)
            if row is None:
                return None
            assert row["status"] != "APPLIED", "cannot release after consumption"
            row["status"] = "RELEASED"
            return dict(row)

        def complete(self, op, data):
            row = self.operations[op]
            intent = WriteIntent.create(**row["intent"])
            prepared = self.writer.prepare(self.source, intent)
            self.writer.verify(self.source, data, intent, prepared)
            if row["status"] != "APPLIED":
                assert row["status"] == "RESERVED"
                self.consumed += 1
                row["status"] = "APPLIED"
            if self.lost_complete:
                self.lost_complete = False
                raise BackendError("BACKEND_UNAVAILABLE")
            return dict(row)

    def case(game, effect, suffix="", *, fault=None, processes=None):
        folder = args.fixtures / game / "party" / effect
        source = (folder / "source").read_bytes()
        request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        assert source == base64.b64decode(request["source_base64"], validate=True)
        template = request["intent"]
        assert template["game"] == game and template["expected_sha256"] == sha256(source).hexdigest()
        directory = output / (game + "-" + effect + suffix)
        directory.mkdir()
        target = directory / "main"
        target.write_bytes(source)
        engine = LocalWriteEngine(directory / "profile", RecordedWriter(args.native),
            files=WindowsWriteFiles(process_names=lambda: processes or []), fault_hook=fault)
        controller = LocalWriteController(SaveActivityGate(), lambda: str(target), engine)
        server = Server(source, template)
        flow = LauncherTraining(controller, server, trainer_id=server.tid)
        mutation = template["mutation"]
        change = {"kind": {"mint": "nature", "silver": "iv", "gold": "ivs"}[effect]}
        if effect == "mint":
            change["nature_id"] = mutation["nature_id"]
        elif effect == "silver":
            change["stat"] = mutation["stat"]
        payload = dict(purchase_id=server.purchase, pokemon_entity_id=server.entity,
                       source_sha256=template["expected_sha256"], change=change)
        return source, target, engine, controller, server, flow, payload

    try:
        selected = [tuple(item.split(":")) for item in args.case] if args.case else [
            (game, effect) for game in ("X", "Y", "OR", "AS", "SN", "MN", "US", "UM")
            for effect in ("mint", "silver", "gold")]
        for repetition in range(args.repeat):
            for game, effect in selected:
                suffix = f"-repeat-{repetition + 1:02d}" if args.case else ""
                source, target, engine, controller, server, flow, payload = case(game, effect, suffix)
                result = flow.apply(payload)
                check(result["status"] == "APPLIED" and server.consumed == 1, f"{game} {effect}: real journal + native write + independent result verification spends once")
                native_id = flow._records()[0]["native_id"]
                check(engine._backup_bytes(engine._load(native_id)) == source and not controller.gate.recovery_required,
                      f"{game} {effect}: independent original backup verified and sync released")
                before = target.read_bytes()
                try:
                    flow.apply({**payload, "source_sha256": sha256(before).hexdigest()})
                except BackendError:
                    pass
                else:
                    raise AssertionError("second click unexpectedly accepted")
                check(target.read_bytes() == before and server.consumed == 1, f"{game} {effect}: second click cannot edit/spend twice")

        if args.case:
            report["status"] = "PASS"
            return

        source, target, engine, controller, server, flow, payload = case("Y", "silver", "-lost-reserve")
        server.lost_reserve = True
        try:
            flow.apply(payload)
        except BackendError:
            pass
        check(target.read_bytes() == source and server.consumed == 0, "lost reservation response never writes")
        flow.settle()
        check(not flow.pending() and not controller.gate.recovery_required, "unwritten reservation is safely released on recovery")

        source, target, engine, controller, server, flow, payload = case("UM", "gold", "-lost-complete")
        server.lost_complete = True
        check(flow.apply(payload)["status"] == "PENDING" and controller.gate.recovery_required,
              "lost completion response keeps written item reserved and synchronization paused")
        restarted = LauncherTraining(controller, server, trainer_id=server.tid)
        restarted.settle()
        check(server.consumed == 1 and not restarted.pending() and not controller.gate.recovery_required,
              "completion replay resolves once without rewriting or double consumption")

        for game in ("Y", "SN"):
            def crash(point):
                if point == "after_publish":
                    raise RuntimeError("isolated power loss")
            source, target, engine, controller, server, flow, payload = case(game, "mint", "-crash", fault=crash)
            try:
                flow.apply(payload)
            except WriteSafetyError:
                pass
            check(server.consumed == 0 and flow.pending() and controller.gate.recovery_required,
                  f"{game} crash after publication does not release or consume uncertain purchase")
            fresh = LocalWriteEngine(engine.profile, RecordedWriter(args.native), files=WindowsWriteFiles(process_names=lambda: []))
            recovered_controller = LocalWriteController(SaveActivityGate(), lambda: str(target), fresh)
            recovered_controller.reconcile()
            recovered = LauncherTraining(recovered_controller, server, trainer_id=server.tid)
            recovered.settle()
            check(server.consumed == 1 and not recovered.pending() and not recovered_controller.gate.recovery_required,
                  f"{game} fresh process reconciles native result and consumes once")

        source, target, engine, controller, server, flow, payload = case("AS", "silver", "-emulator", processes=["Azahar.exe"])
        try:
            flow.apply(payload)
        except WriteSafetyError as error:
            check(error.code == "EMULATOR_RUNNING" and target.read_bytes() == source and server.consumed == 0 and not flow.pending(),
                  "open emulator refuses write and releases purchase")
        else:
            raise AssertionError("emulator write accepted")
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=type(error).__name__ + ":" + str(error))
        raise
    finally:
        (output / "acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
