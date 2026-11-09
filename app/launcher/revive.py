"""«Revivir Pokémon» desde el Launcher (decisión del propietario, 2026-11-09).

The server authorizes the attempt and the claim; the local engine moves the
Pokémon with its usual protections (emulator closed, exact bytes, verified
backup, durable journal, native re-read); the hosted verifier proves the result
independently; only then does the server consume the comodín. The death and its
NET penalty are never touched: they live in the server's immutable history.
"""

from hashlib import sha256
from pathlib import Path
from time import monotonic, sleep
from uuid import UUID, uuid4

from app.domain.revive_plan import revive_destination, revive_mutation, trainer_key
from app.launcher.backend import BackendError
from app.launcher.item_use import (
    SETTLED_STATES,
    AuthenticatedItemResultTransport,
    EngineeringItemUse,
)
from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WriteSafetyError
from app.save_parser.adapter import PkhexProcessParser

KIND = "revive"
VERIFY_WAIT_SECONDS = 150.0
VERIFY_POLL_SECONDS = 4.0

MESSAGES = {
    "NO_VOUCHER": "No tienes comodines Revivir disponibles.",
    "NO_TARGETS": "No hay Pokémon muertos válidos en la Caja {box}.",
    "SAVE_CHANGED": "La partida ha cambiado desde que seleccionaste este Pokémon.",
    "NOT_SYNCED": "Tu partida tiene cambios sin sincronizar. Espera a que se sincronice y vuelve a intentarlo.",
    "NO_LEAGUE_SAVE": "Tu partida de la Liga todavía no está disponible. Sincronízala con el Launcher.",
    "NO_FREE_SLOT": "No hay ningún hueco libre en las Cajas 1 a {limit}. Libera uno y vuelve a intentarlo; el comodín no se ha gastado.",
    "EMULATOR_RUNNING": "Debes cerrar el juego antes de aplicar esta operación.",
    "DONE": "La operación se ha completado correctamente.",
    "VERIFYING": "Revivido en tu partida. PokeApp lo está verificando; el comodín se gastará al confirmarlo.",
    "RELEASED": "No se ha podido verificar. Tu partida ha vuelto a como estaba y el comodín no se ha gastado.",
    "RECOVERY": "Hay una operación pendiente de comprobar. Mantén el juego cerrado y vuelve a abrir esta ventana.",
}


class ReviveRemote:
    """The trainer's own session: the server derives the trainer from it."""

    def __init__(self, session, season_id, trainer_id):
        self.session = session
        self.sid, self.tid = str(UUID(season_id)), str(UUID(trainer_id))

    def _items(self, aid, step=""):
        return f"/v1/launcher/seasons/{self.sid}/item-uses/{UUID(aid)}{step}"

    def board(self):
        return self.session.request(
            "GET", f"/v1/launcher/seasons/{self.sid}/revive", missing=True
        )

    def prepare(self, purchase_id, entity_id, save_id, save_sha256, operation_id):
        return self.session.request(
            "PUT",
            f"/v1/launcher/seasons/{self.sid}/revive/{UUID(purchase_id)}",
            body={
                "pokemon_entity_id": entity_id,
                "save_file_id": save_id,
                "save_sha256": save_sha256,
                "operation_id": operation_id,
            },
        )

    def _scope(self, sid, tid):
        if sid != self.sid or tid != self.tid:
            raise WriteSafetyError("ITEM_BINDING_MISMATCH")

    def claim(self, aid, sid, tid, request):
        self._scope(sid, tid)
        return self.session.request("PUT", self._items(aid, "/claim"), body=request)

    def complete(self, aid, sid, tid, request):
        self._scope(sid, tid)
        return self.session.request("PUT", self._items(aid), body=request)


class LauncherRevive:
    def __init__(self, controller, remote, *, session):
        self.controller, self.remote = controller, remote
        self.engine = controller.engine
        self.transport = AuthenticatedItemResultTransport(session)
        self.bridge = EngineeringItemUse(
            controller, remote, season_id=remote.sid, trainer_id=remote.tid
        )
        self.parser = PkhexProcessParser(Path(self.engine.native.executable))

    def _read(self):
        data = self.engine.files.read_path(Path(self.controller.selected()))
        return data, sha256(data).hexdigest(), self.parser.parse(data)

    def view(self):
        board = self.remote.board()
        if board is None:
            raise WriteSafetyError("REVIVE_UNAVAILABLE")
        data, digest, observation = self._read()
        dead_box = board["dead_box_number"]
        box = next((b for b in observation.boxes if b.number == dead_box), None)
        saved = board["save"]
        candidates = []
        for target in board["targets"]:
            pokemon = box.slots[target["slot_number"] - 1] if box else None
            if pokemon is None or pokemon.is_egg:
                continue
            candidates.append(
                {
                    "pokemon_entity_id": target["pokemon_entity_id"],
                    "slot_number": target["slot_number"],
                    "species": pokemon.species_id,
                    "form": pokemon.form,
                    "nickname": pokemon.nickname,
                    "level": pokemon.level,
                }
            )
        purchases = [p["id"] for p in board["purchases"] if p["authorization"] is None or p["authorization"]["status"] == "FAILED_RECOVERABLE"]
        return {
            "application_enabled": self.engine.allows(KIND),
            "dead_box_number": dead_box,
            "free_slot": revive_destination(observation.boxes, dead_box) is not None,
            "in_sync": saved is not None and saved["sha256"] == digest,
            "official_save": saved is not None,
            "voucher_count": len(board["purchases"]),
            "purchases": purchases,
            "candidates": candidates,
            "game": observation.game,
        }

    def apply(self, purchase_id, entity_id):
        """Prepare, apply locally, prove and complete, in one continuous flow."""
        self.engine.files.assert_closed(True)
        board = self.remote.board()
        if board is None:
            raise WriteSafetyError("REVIVE_UNAVAILABLE")
        saved = board["save"]
        if saved is None:
            return self._refused("NO_LEAGUE_SAVE")
        dead_box = board["dead_box_number"]
        if not any(p["id"] == purchase_id for p in board["purchases"]):
            return self._refused("NO_VOUCHER")
        # Compared before parsing: a changed file is never read as a plan.
        data = self.engine.files.read_path(Path(self.controller.selected()))
        digest = sha256(data).hexdigest()
        if saved["sha256"] != digest:
            return self._refused("SAVE_CHANGED")
        observation = self.parser.parse(data)
        target = next(
            (t for t in board["targets"] if t["pokemon_entity_id"] == entity_id), None
        )
        box = next((b for b in observation.boxes if b.number == dead_box), None)
        pokemon = box.slots[target["slot_number"] - 1] if target and box else None
        if pokemon is None:
            return self._refused("SAVE_CHANGED")
        destination = revive_destination(observation.boxes, dead_box)
        if destination is None:
            return self._refused("NO_FREE_SLOT", dead_box)
        identity = pokemon.identity
        authorization = self.remote.prepare(
            purchase_id, entity_id, saved["id"], digest, str(uuid4())
        )
        intent = WriteIntent.create(
            game=observation.game,
            expected_sha256=digest,
            trainer_key=trainer_key(observation),
            mutation=revive_mutation(
                dead_box,
                target["slot_number"],
                identity.pid,
                identity.encryption_constant,
                destination,
                authorization["id"],
            ),
        )
        self.bridge.bind_revive(authorization, intent, pokemon_entity_id=entity_id)
        return self._drive(authorization["id"], pokemon, dead_box)

    def _drive(self, aid, pokemon=None, dead_box=None):
        bridge = self.bridge
        try:
            state = bridge.apply(aid, closed_emulator_confirmed=True)
        except BackendError as error:
            # The server will never accept this attempt (expired, superseded,
            # conflicting): release it instead of holding the sync back forever.
            if error.status not in (403, 404, 409):
                raise
            final = bridge.release(aid, code="AUTHORIZATION_REFUSED")
            return self._done(
                "RELEASED" if final == "RELEASED" else "RECOVERY", pokemon
            )
        if state == "LOCAL_REJECTED":
            bridge.release(aid, code="LOCAL_WRITE_REJECTED")
            return self._done("RELEASED", pokemon)
        if state != "LOCAL_VERIFIED_AWAITING_CONFIRMATION":
            return self._done("RECOVERY", pokemon)
        deadline = monotonic() + VERIFY_WAIT_SECONDS
        while True:
            status = bridge.submit_verification(aid, self.transport)
            if status == "VERIFIED":
                break
            if status in ("REJECTED", "EXPIRED"):
                final = bridge.release(aid, code="VERIFICATION_" + status)
                return self._done(
                    "RELEASED" if final == "RELEASED" else "RECOVERY", pokemon
                )
            if status == "RECOVERY_REQUIRED":
                return self._done("RECOVERY", pokemon)
            if monotonic() >= deadline:
                return self._done("VERIFYING", pokemon)
            sleep(VERIFY_POLL_SECONDS)
        final = bridge.complete(aid)
        if final == "APPLIED_VERIFIED":
            return self._done("DONE", pokemon, dead_box)
        if final == "BLOCKED_UNCERTAIN":
            final = bridge.release(aid, code="COMPLETION_BLOCKED")
            return self._done(
                "RELEASED" if final == "RELEASED" else "RECOVERY", pokemon
            )
        return self._done("RECOVERY", pokemon)

    def resume(self):
        """An interrupted operation continues from the journal, never from zero."""
        results = []
        for aid, record in self.bridge.bindings():
            if record["state"] not in SETTLED_STATES:
                results.append(self._drive(aid))
        return results

    @staticmethod
    def _refused(key, dead_box=None):
        limit = min(dead_box - 1, 7) if dead_box else 6
        return {
            "status": key,
            "message": MESSAGES[key].format(box=dead_box or 7, limit=limit),
            "completed": False,
        }

    @staticmethod
    def _done(key, pokemon=None, dead_box=None):
        result = {
            "status": key,
            "message": MESSAGES[key],
            "completed": key == "DONE",
        }
        if key == "DONE" and pokemon is not None:
            result["pokemon"] = {
                "species": pokemon.species_id,
                "form": pokemon.form,
                "nickname": pokemon.nickname,
                "level": pokemon.level,
            }
        return result
