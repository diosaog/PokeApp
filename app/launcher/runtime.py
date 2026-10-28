"""Local UI state never waits for cloud. Separate parse and network workers."""

import hashlib
import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from queue import Empty, Full, Queue

from app.launcher.backend import BackendClient, BackendError, LauncherSession
from app.launcher.core import LauncherCore
from app.launcher.emulator_qualification import qualification_status
from app.launcher.journal import LocalConflict
from app.launcher.save_activity import SaveActivityGate, SaveBusy, save_read
from app.launcher.secrets import TokenStore
from app.launcher.sync import SaveWatchService
from app.launcher.trusted_sync import (
    PERSONAL,
    TrustedStore,
    deliver_trusted,
    save_paths,
)
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WriteSafetyError
from app.save_parser.files import SaveSource, SnapshotReader
from app.save_parser.models import SaveError
from app.save_parser.writer import PkhexProcessWriter

PRODUCTION_API = "https://pokeapp-api-production.up.railway.app"
QUICK_COMMANDS = ("quick_items_refresh", "quick_item_offer")
QUICK_ERRORS = {
    "INVENTORY_LIMIT": "Esa cantidad supera el máximo de la bolsa en este juego.",
    "INVENTORY_FULL": "La bolsa está llena: no cabe un objeto nuevo.",
    "CORRUPT_SAVE": "No se pudo preparar un archivo verificable con esa cantidad. Prueba con otra; tu partida no se ha modificado.",
    "STALE_SOURCE": "La partida ha cambiado. Vuelve a leerla e inténtalo de nuevo.",
    "STALE_MUTATION": "La partida ha cambiado. Vuelve a leerla e inténtalo de nuevo.",
    "EMULATOR_RUNNING": "Cierra el juego y el emulador antes de añadir objetos.",
    "QUICK_ITEMS_DISABLED": "Añadir objetos se activará cuando termine la certificación real del Launcher con Lime3DS. Ya puedes consultar tus cantidades.",
    "NATIVE_VERIFICATION_FAILED": "No se pudo preparar un archivo verificable con esa cantidad. Prueba con otra; tu partida no se ha modificado.",
    "NO_SELECTED_WRITE_TARGET": "Selecciona tu partida primero.",
    "UNSUPPORTED_FORMAT": "Esta partida no admite objetos rápidos. Juegos admitidos: X/Y, Rubí Omega/Zafiro Alfa y Sol/Luna/Ultrasol/Ultraluna.",
}
TRANSFER_COMMANDS = (
    "transfer_prepare",
    "transfer_apply",
    "transfer_fulfil",
    "transfer_cancel",
    "transfer_refresh",
)


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
        self,
        profile,
        inspector,
        *,
        client=None,
        token_store=None,
        start=True,
        discover=False,
    ):
        # Emulator discovery at start is for the real Launcher only (stdio).
        self.discover_on_start = discover
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
        try:
            # Listing/exporting verified backups never requires a native parser.
            writer = LocalWriteEngine(
                write_directory,
                PkhexProcessWriter(executable) if executable is not None else None,
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
            # Last time PokeApp confirmed this save is the current one.
            "last_synced": None,
            "auth_status": "LOGIN_REQUIRED",
            "cloud_sync": False,
            "cloud_receipt": None,
            "outbox": {"pending": 0, "paused": 0},
            "error": None,
            "write_error": None,
            "transfer_result": None,
            "quick_items": None,
            "quick_item_error": None,
            "emulator_saves": [],
            # Automatic save choice: PENDING | NONE | AUTO_SELECTED | CHOOSE | KEPT.
            "save_choice": {"status": "PENDING", "count": 0},
            "backend_origin": self.client.origin,
        }
        # Short-lived access token for the Launcher's own web view. Kept out of
        # self.value: state() goes to the renderer, this goes to main only.
        self._web_token = None
        self._web_token_wanted = False
        # Set the moment a logout is requested, before the cloud loop runs it,
        # so the web can never be handed the session it just signed out of.
        self._web_signed_out = False
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
        engine = getattr(self.writes, "engine", None)
        result["write"]["transfer_application_enabled"] = engine is not None and (
            type(getattr(engine, "capability", None)) is EngineeringCapability
            or (engine.allows("transfer_remove") and engine.allows("transfer_insert"))
        )
        result["emulator"] = qualification_status()
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
            "backup_list",
            "backup_export",
            "backup_restore",
        ):
            if name in ("backup_export", "backup_restore"):
                expected = (
                    {"operation_id", "destination", "role"}
                    if name == "backup_export"
                    else {
                        "operation_id",
                        "closed_emulator_confirmed",
                        "restore_confirmed",
                    }
                )
                if (
                    set(args) != expected
                    or not isinstance(args.get("operation_id"), str)
                    or len(args["operation_id"]) != 36
                ):
                    raise ValueError("invalid_backup_arguments")
                if name == "backup_export" and (
                    args["role"] not in ("original", "before_restore", "daily")
                    or not isinstance(args["destination"], str)
                    or not 1 <= len(args["destination"]) <= 4096
                ):
                    raise ValueError("invalid_backup_destination")
                if name == "backup_restore" and (
                    args["closed_emulator_confirmed"] is not True
                    or args["restore_confirmed"] is not True
                ):
                    raise ValueError("restore_confirmation_required")
            elif name == "write_confirm":
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
        if name == "web_session":
            if args:
                raise ValueError("unexpected_web_session_arguments")
            with self.lock:
                token = self._web_token
                if self._web_signed_out:
                    return {"status": "LOGIN_REQUIRED"}
            if token and token["expires_at"] > time.time() + 300:
                return {"status": "OK", **token}
            # Ask the cloud loop for a fresh token; main retries shortly.
            self._web_token_wanted = True
            self.next_cloud_refresh = 0
            return {
                "status": "PENDING" if self.session._principal else "LOGIN_REQUIRED"
            }
        if name == "discover_saves":
            from app.launcher.discovery import emulator_saves

            if args:
                raise ValueError("unexpected_discovery_arguments")
            found = emulator_saves()
            auto = self._choose_save(found)
            if auto:
                try:
                    self.local_commands.put_nowait(
                        ("select", {"path": found[0]["path"]})
                    )
                except Full:
                    return {"status": "BUSY"}
            return {"status": "DONE", "count": len(found), "auto_selected": auto}
        if name == "select_discovered":
            with self.lock:
                known = {s["path"] for s in self.value["emulator_saves"]}
            if set(args) != {"path"} or args["path"] not in known:
                raise ValueError("invalid_selection")
            name = "select"
        if name in QUICK_COMMANDS:
            if name == "quick_items_refresh":
                valid = args == {}
            else:
                valid = (
                    set(args) == {"item", "quantity", "closed_emulator_confirmed"}
                    and args["item"] in ("rare_candy", "heart_scale")
                    and type(args["quantity"]) is int
                    and 1 <= args["quantity"] <= 9999
                    and args["closed_emulator_confirmed"] is True
                )
            if not valid:
                raise ValueError("invalid_quick_item_arguments")
            try:
                self.write_commands.put_nowait((name, dict(args)))
            except Full:
                return {"status": "BUSY"}
            return {"status": "QUEUED"}
        if name in TRANSFER_COMMANDS:
            expected = (
                {"authorization_id", "closed_emulator_confirmed"}
                if name in ("transfer_prepare", "transfer_apply", "transfer_fulfil")
                else {"authorization_id"}
            )
            if (
                set(args) != expected
                or not isinstance(args["authorization_id"], str)
                or len(args["authorization_id"]) != 36
                or args.get("closed_emulator_confirmed", True) is not True
            ):
                raise ValueError("invalid_transfer_arguments")
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
        if name == "logout":
            with self.lock:
                self._web_token = None
                self._web_token_wanted = False
                self._web_signed_out = True
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

    def _auto_consent(self, trainer_id):
        """Owner decisions (2026-10-27, 2026-10-28): signing in is the consent
        to sync the selected save automatically — also on a shared PC; there
        is no manual sync. A save of another in-game trainer is still refused
        by the server for a season (SAVE_TRAINER_MISMATCH)."""
        self.store.enable(self.client.origin, trainer_id)
        return True

    def _new_saves(self, found):
        """Candidates this Launcher has not listed before (path hashes only).

        The first discovery sets the baseline, so nothing counts as new then."""
        path = self.core.profile / "known-saves.json"
        key = lambda f: hashlib.sha256(
            os.path.normcase(f["path"]).encode("utf-8")
        ).hexdigest()
        try:
            known = set(json.loads(path.read_text(encoding="utf-8"))[:64])
            baseline = False
        except (OSError, ValueError, TypeError):
            known, baseline = set(), True
        selected = self.core.config.selected_save
        new = [
            f
            for f in found
            if key(f) not in known and f["path"] != selected and not baseline
        ]
        try:
            path.write_text(
                json.dumps(sorted(known | {key(f) for f in found})[:64]),
                encoding="utf-8",
            )
        except OSError:
            pass
        return new

    def _choose_save(self, found):
        """Owner rule: one valid candidate is chosen automatically; several ask.

        A remembered save is never replaced: other or new candidates only raise
        a notice. Discovery lists and stats files; it never opens them."""
        new = self._new_saves(found)
        selected = self.core.config.selected_save
        if selected:
            others = [f for f in found if f["path"] != selected]
            choice = {"status": "KEPT", "count": len(others), "new": len(new)}
        elif len(found) == 1:
            choice = {"status": "AUTO_SELECTED", "count": 1, "new": 0}
        else:
            choice = {
                "status": "CHOOSE" if found else "NONE",
                "count": len(found),
                "new": len(new),
            }
        self._patch(emulator_saves=found, save_choice=choice)
        return choice["status"] == "AUTO_SELECTED"

    def _discover_on_start(self):
        from app.launcher.discovery import emulator_saves

        try:
            found = emulator_saves()
        except OSError:
            found = []
        if self._choose_save(found):
            self.local_commands.put_nowait(("select", {"path": found[0]["path"]}))

    def _local_loop(self):
        if self.discover_on_start:
            try:
                self._discover_on_start()
            except Exception:  # noqa: BLE001 - discovery is a convenience only
                self._patch(save_choice={"status": "NONE", "count": 0})
        while not self.stop.wait(0.1):
            try:
                self._write_step()
                self._local_step()
            except SaveBusy:
                continue  # a local physical write/recovery exclusively owns the save
            except Exception:  # noqa: BLE001 - sanitized local boundary
                self._patch(local_status="LOCAL_UNAVAILABLE")

    def _transfer_step(self, name, args):
        from app.launcher.transfer import AuthenticatedTransferRemote, LauncherTransfers

        try:
            principal = self.session._principal
            with self.lock:
                cloud = deepcopy(self.value.get("cloud")) or {}
            season = (cloud.get("data") or {}).get("season")
            if principal is None or not season:
                raise WriteSafetyError("TRANSFER_CONTEXT_UNAVAILABLE")
            transfers = LauncherTransfers(
                self.writes,
                AuthenticatedTransferRemote(
                    self.session, season["id"], principal.trainer_id
                ),
            )
            aid = args["authorization_id"]
            if name == "transfer_prepare":
                result = transfers.prepare(aid, closed_emulator_confirmed=True)
            elif name == "transfer_apply":
                result = transfers.apply(aid, closed_emulator_confirmed=True)
            elif name == "transfer_fulfil":
                result = transfers.fulfil(aid, closed_emulator_confirmed=True)
            elif name == "transfer_cancel":
                result = transfers.cancel(aid)
            else:
                result = transfers.refresh(aid)
            self._patch(write_error=None, transfer_result=result)
            if name == "transfer_fulfil" or result.get("completed"):
                self.next_cloud_refresh = 0  # the obligation state changes server-side
            if result["status"] == "COMMITTED":
                self.next_cloud_refresh = 0
                self._load_local()  # re-read the save the server now accepts
        except SaveBusy:
            self._patch(
                write_error="Hay una lectura o sincronización en curso. Espera y vuelve a intentarlo."
            )
        except BackendError:
            self._patch(
                write_error="PokeApp todavía no permite este paso: esperando al otro entrenador o a la verificación. Nada se ha confirmado."
            )
        except WriteSafetyError as error:
            self._patch(
                write_error="La aplicación física de robos no está habilitada en este Launcher."
                if str(error) == "TRANSFER_APPLICATION_DISABLED"
                else "No se pudo continuar el robo. Mantén el emulador cerrado y conserva las copias."
            )
        except Exception:  # noqa: BLE001 - no native output, private path or journal data to UI
            self.save_activity.recovery_required = True
            self._patch(
                write_error="No se pudo verificar la operación. La sincronización queda pausada."
            )

    def _quick_step(self, name, args):
        from app.launcher.quick_items import inventory_view, quick_item_intent
        from app.save_parser.writer import NativeWriteError

        engine = self.writes.engine
        try:
            native = getattr(engine, "native", None)
            if native is None or not self.writes.selected():
                raise WriteSafetyError("NO_SELECTED_WRITE_TARGET")
            data = engine.files.read_path(Path(self.writes.selected()))
            enabled = engine.allows("add_item")
            if name == "quick_items_refresh":
                view = inventory_view(native, data)
                self._patch(
                    quick_items=view | {"application_enabled": enabled},
                    quick_item_error=None,
                )
                return
            if not enabled:
                raise WriteSafetyError("QUICK_ITEMS_DISABLED")
            intent = quick_item_intent(native, data, args["item"], args["quantity"])
            # Existing journal: backup, explicit write_confirm, readback, recovery.
            self.writes.offer(intent, closed_emulator_confirmed=True)
            self._patch(quick_item_error=None, write_error=None)
        except SaveBusy:
            self._patch(
                quick_item_error="Hay una lectura o sincronización en curso. Espera y vuelve a intentarlo."
            )
        except (NativeWriteError, WriteSafetyError) as error:
            self._patch(
                quick_item_error=QUICK_ERRORS.get(
                    str(error) or getattr(error, "code", ""),
                    "No se puede preparar el cambio. Revisa la partida seleccionada; no se ha modificado.",
                )
            )
        except Exception:  # noqa: BLE001 - no native output, path or journal data to UI
            if name == "quick_item_offer":
                self.save_activity.recovery_required = True
            self._patch(
                quick_item_error="No se pudo comprobar la partida. Conserva las copias y vuelve a intentarlo."
            )

    def _write_step(self):
        try:
            name, args = self.write_commands.get_nowait()
        except Empty:
            return
        if name in QUICK_COMMANDS:
            try:
                self._quick_step(name, args)
            finally:
                self.write_commands.task_done()
            return
        if name in TRANSFER_COMMANDS:
            try:
                self._transfer_step(name, args)
            finally:
                self.write_commands.task_done()
            return
        try:
            if name == "write_confirm":
                result = self.writes.confirm(**args)
            elif name == "backup_list":
                result = self.writes.refresh_backups()
            elif name == "backup_export":
                result = self.writes.export_backup(**args)
            elif name == "backup_restore":
                result = self.writes.restore_backup(**args)
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
                self._patch(quick_items=None)  # counts are re-read, never assumed
                self._load_local()
        except SaveBusy:
            self._patch(
                write_error="Hay una lectura o sincronización en curso. Espera y vuelve a confirmar."
            )
        except WriteSafetyError as error:
            self._patch(
                write_error="Otra instancia de PokeApp Launcher está trabajando con esta partida. Ciérrala y vuelve a intentarlo; no se ha modificado nada."
                if str(error) == "WRITE_ALREADY_RUNNING"
                else "No se pudo confirmar el cambio. Revisa la partida seleccionada y conserva las copias."
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
        # Without an active season the save still syncs, to the personal record.
        scope = season["id"] if season else PERSONAL
        if not (
            state["cloud_sync"]
            and principal
            and state["cloud"]
            and receipt
            and state["local_status"] == "READY"
        ):
            return
        try:
            snapshot = SnapshotReader().read(SaveSource.enroll(state["selected_save"]))
            oid = self.store.enqueue_raw(
                self.client.origin,
                principal["trainer_id"],
                scope,
                receipt,
                snapshot.data,
            )
            accepted = self.store.receipt(
                self.client.origin, principal["trainer_id"], scope, oid
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
        wanted, self._web_token_wanted = self._web_token_wanted, False
        principal = self.session.principal(min_validity=600 if wanted else 30)
        self.tokens.save(self.client.origin, self.session)
        tokens = self.session._tokens
        with self.lock:
            self._web_token = (
                None
                if self._web_signed_out
                else (
                    {
                        "access_token": tokens.access_token,
                        "expires_at": int(tokens.expires_at),
                        "trainer_id": principal.trainer_id,
                    }
                    if tokens and isinstance(tokens.expires_at, (int, float))
                    else None
                )
            )
        if not self.store.enabled(
            self.client.origin, principal.trainer_id
        ) and self._auto_consent(principal.trainer_id):
            self._patch(cloud_sync=True)
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
        item_uses = None
        transfers = None
        if season:
            from uuid import UUID

            sid = str(UUID(season["id"]))
            shop = self.session.request("GET", f"/v1/read/seasons/{sid}/shop")
            wallet = shop.get("balance")
            raw_uses = self.session.request(
                "GET", f"/v1/launcher/seasons/{sid}/item-uses", missing=True
            )
            if raw_uses is not None:
                from pydantic import ValidationError

                from app.launcher.item_use import ItemUseListWire

                try:
                    validated = ItemUseListWire.model_validate(raw_uses)
                    if any(
                        str(a.trainer_id) != principal.trainer_id
                        or str(a.season_id) != sid
                        for a in validated.items
                    ):
                        raise ValueError("item-use scope")
                    item_uses = [{"status": a.status} for a in validated.items]
                except (ValidationError, ValueError):
                    raise BackendError("BACKEND_UNAVAILABLE") from None
            raw_transfers = self.session.request(
                "GET", f"/v1/launcher/seasons/{sid}/transfers", missing=True
            )
            if raw_transfers is not None:
                from pydantic import ValidationError

                from app.launcher.transfer import TransferAssignmentsWire

                try:
                    listed = TransferAssignmentsWire.model_validate(raw_transfers)
                except ValidationError:
                    raise BackendError("BACKEND_UNAVAILABLE") from None
                # Status only: plans are fetched fresh at preparation, never cached.
                transfers = [
                    {
                        "authorization_id": t.authorization_id,
                        "side": t.side,
                        "status": t.status,
                        "obligation": t.obligation,
                        "mandatory": t.mandatory,
                        "planned": t.intent is not None,
                        "claimed": t.claimed,
                        "apply_started": t.apply_started,
                        "verified": t.verified,
                        "location": t.location(),
                    }
                    for t in listed.items
                ]
        data = {
            "principal": principal.model_dump(),
            "season": season,
            "wallet": wallet,
            "item_uses": item_uses,
            "transfers": transfers,
            # 27A: a decided robbery's removal comes before any ordinary sync.
            "mandatory_sync": any(t["mandatory"] for t in transfers or []),
        }
        self.store.save_cache(self.client.origin, principal.trainer_id, data)
        self._patch(
            cloud=self.store.cache(self.client.origin, principal.trainer_id),
            last_online=time.time(),
        )
        self.next_cloud_refresh = time.monotonic() + 120
        if data["mandatory_sync"]:
            return  # the server refuses ordinary sync until the removal is verified
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
                    and row["season"] == (season["id"] if season else PERSONAL)
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
                f"{save_paths(accepted['season_id'])[0]}/receipt?sha256={accepted['sha256']}",
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
            **({"last_synced": time.time()} if accepted else {}),
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
                        with self.lock:
                            self._web_token = None
                        self._patch(
                            principal=None,
                            cloud=None,
                            cloud_receipt=None,
                            last_synced=None,
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
                        with self.lock:
                            self._web_signed_out = False
                        self._patch(
                            principal=principal.model_dump(),
                            auth_status="VERIFIED",
                            cloud_sync=self._auto_consent(principal.trainer_id),
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
