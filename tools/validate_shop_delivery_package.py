"""Run paid delivery from the FINAL packaged Python bytecode and native worker.

Only a newly generated tools/make_launcher_fixture.ps1 fixture is admitted;
all writes, backups and journals live below a fresh private evidence directory.
The server is an in-memory receipt fixture, not a production account. No game
matrix is repeated: this joins the two shipped runtimes on real Windows files.
"""

import argparse
import importlib.abc
import importlib.util
import json
import os
import sys
from hashlib import sha256
from pathlib import Path
from types import CodeType
from uuid import uuid4

from PyInstaller.archive.readers import CArchiveReader

REPO = Path(__file__).resolve().parents[1]


class PackagedApplication(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, core):
        self.archive = CArchiveReader(str(core)).open_embedded_archive("PYZ.pyz")

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "app" or fullname.startswith("app."):
            if fullname not in self.archive.toc:
                raise ImportError(
                    f"Application module missing from package: {fullname}"
                )
            return importlib.util.spec_from_loader(
                fullname, self, is_package=self.archive.toc[fullname][0] == 1
            )
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = "packaged-core/" + module.__name__.replace(".", "/") + ".py"
        exec(self.archive.extract(module.__name__), module.__dict__)


def portable_code(code):
    return code.replace(
        co_filename="",
        co_consts=tuple(
            portable_code(value) if isinstance(value, CodeType) else value
            for value in code.co_consts
        ),
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--build", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    build, output = args.build.resolve(strict=True), args.out.resolve()
    if output.exists():
        raise ValueError("Use a fresh evidence directory")
    output.mkdir(parents=True)
    report = {"status": "RUNNING", "checks": [], "server": "in-memory only"}

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        report["checks"].append(label)
        print("PASS", label, flush=True)

    try:
        fixture = build / "synthetic-fixture/main"
        original = fixture.read_bytes()
        runtime = build / "release/win-unpacked/resources/runtime"
        importer = PackagedApplication(runtime / "core/PokeApp.Core.exe")
        for name in (
            "app.launcher.item_delivery",
            "app.launcher.runtime",
            "app.launcher.write_engine",
            "app.launcher.write_files",
            "app.launcher.write_control",
            "app.launcher.save_activity",
            "app.save_parser.writer",
            "app.domain.shop_item_uses",
        ):
            source = REPO / (name.replace(".", "/") + ".py")
            check(
                portable_code(importer.archive.extract(name))
                == portable_code(compile(source.read_bytes(), str(source), "exec")),
                name + " is bytecode-identical to final source",
            )
        if any(name == "app" or name.startswith("app.") for name in sys.modules):
            raise RuntimeError("Application already imported from outside package")
        sys.meta_path.insert(0, importer)
        from app.launcher.backend import BackendError
        from app.launcher.item_delivery import DeliveryRefused, LauncherDeliveries
        from app.launcher.save_activity import SaveActivityGate
        from app.launcher.write_control import LocalWriteController
        from app.launcher.write_engine import LocalWriteEngine
        from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
        from app.save_parser.adapter import PkhexProcessParser
        from app.save_parser.writer import PkhexProcessWriter

        # No SDK, installed runtime or Python executable on the native worker's
        # PATH: its own self-contained files must satisfy every dependency.
        os.environ["PATH"] = os.path.join(os.environ["SystemRoot"], "System32")
        os.environ["DOTNET_ROOT"] = str(output / "unavailable-dotnet")
        os.environ["DOTNET_MULTILEVEL_LOOKUP"] = "0"
        parser = runtime / "parser/PokeApp.Parser.exe"
        observation = PkhexProcessParser(parser).parse(original)
        check(
            observation.game == "X"
            and observation.trainer.name == "Package Test"
            and observation.trainer.tid == 54321
            and observation.trainer.sid == 12345,
            "synthetic fixture admitted; packaged parser runs without installed .NET",
        )
        native = PkhexProcessWriter(parser)
        initial = native.inventory(
            original, ("sitrus_berry", "leftovers", "bottle_cap")
        )
        target = output / "disposable-save"
        target.write_bytes(original)
        processes = []
        profile = output / "journal"

        class Server:
            sid = str(uuid4())

            def __init__(self):
                self.purchases, self.deliveries = {}, {}
                self.drop_completion = False
                self.authorized_trainer_key = initial["trainer_key"]

            def purchase(self):
                identifier = str(uuid4())
                self.purchases[identifier] = "pending"
                return identifier

            def receipt(self, operation):
                row = self.deliveries[operation]
                return dict(
                    row,
                    operation_id=operation,
                    purchase_status=self.purchases[row["purchase_id"]],
                    authorized_trainer_key=self.authorized_trainer_key,
                )

            def reserve(self, operation, purchase, item, game):
                if self.purchases[purchase] != "pending":
                    raise BackendError(
                        "OBSERVATION_REJECTED",
                        status=409,
                        detail="PURCHASE_NOT_REDEEMABLE",
                    )
                self.deliveries[operation] = {
                    "purchase_id": purchase,
                    "status": "RESERVED",
                }
                return self.receipt(operation)

            def complete(self, operation, source, result):
                row = self.deliveries[operation]
                assert source != result
                row["status"] = "DELIVERED"
                self.purchases[row["purchase_id"]] = "used"
                if self.drop_completion:
                    self.drop_completion = False
                    raise BackendError("BACKEND_UNAVAILABLE")
                return self.receipt(operation)

            def release(self, operation):
                row = self.deliveries[operation]
                assert row["status"] != "DELIVERED"
                row["status"] = "RELEASED"
                return self.receipt(operation)

        server, trainer = Server(), str(uuid4())

        def flow():
            engine = LocalWriteEngine(
                profile,
                native,
                files=WindowsWriteFiles(process_names=lambda: list(processes)),
            )
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine
            )
            return LauncherDeliveries(controller, server, trainer_id=trainer), engine

        delivery, engine = flow()
        purchase = server.purchase()
        result = delivery.deliver(purchase, "sitrus_berry")
        after = target.read_bytes()
        counts = native.inventory(after, ("sitrus_berry",))
        check(
            result["status"] == "DELIVERED"
            and server.purchases[purchase] == "used"
            and counts["items"]["sitrus_berry"]["count"]
            == initial["items"]["sitrus_berry"]["count"] + 1
            and engine.status(result["operation_id"]).status == "APPLIED_VERIFIED",
            "packaged delivery reserves, writes exactly one, rereads and consumes once",
        )
        backups = list((profile / "write-backups").glob("*.original"))
        check(
            len(backups) == 1 and backups[0].read_bytes() == original,
            "independent verified backup holds the exact original bytes",
        )
        try:
            delivery.deliver(purchase, "sitrus_berry")
            raise AssertionError("Second delivery admitted")
        except DeliveryRefused:
            pass
        check(target.read_bytes() == after, "repeated purchase never writes twice")

        wrong_trainer = server.purchase()
        server.authorized_trainer_key = "f" * 64
        try:
            delivery.deliver(wrong_trainer, "leftovers")
            raise AssertionError("Wrong league trainer admitted")
        except WriteSafetyError as error:
            check(
                error.code == "DELIVERY_OTHER_GAME"
                and target.read_bytes() == after
                and server.purchases[wrong_trainer] == "pending",
                "server-authorized trainer mismatch refuses writing and preserves purchase",
            )
        server.authorized_trainer_key = initial["trainer_key"]

        incompatible = server.purchase()
        try:
            delivery.deliver(incompatible, "bottle_cap")
            raise AssertionError("Gen7 item admitted in Gen6")
        except WriteSafetyError as error:
            check(
                error.code == "ITEM_NOT_IN_GAME"
                and target.read_bytes() == after
                and server.purchases[incompatible] == "pending",
                "Bottle Cap refused in X without consuming or writing",
            )

        blocked = server.purchase()
        processes.append("Lime3DS.exe")
        try:
            delivery.deliver(blocked, "leftovers")
            raise AssertionError("Open emulator admitted")
        except WriteSafetyError as error:
            check(
                error.code == "EMULATOR_RUNNING"
                and target.read_bytes() == after
                and server.purchases[blocked] == "pending",
                "running emulator refused; unused purchase released safely",
            )
        processes.clear()
        server.drop_completion = True
        result = delivery.deliver(blocked, "leftovers")
        written = target.read_bytes()
        check(
            result["status"] == "APPLIED",
            "lost completion leaves a recoverable journal",
        )
        delivery, engine = flow()
        check(
            delivery.settle() == []
            and target.read_bytes() == written
            and server.purchases[blocked] == "used"
            and all(
                row["state"] in ("DELIVERED", "RELEASED") for row in delivery.bindings()
            ),
            "fresh packaged engine recovers completion without a second write",
        )

        uncertain = server.purchase()

        def interrupt(point):
            if point == "after_publish":
                raise OSError("fixture interruption after replacement")

        engine.fault_hook = interrupt
        try:
            delivery.deliver(uncertain, "sitrus_berry")
            raise AssertionError("Unverified replacement marked delivered")
        except WriteSafetyError as error:
            check(
                error.code == "DELIVERY_RECOVERY_REQUIRED",
                "interrupted replacement requires recovery",
            )
        record = next(
            row for row in delivery.bindings() if row["purchase_id"] == uncertain
        )
        operation = record["operation_id"]
        uncertain_bytes = target.read_bytes()
        check(
            delivery.settle() == [operation]
            and server.deliveries[operation]["status"] == "RESERVED"
            and server.purchases[uncertain] == "pending",
            "uncertain write keeps its server reservation and never spends or releases",
        )
        delivery, engine = flow()
        check(
            engine.reconcile(operation).status == "APPLIED_VERIFIED"
            and delivery.settle() == []
            and target.read_bytes() == uncertain_bytes
            and server.purchases[uncertain] == "used",
            "fresh packaged engine verifies uncertain replacement then completes once",
        )
        check(fixture.read_bytes() == original, "synthetic input retained unchanged")
        report.update(
            status="PASS",
            fixture_sha256=sha256(original).hexdigest(),
            packaged_bytecode=True,
            self_contained_native=True,
        )
    except Exception as error:
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        (output / "delivery-package.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
