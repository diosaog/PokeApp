"""Local UI state never waits for cloud. Separate parse and network workers."""

import hashlib
import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from queue import Empty, Full, Queue

from app.launcher.backend import (
    SESSION_ENDED,
    BackendClient,
    BackendError,
    LauncherSession,
)
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
QUICK_COMMANDS = ("quick_items_refresh", "quick_item_offer", "quick_item_apply")
QUICK_ERRORS = {
    "INVENTORY_LIMIT": "Esa cantidad supera el máximo de la bolsa en este juego.",
    "INVENTORY_FULL": "La bolsa está llena: no cabe un objeto nuevo.",
    "CORRUPT_SAVE": "No se pudo preparar un archivo verificable con esa cantidad. Prueba con otra; tu partida no se ha modificado.",
    "STALE_SOURCE": "La partida ha cambiado. Vuelve a leerla e inténtalo de nuevo.",
    "STALE_MUTATION": "La partida ha cambiado. Vuelve a leerla e inténtalo de nuevo.",
    "EMULATOR_RUNNING": "El emulador está abierto: ciérralo (y el juego) y vuelve a pulsar «Añadir a la bolsa». Tu partida no ha cambiado.",
    "PROCESS_CHECK_UNAVAILABLE": "No se pudo comprobar si el emulador está abierto. Vuelve a intentarlo; tu partida no ha cambiado.",
    "FILE_LOCKED_OR_ACCESS_DENIED": "No se puede añadir el objeto porque el archivo de la partida está siendo utilizado por otro programa. Tu partida no ha cambiado.",
    "TARGET_READ_ONLY": "El archivo de la partida es de solo lectura. Tu partida no ha cambiado.",
    "SOURCE_HASH_CHANGED": "La partida ha cambiado mientras se preparaba. Vuelve a intentarlo; tu partida no ha cambiado.",
    "BACKUP_INVALID": "No se pudo verificar la copia de seguridad. Tu partida no ha cambiado.",
    "ARTIFACT_VERIFICATION_FAILED": "No se pudo verificar la copia de seguridad. Tu partida no ha cambiado.",
    "QUICK_ITEMS_DISABLED": "Añadir objetos no está disponible en este Launcher. Ya puedes consultar tus cantidades.",
    "NATIVE_VERIFICATION_FAILED": "No se pudo preparar un archivo verificable con esa cantidad. Prueba con otra; tu partida no se ha modificado.",
    "NO_SELECTED_WRITE_TARGET": "Selecciona tu partida primero.",
    "UNSUPPORTED_FORMAT": "Esta partida no admite objetos rápidos. Juegos admitidos: X/Y, Rubí Omega/Zafiro Alfa y Sol/Luna/Ultrasol/Ultraluna.",
}
GAME_NAMES = {
    "X": "Pokémon X",
    "Y": "Pokémon Y",
    "OR": "Pokémon Rubí Omega",
    "AS": "Pokémon Zafiro Alfa",
    "SN": "Pokémon Sol",
    "MN": "Pokémon Luna",
    "US": "Pokémon Ultrasol",
    "UM": "Pokémon Ultraluna",
}


def save_identity(receipt):
    """What a season binds: game and in-game trainer, exactly as the server
    builds it from its own parse of the same bytes."""
    if receipt is None:
        return None
    return {
        "game": receipt.observation.game,
        "trainer": receipt.observation.trainer.model_dump(mode="json"),
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
        # A new local change or a web token request runs the cloud step now
        # instead of at its next 30 s turn.
        self._cloud_wake = threading.Event()
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
            # PokeApp's receipt for the selected save as the trainer's active
            # save (personal record), and for the active season when it uses it.
            "cloud_receipt": None,
            "season_receipt": None,
            # True only while bytes are actually being sent; connectivity is
            # cloud_status alone, so the UI never flickers every cycle.
            "syncing": False,
            "outbox": {"pending": 0, "paused": 0},
            "error": None,
            "error_detail": None,
            "write_error": None,
            "transfer_result": None,
            "quick_items": None,
            "quick_item_error": None,
            "quick_item_result": None,
            # Counts finished quick-item steps, so the same refusal twice is
            # still told twice.
            "quick_item_seq": 0,
            "emulator_saves": [],
            # What the last search checked, so «no saves» can say why.
            "discovery": None,
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
        if time.time() - result["last_online"] > 90 and not result["syncing"]:
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
            # Ask the cloud loop for a fresh token now; main retries shortly.
            self._web_token_wanted = True
            self.next_cloud_refresh = 0
            self._cloud_wake.set()
            return {
                "status": "PENDING" if self.session._principal else "LOGIN_REQUIRED"
            }
        if name == "discover_saves":
            from app.launcher.discovery import discover_emulator_saves

            if args:
                raise ValueError("unexpected_discovery_arguments")
            found, report = discover_emulator_saves()
            self._patch(discovery=report)
            auto = self._choose_save(found)
            if auto:
                try:
                    self.local_commands.put_nowait(
                        ("select", {"path": found[0]["path"]})
                    )
                except Full:
                    return {"status": "BUSY"}
            # The list itself goes back with the answer: the selector never
            # opens on a state poll that predates this search.
            with self.lock:
                choice = deepcopy(self.value["save_choice"])
            return {
                "status": "DONE",
                "count": len(found),
                "auto_selected": auto,
                "saves": found,
                "discovery": report,
                "save_choice": choice,
            }
        if name == "select_discovered":
            with self.lock:
                known = {s["path"] for s in self.value["emulator_saves"]}
            if set(args) != {"path"} or args["path"] not in known:
                raise ValueError("invalid_selection")
            name = "select"
        if name in QUICK_COMMANDS:
            if name == "quick_items_refresh":
                valid = args == {}
            elif name == "quick_item_apply":
                # One click: the core itself checks that no emulator runs and
                # that the file is free, then backs up, writes and verifies.
                valid = (
                    set(args) == {"item", "quantity"}
                    and args["item"] in ("rare_candy", "heart_scale")
                    and type(args["quantity"]) is int
                    and 1 <= args["quantity"] <= 9999
                )
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
        if name == "select":
            # A file that cannot be a save is refused now, with its reason,
            # instead of failing silently in the background reader.
            try:
                SaveSource.enroll(Path(args["path"]))
            except SaveError as exc:
                raise ValueError(exc.code.value.lower()) from None
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
            # Metadata checks are cheap: a change is seen within ~3 s even on
            # profiles that still store the old 5 s interval.
            poll_seconds=min(2.0, self.core.config.poll_seconds),
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
            # A remembered file that is gone (renamed, moved, emulator
            # reinstalled) is said plainly instead of failing every read.
            missing = not Path(selected).is_file()
            choice = {
                "status": "MISSING" if missing else "KEPT",
                "count": len(others),
                "new": len(new),
            }
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
        from app.launcher.discovery import discover_emulator_saves

        try:
            found, report = discover_emulator_saves()
        except OSError:
            found, report = [], None
        self._patch(discovery=report)
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
            # A robbery acts on the save this season uses, never on another
            # game the trainer happens to have selected.
            link = (cloud.get("data") or {}).get("season_link") or {}
            if (
                name != "transfer_refresh"
                and link.get("status") == "BOUND"
                and link.get("identity") != save_identity(self.receipt)
            ):
                self._patch(
                    write_error=(
                        "Este robo es sobre tu partida de la Liga ("
                        + GAME_NAMES.get(link.get("game"), "otra partida")
                        + "). Elígela en «Cambiar partida» y vuelve a intentarlo; "
                        "no se ha modificado nada."
                    )
                )
                return
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
            self._patch(write_error=self._unexpected_write_failure())

    def _settle_recovery(self):
        """After an unexpected failure, pause reads and sync only for a really
        uncertain physical write — the engine's journal or an open robbery
        binding says so — never for a preparation that left the save as it was."""
        engine = getattr(self.writes, "engine", None)
        try:
            pending = engine.pending() if engine is not None else ()
            self.save_activity.recovery_required = (
                any(r.status in ("RECOVERY_REQUIRED", "PREPARED") for r in pending)
                or self.writes._transfer_notice() is not None
            )
        except Exception:  # noqa: BLE001 - an unreadable journal is uncertainty
            self.save_activity.recovery_required = True
        return self.save_activity.recovery_required

    def _unexpected_write_failure(self):
        if self._settle_recovery():
            return "No se pudo verificar la operación. La sincronización queda pausada hasta comprobarla."
        return "No se pudo completar la operación. Tu partida no ha cambiado; vuelve a intentarlo."

    def _quick_step(self, name, args):
        self._patch(quick_item_result=None)
        try:
            self._quick_attempt(name, args)
        finally:
            with self.lock:
                self.value["quick_item_seq"] += 1

    def _quick_attempt(self, name, args):
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
            # Existing journal: verified backup, process check, readback, recovery.
            self.writes.offer(intent, closed_emulator_confirmed=True)
            if name == "quick_item_apply":
                self._apply_quick_item(intent, args)
            self._patch(quick_item_error=None, write_error=None)
        except SaveBusy:
            self._patch(
                quick_item_error="Hay una lectura o sincronización en curso. Espera unos segundos y vuelve a intentarlo."
            )
        except (NativeWriteError, WriteSafetyError) as error:
            self._patch(
                quick_item_error=QUICK_ERRORS.get(
                    str(error) or getattr(error, "code", ""),
                    "No se puede preparar el cambio. Revisa la partida seleccionada; no se ha modificado.",
                )
            )
        except Exception:  # noqa: BLE001 - no native output, path or journal data to UI
            self._patch(quick_item_error=self._unexpected_write_failure())

    def _apply_quick_item(self, intent, args):
        """The prepared change is applied at once: the engine re-checks that no
        emulator runs and that source, backup and staged bytes are exact, then
        re-reads the result natively. Anything else leaves the save as it was."""
        state = self.writes.state()
        if state["status"] != "AWAITING_CONFIRMATION" or not state["operation_id"]:
            raise WriteSafetyError("NATIVE_VERIFICATION_FAILED")
        operation = state["operation_id"]
        result = self.writes.confirm(operation, closed_emulator_confirmed=True)
        if result["status"] != "APPLIED_VERIFIED":
            error = None
            try:
                error = self.writes.engine.status(operation).error
            except Exception:  # noqa: BLE001 - the status below still decides
                pass
            if result["status"] == "RECOVERY_REQUIRED":
                raise RuntimeError("quick_item_recovery")
            raise WriteSafetyError(error or "NATIVE_VERIFICATION_FAILED")
        from app.launcher.quick_items import inventory_view

        # Counts are re-read from the written file, never assumed.
        self._patch(quick_items=None)
        self._load_local()
        try:
            data = self.writes.engine.files.read_path(Path(self.writes.selected()))
            view = inventory_view(self.writes.engine.native, data)
        except Exception:  # noqa: BLE001 - the change itself is verified
            view = None
        if view is not None:
            self._patch(
                quick_items=view | {"application_enabled": True},
            )
        self._patch(
            quick_item_result={
                "item": args["item"],
                "quantity": args["quantity"],
                "game": intent.game,
                "at": int(time.time()),
            }
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
                else QUICK_ERRORS.get(
                    str(error),
                    "No se pudo confirmar el cambio. Revisa la partida seleccionada y conserva las copias.",
                )
            )
        except Exception:  # no native output, private path or journal data to UI
            self._patch(write_error=self._unexpected_write_failure())
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
        if self.watch is None and self.core.config.selected_save:
            # A write that ended in any other way than a verified apply/restore
            # used to leave the save unwatched until the Launcher restarted.
            self._load_local()
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

    @staticmethod
    def _sync_scopes(data, receipt):
        """Owner rule (2026-10-28): the selected save is the trainer's active
        save on every screen, so it always goes to the personal record. The
        active season also gets it while it is the save that season accepts:
        same game and in-game trainer, or none bound yet. A season never
        silently changes the save (and Pokémon) it competes with."""
        scopes = [PERSONAL]
        season = data.get("season")
        if not season or data.get("mandatory_sync"):
            return scopes
        link = data.get("season_link") or {"status": "UNKNOWN"}
        if link.get("status") in ("OPEN", "UNKNOWN") or (
            link.get("status") == "BOUND"
            and link.get("identity") == save_identity(receipt)
        ):
            scopes.append(season["id"])
        return scopes

    @save_read
    def _enqueue_local(self):
        state = self.state()
        principal = state["principal"]
        receipt = self.receipt
        if not (
            state["cloud_sync"]
            and principal
            and state["cloud"]
            and receipt
            and state["local_status"] == "READY"
        ):
            return
        origin, trainer = self.client.origin, principal["trainer_id"]
        raw_hash = receipt.fingerprint.sha256
        scopes = self._sync_scopes(state["cloud"].get("data") or {}, receipt)
        try:
            missing = [s for s in scopes if not self.store.has(origin, trainer, s, raw_hash)]
            if missing:
                snapshot = SnapshotReader().read(SaveSource.enroll(state["selected_save"]))
                for scope in missing:
                    self.store.enqueue_raw(origin, trainer, scope, receipt, snapshot.data)
                self._cloud_wake.set()
            accepted = self.store.receipt(origin, trainer, PERSONAL, raw_hash)
            in_season = next((s for s in scopes if s != PERSONAL), None)
            season_accepted = (
                self.store.receipt(origin, trainer, in_season, raw_hash)
                if in_season
                else None
            )
            self._patch(
                cloud_receipt=accepted.model_dump() if accepted else None,
                season_receipt=season_accepted.model_dump() if season_accepted else None,
                outbox=self.store.summary(origin, trainer),
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
        link = None
        if season:
            from uuid import UUID

            sid = str(UUID(season["id"]))
            link = self._season_link(sid)
        if season and link["status"] != "NOT_PARTICIPANT":
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
            # Whether, and with which save, this trainer plays the active season.
            "season_link": link,
            "wallet": wallet,
            "item_uses": item_uses,
            "transfers": transfers,
            # 27A: a decided robbery's removal comes before any ordinary season
            # sync; the personal record (no competitive effect) still syncs.
            "mandatory_sync": any(t["mandatory"] for t in transfers or []),
        }
        self.store.save_cache(self.client.origin, principal.trainer_id, data)
        self._patch(
            cloud=self.store.cache(self.client.origin, principal.trainer_id),
            last_online=time.time(),
        )
        self.next_cloud_refresh = time.monotonic() + 120
        # Only the locally ready selected save is eligible; never upload old/missing cache as new.
        self._enqueue_local()
        self._deliver_pending(principal.trainer_id)
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
        in_season = self.state()["season_receipt"]
        if in_season:
            # Same proof for the season copy; another device's newer season
            # save is reported on the season line, never as a sync failure.
            latest = self.session.request(
                "GET",
                f"{save_paths(in_season['season_id'])[0]}/receipt?sha256={in_season['sha256']}",
            )
            if (
                not latest.get("is_current")
                or latest.get("save_id") != in_season["save_id"]
            ):
                self._patch(season_receipt=None)
                self._season_refused(BackendError("SAVE_SUPERSEDED"))
        self._patch(
            outbox=self.store.summary(self.client.origin, principal.trainer_id),
            cloud_status="ONLINE",
            last_online=time.time(),
            error=None,
            error_detail=None,
            **({"last_synced": time.time()} if accepted else {}),
        )

    def _season_link(self, sid):
        """Does this trainer play the active season, and with which save?
        Read from the season's own save context: 403 means not enrolled, 409
        means no longer playing (withdrawn, or the season stopped accepting)."""
        try:
            context = self.session.request("GET", f"/v1/seasons/{sid}/saves/context")
        except BackendError as exc:
            if str(exc) == "FORBIDDEN":
                return {"status": "NOT_PARTICIPANT"}
            if str(exc) == "OBSERVATION_REJECTED":
                return {"status": "CLOSED", "reason": exc.detail}
            raise
        if not isinstance(context, dict) or "save_identity" not in context:
            return {"status": "UNKNOWN"}  # an API that does not say it yet
        identity = context["save_identity"]
        if not isinstance(identity, dict):
            return {"status": "OPEN"}
        return {"status": "BOUND", "game": identity.get("game"), "identity": identity}

    def _season_refused(self, exc):
        """The season kept its own save: remember why, for the UI, until the
        next refresh reads its context again."""
        detail = getattr(exc, "detail", None)
        status = (
            "NOT_PARTICIPANT"
            if str(exc) == "FORBIDDEN"
            else "SUPERSEDED"
            if str(exc) == "SAVE_SUPERSEDED"
            else "OTHER_SAVE"
            if detail
            in ("SAVE_TRAINER_MISMATCH", "SAVE_IDENTITY_CHANGED", "SAVE_IDENTITY_OTHER_OWNER")
            else "REFUSED"
        )
        with self.lock:
            cloud = deepcopy(self.value.get("cloud"))
            if not cloud or not isinstance(cloud.get("data"), dict):
                return
            link = dict(cloud["data"].get("season_link") or {})
            link.update(status=status, reason=detail or str(exc))
            cloud["data"]["season_link"] = link
            self.value["cloud"] = cloud

    def _deliver_pending(self, trainer):
        """Every queued row, oldest first, in one pass (bounded). A season that
        refuses the save never stops the personal record from syncing."""
        origin = self.client.origin
        for _ in range(8):
            row = self.store.pending(origin, trainer)
            if row is None:
                break
            current, state = self.receipt, self.state()
            scopes = (
                self._sync_scopes((state["cloud"] or {}).get("data") or {}, current)
                if current
                else []
            )
            ready = (
                current is not None
                and state["local_status"] == "READY"
                and state["cloud_sync"]
            )
            self._patch(syncing=True)
            try:
                delivered = deliver_trusted(
                    self.session,
                    self.store,
                    row,
                    selected_hash=current.fingerprint.sha256
                    if ready and row["season"] in scopes
                    else None,
                )
            except BackendError as exc:
                code = str(exc)
                if row["season"] != PERSONAL and code in (
                    "FORBIDDEN",
                    "SAVE_REJECTED",
                    "OBSERVATION_REJECTED",
                    "SAVE_SUPERSEDED",
                ):
                    self.store.block(row)
                    self._season_refused(exc)
                    continue
                if code == "SAVE_SUPERSEDED":
                    continue  # that row is blocked; a newer one may follow
                if code in ("OBSERVATION_REJECTED", "SAVE_REJECTED", "SAVE_RECEIPT_MISMATCH"):
                    self.store.block(row)
                raise
            finally:
                self._patch(syncing=False)
            if delivered is not None and current is not None and (
                delivered.sha256 == current.fingerprint.sha256
            ):
                key = "cloud_receipt" if row["season"] == PERSONAL else "season_receipt"
                self._patch(**{key: delivered.model_dump()})
        self._enqueue_local()

    def _cloud_loop(self):
        next_attempt, failures, last_attempt = 0.0, 0, float("-inf")
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
                            season_receipt=None,
                            last_synced=None,
                            auth_status="LOGIN_REQUIRED",
                            cloud_sync=False,
                            error=None,
                            error_detail=None,
                        )
                    elif name == "login":
                        self._patch(
                            auth_status="CHECKING",
                            cloud=None,
                            principal=None,
                            cloud_receipt=None,
                            season_receipt=None,
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
                if self._cloud_wake.is_set():
                    self._cloud_wake.clear()
                    # A local change or a web token request runs the next step
                    # now; a failure backoff is never shortened below 5 s.
                    now = time.monotonic()
                    next_attempt = min(
                        next_attempt, max(now, last_attempt + 5) if failures else now
                    )
                if time.monotonic() < next_attempt:
                    continue
                last_attempt = time.monotonic()
                self._cloud_step()
                failures, next_attempt = 0, time.monotonic() + 30
            except SaveBusy:
                continue  # no upload/reimport overlaps a physical write/recovery
            except BackendError as exc:
                code = str(exc)
                if code in SESSION_ENDED:
                    # Only a rejected session or a disabled account signs out:
                    # a refused resource (403) or a slow answer never does.
                    self.session.logout()
                    self.tokens.clear()
                    with self.lock:
                        self._web_token = None
                    self._patch(auth_status="LOGIN_REQUIRED", principal=None)
                failures += 1
                # Recover unattended after an outage. Each upload still reconciles
                # its exact receipt/CAS before retry; semantic rejection stays blocked.
                next_attempt = time.monotonic() + min(60, 5 * 3 ** min(failures - 1, 3))
                if not self.session._principal:
                    self._patch(auth_status="LOGIN_REQUIRED")
                # One slow or failed answer is not "offline": two in a row are.
                offline = code == "BACKEND_UNAVAILABLE" and failures >= 2
                self._patch(
                    error=code,
                    error_detail=getattr(exc, "detail", None),
                    **({"cloud_status": "OFFLINE"} if offline else {}),
                )
            except Exception:  # noqa: BLE001 - isolate cloud/storage failures from local browsing
                failures += 1
                next_attempt = time.monotonic() + 60
                self._patch(
                    error="SYNC_UNAVAILABLE",
                    **({"cloud_status": "OFFLINE"} if failures >= 2 else {}),
                )

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=90)
        self.client.close()
