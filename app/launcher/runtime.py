"""Local UI state never waits for cloud. Separate parse and network workers."""

import threading
import time
from copy import deepcopy
from pathlib import Path
from queue import Empty, Full, Queue

from app.launcher.backend import BackendClient, BackendError, LauncherSession
from app.launcher.core import LauncherCore
from app.launcher.journal import LocalConflict
from app.launcher.save_activity import SaveActivityGate, SaveBusy, save_read
from app.launcher.secrets import TokenStore
from app.launcher.sync import SaveWatchService
from app.launcher.trusted_sync import TrustedStore, deliver_trusted
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import LocalWriteEngine
from app.launcher.write_files import WriteSafetyError
from app.save_parser.files import SaveSource, SnapshotReader
from app.save_parser.models import SaveError
from app.save_parser.writer import PkhexProcessWriter

PRODUCTION_API = "https://pokeapp-api-production.up.railway.app"


def _write_recovery_exists(directory):
    """Absent/empty infrastructure is not an uncertain physical operation."""
    try:
        if directory.is_symlink() or directory.is_junction():
            return True
        if not directory.exists():
            return False
        for child in directory.iterdir():
            if (
                child.name == "write-backups"
                and not child.is_symlink()
                and not child.is_junction()
                and child.is_dir()
                and not any(child.iterdir())
            ):
                continue
            return True
        return False
    except OSError:
        return True


class LauncherRuntime:
    def __init__(
        self, profile, inspector, *, client=None, token_store=None, start=True
    ):
        self.core = LauncherCore(profile, inspector)
        self.client = client or BackendClient(PRODUCTION_API)
        self.session = LauncherSession(self.client)
        self.tokens = token_store or TokenStore(self.core.profile)
        self.store = TrustedStore(self.core.journal)
        self.lock = threading.Lock()
        self.save_activity = SaveActivityGate()
        writer = None
        write_directory = self.core.profile / "writes"
        had_recovery_material = _write_recovery_exists(write_directory)
        executable = getattr(inspector.parser, "executable", None)
        if executable is not None:
            try:
                writer = LocalWriteEngine(
                    write_directory, PkhexProcessWriter(executable)
                )
            except Exception:  # fail closed on unreadable local recovery state
                pass
        self.writes = LocalWriteController(
            self.save_activity,
            lambda: self.core.config.selected_save,
            writer,
            on_verified=self._invalidate_written_save,
        )
        if writer is None and had_recovery_material:
            self.save_activity.recovery_required = True
        self.stop = threading.Event()
        self.next_cloud_refresh = 0.0
        self.local_commands, self.cloud_commands = Queue(maxsize=1), Queue(maxsize=1)
        self.write_commands = Queue(maxsize=1)
        self.value = {
            "local_status": "NO_SAVE",
            "receipt_id": None,
            "observation": None,
            "selected_save": self.core.config.selected_save,
            "principal": None,
            "cloud": None,
            "cloud_status": "OFFLINE",
            "last_online": 0,
            "auth_status": "LOGIN_REQUIRED",
            "cloud_sync": False,
            "cloud_receipt": None,
            "outbox": {"pending": 0, "paused": 0},
            "error": None,
            "write_error": None,
        }
        self.receipt = None
        self.watch = None
        self._load_local()
        try:
            self.tokens.load(self.client.origin, self.session)
            if self.session._principal:
                tid = self.session._principal.trainer_id
                self.value.update(
                    principal=self.session._principal.model_dump(),
                    cloud=self.store.cache(self.client.origin, tid),
                    auth_status="STALE",
                    cloud_sync=self.store.enabled(self.client.origin, tid),
                )
        except (OSError, ValueError, KeyError):
            self.session.logout()
            self.value["error"] = "LOGIN_REQUIRED"
        self.threads = []
        if start:
            for target in (self._local_loop, self._cloud_loop):
                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                self.threads.append(thread)

    def _patch(self, **fields):
        with self.lock:
            self.value.update(fields)

    def state(self, known_receipt=None):
        with self.lock:
            result = {k: v for k, v in self.value.items() if k != "observation"}
            if known_receipt != self.value["receipt_id"] or known_receipt is None:
                result["observation"] = self.value["observation"]
            result = deepcopy(result)
        result["cloud_stale"] = (
            result["auth_status"] != "VERIFIED"
            or time.time() - result["last_online"] > 90
            or result["cloud_status"] == "OFFLINE"
        )
        if (
            time.time() - result["last_online"] > 90
            and result["cloud_status"] != "SYNCING"
        ):
            result["cloud_status"] = "OFFLINE"
        result["write"] = self.writes.state()
        return result

    def command(self, name, args=None):
        args = args or {}
        if not isinstance(args, dict):
            raise ValueError("invalid_command_arguments")
        if name == "state":
            return self.state(args.get("known_receipt"))
        if name in (
            "write_confirm",
            "write_reconcile",
            "export_prepare",
            "export_confirm",
            "export_reconcile",
        ):
            if name == "write_confirm":
                state = self.writes.state()
                if (
                    set(args) != {"operation_id", "closed_emulator_confirmed"}
                    or args["closed_emulator_confirmed"] is not True
                    or not state["can_confirm"]
                    or args["operation_id"] != state["operation_id"]
                ):
                    raise ValueError("write_confirmation_required")
            elif name == "export_prepare":
                if (
                    set(args) - {"destination", "intent", "closed_emulator_confirmed"}
                    or not isinstance(args.get("destination"), str)
                    or not args["destination"]
                    or len(args["destination"]) > 4096
                    or not isinstance(args.get("intent"), dict)
                    or args.get("closed_emulator_confirmed") is not True
                ):
                    raise ValueError("invalid_export_destination")
            elif name == "export_confirm":
                if (
                    set(args) != {"operation_id", "closed_emulator_confirmed"}
                    or not isinstance(args["operation_id"], str)
                    or args["closed_emulator_confirmed"] is not True
                ):
                    raise ValueError("invalid_export_operation")
            elif args:
                raise ValueError("unexpected_recovery_arguments")
            try:
                self.write_commands.put_nowait((name, dict(args)))
            except Full:
                return {"status": "BUSY"}
            return {"status": "QUEUED"}
        if name not in ("select", "login", "logout", "retry", "sync"):
            raise ValueError("command_not_supported")
        if name == "select" and (
            not isinstance(args.get("path"), str) or len(args["path"]) > 4096
        ):
            raise ValueError("invalid_selection")
        if name == "login" and (
            not isinstance(args.get("trainer"), str)
            or not 1 <= len(args["trainer"]) <= 128
            or not isinstance(args.get("pin"), str)
            or not 4 <= len(args["pin"]) <= 32
        ):
            raise ValueError("invalid_login")
        queue = (
            self.local_commands if name in ("select", "sync") else self.cloud_commands
        )
        try:
            queue.put_nowait((name, args))
        except Full:
            return {"status": "BUSY"}
        return {"status": "QUEUED"}

    def _load_local(self):
        # Cached local inspection remains useful when the configured file is missing.
        path = self.core.config.selected_save
        self.watch = None
        self.receipt = None
        if not path:
            return
        source = SaveSource(
            Path(path)
        )  # cache key only; reads still use enroll/verified_path
        self.receipt = self.core.journal.head(source)
        if self.receipt:
            self._patch(
                receipt_id=self.receipt.id,
                observation=self.receipt.observation.model_dump(mode="json"),
                local_status="CACHED",
            )
        self.watch = SaveWatchService(
            self.core.sync,
            source,
            poll_seconds=self.core.config.poll_seconds,
            debounce_seconds=self.core.config.debounce_seconds,
        )

    def _local_loop(self):
        while not self.stop.wait(0.1):
            try:
                self._write_step()
                self._local_step()
            except SaveBusy:
                continue  # a local physical write/recovery exclusively owns the save
            except Exception:  # noqa: BLE001 - sanitized local boundary
                self._patch(local_status="LOCAL_UNAVAILABLE")

    def _write_step(self):
        try:
            name, args = self.write_commands.get_nowait()
        except Empty:
            return
        try:
            if name == "write_confirm":
                result = self.writes.confirm(**args)
            elif name == "export_prepare":
                result = self.writes.prepare_export(**args)
            elif name == "export_confirm":
                result = self.writes.confirm_export(**args)
            elif name == "export_reconcile":
                result = self.writes.reconcile()
            else:
                result = self.writes.reconcile()
            self._patch(write_error=None)
            if result["status"] in ("APPLIED_VERIFIED", "RESTORED_VERIFIED"):
                self._load_local()
        except SaveBusy:
            self._patch(
                write_error="Hay una lectura o sincronización en curso. Espera y vuelve a confirmar."
            )
        except WriteSafetyError:
            self._patch(
                write_error="No se pudo confirmar el cambio. Revisa la partida seleccionada y conserva las copias."
            )
        except Exception:  # no native output, private path or journal data to UI
            self.save_activity.recovery_required = True
            self._patch(
                write_error="No se pudo verificar la operación. La sincronización queda pausada."
            )
        finally:
            self.write_commands.task_done()

    def _invalidate_written_save(self):
        # Called while the controller still holds the exclusive write lease.
        # A cloud worker can resume only after stale upload eligibility is gone.
        self.receipt = None
        self.watch = None
        self._patch(
            local_status="READING",
            receipt_id=None,
            observation=None,
            cloud_receipt=None,
        )

    @save_read
    def _local_step(self):
        try:
            name, args = self.local_commands.get_nowait()
            if name == "select":
                self.core.select(Path(args["path"]))
                self._patch(
                    selected_save=self.core.config.selected_save,
                    observation=None,
                    receipt_id=None,
                    cloud_receipt=None,
                    local_status="READING",
                )
                self._load_local()
            elif name == "sync":
                principal = self.state()["principal"]
                if principal:
                    # Upgrading an old private-inbox opt-in must not silently
                    # authorize the new registration/economy effects.
                    self.store.enable(self.client.origin, principal["trainer_id"])
                    self._patch(cloud_sync=True, error=None)
                    self._enqueue_local()
            self.local_commands.task_done()
        except Empty:
            pass
        if self.watch:
            result = self.watch.tick(time.monotonic())
            if result:
                if result.status in ("SYNCED", "NO_CHANGE"):
                    receipt = self.core.journal.head(self.watch.source)
                    if self.receipt is None or self.receipt.id != receipt.id:
                        self._patch(cloud_receipt=None)
                    self.receipt = receipt
                    self._patch(
                        local_status="READY",
                        receipt_id=receipt.id,
                        observation=receipt.observation.model_dump(mode="json"),
                    )
                    self._enqueue_local()
                else:
                    self._patch(local_status=result.error or "LOCAL_UNAVAILABLE")

    @save_read
    def _enqueue_local(self):
        state = self.state()
        principal = state["principal"]
        season = (state["cloud"] or {}).get("data", {}).get("season")
        receipt = self.receipt
        if not (
            state["cloud_sync"]
            and principal
            and season
            and receipt
            and state["local_status"] == "READY"
        ):
            return
        try:
            snapshot = SnapshotReader().read(SaveSource.enroll(state["selected_save"]))
            oid = self.store.enqueue_raw(
                self.client.origin,
                principal["trainer_id"],
                season["id"],
                receipt,
                snapshot.data,
            )
            accepted = self.store.receipt(
                self.client.origin, principal["trainer_id"], season["id"], oid
            )
            self._patch(
                cloud_receipt=accepted.model_dump() if accepted else None,
                outbox=self.store.summary(self.client.origin, principal["trainer_id"]),
            )
        except (LocalConflict, SaveError) as error:
            self._patch(cloud_receipt=None, local_status="READING", error=str(error))

    @save_read
    def _cloud_step(self):
        health = self.client.json("GET", "/health")
        if health.get("status") != "ok" or health.get("service") != "pokeapp-api":
            raise BackendError("BACKEND_UNAVAILABLE")
        self._patch(last_online=time.time(), cloud_status="ONLINE")
        if not self.session._principal:
            return
        if (
            time.monotonic() < self.next_cloud_refresh
            and self.store.pending(
                self.client.origin, self.session._principal.trainer_id
            )
            is None
        ):
            return  # lightweight /health only between cached cloud refreshes
        principal = self.session.principal()
        self.tokens.save(self.client.origin, self.session)
        self._patch(principal=principal.model_dump(), auth_status="VERIFIED")
        seasons = self.session.request("GET", "/v1/read/seasons")
        items = seasons.get("items")
        if not isinstance(items, list):
            raise BackendError("BACKEND_UNAVAILABLE")
        active = [s for s in items if s.get("status") == "active"]
        if len(active) > 1:
            raise BackendError("BACKEND_UNAVAILABLE")
        if not active and seasons.get("next_offset") is not None:
            # A partial listing cannot prove there is no current season.
            raise BackendError("BACKEND_UNAVAILABLE")
        season = active[0] if active else None
        wallet = None
        if season:
            from uuid import UUID

            sid = str(UUID(season["id"]))
            shop = self.session.request("GET", f"/v1/read/seasons/{sid}/shop")
            wallet = shop.get("balance")
        data = {"principal": principal.model_dump(), "season": season, "wallet": wallet}
        self.store.save_cache(self.client.origin, principal.trainer_id, data)
        self._patch(
            cloud=self.store.cache(self.client.origin, principal.trainer_id),
            last_online=time.time(),
        )
        self.next_cloud_refresh = time.monotonic() + 120
        # Only the locally ready selected save is eligible; never upload old/missing cache as new.
        self._enqueue_local()
        row = self.store.pending(self.client.origin, principal.trainer_id)
        if row:
            try:
                current = self.receipt
                state = self.state()
                delivered = deliver_trusted(
                    self.session,
                    self.store,
                    row,
                    selected_hash=current.fingerprint.sha256
                    if current
                    and state["local_status"] == "READY"
                    and state["cloud_sync"]
                    and season
                    and row["season"] == season["id"]
                    else None,
                )
                if delivered is not None:
                    self._patch(cloud_receipt=delivered.model_dump())
                self._enqueue_local()
            except BackendError as exc:
                if str(exc) in (
                    "OBSERVATION_REJECTED",
                    "SAVE_REJECTED",
                    "SAVE_RECEIPT_MISMATCH",
                ):
                    self.store.block(row)
                raise
        accepted = self.state()["cloud_receipt"]
        if accepted:
            # A different device may have registered a newer file since our last
            # success. Cached success must not claim that an old save is current.
            latest = self.session.request(
                "GET",
                f"/v1/seasons/{accepted['season_id']}/saves/receipt?sha256={accepted['sha256']}",
            )
            if (
                not latest.get("is_current")
                or latest.get("save_id") != accepted["save_id"]
            ):
                self._patch(cloud_receipt=None)
                raise BackendError("SAVE_SUPERSEDED")
        self._patch(
            outbox=self.store.summary(self.client.origin, principal.trainer_id),
            cloud_status="ONLINE",
            last_online=time.time(),
            error=None,
        )

    def _cloud_loop(self):
        next_attempt, failures = 0.0, 0
        while not self.stop.wait(0.2):
            try:
                try:
                    name, args = self.cloud_commands.get_nowait()
                    if name == "logout":
                        self.session.logout()
                        self.tokens.clear()
                        self._patch(
                            principal=None,
                            cloud=None,
                            cloud_receipt=None,
                            auth_status="LOGIN_REQUIRED",
                            cloud_sync=False,
                            error=None,
                        )
                    elif name == "login":
                        self._patch(
                            auth_status="CHECKING",
                            cloud_status="SYNCING",
                            cloud=None,
                            principal=None,
                            cloud_receipt=None,
                        )
                        self.tokens.clear()
                        try:
                            principal = self.session.login(args["trainer"], args["pin"])
                        finally:
                            args.clear()
                        self.tokens.save(self.client.origin, self.session)
                        self._patch(
                            principal=principal.model_dump(),
                            auth_status="VERIFIED",
                            cloud_sync=self.store.enabled(
                                self.client.origin, principal.trainer_id
                            ),
                        )
                    elif name == "retry" and self.session._principal:
                        self.store.retry(
                            self.client.origin, self.session._principal.trainer_id
                        )
                    args.clear()  # no credentials in journal/logs/UI replies
                    self.cloud_commands.task_done()
                    failures, next_attempt = 0, 0
                    self.next_cloud_refresh = 0
                except Empty:
                    pass
                if time.monotonic() < next_attempt:
                    continue
                self._patch(cloud_status="SYNCING")
                self._cloud_step()
                failures, next_attempt = 0, time.monotonic() + 30
            except SaveBusy:
                continue  # no upload/reimport overlaps a physical write/recovery
            except BackendError as exc:
                code = str(exc)
                if code in ("LOGIN_REQUIRED", "SESSION_REJECTED"):
                    self.session.logout()
                    self.tokens.clear()
                    self._patch(auth_status="LOGIN_REQUIRED", principal=None)
                failures += 1
                # Five automatic attempts, then manual retry. No endless replay loop.
                next_attempt = time.monotonic() + (
                    min(300, 5 * 3 ** (failures - 1)) if failures < 5 else float("inf")
                )
                if not self.session._principal:
                    self._patch(auth_status="LOGIN_REQUIRED")
                rejected = code in (
                    "SAVE_REJECTED",
                    "OBSERVATION_REJECTED",
                    "SAVE_SUPERSEDED",
                    "SAVE_RECEIPT_MISMATCH",
                )
                self._patch(
                    cloud_status="ONLINE" if rejected else "OFFLINE", error=code
                )
            except Exception:  # noqa: BLE001 - isolate cloud/storage failures from local browsing
                failures += 1
                next_attempt = time.monotonic() + (60 if failures < 5 else float("inf"))
                self._patch(cloud_status="OFFLINE", error="SYNC_UNAVAILABLE")

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=90)
        self.client.close()
