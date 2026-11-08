"""Administración › Avisos: compare each accepted save with its predecessor.

Runs on its own worker after a save is registered, so a sync never waits for
it and never fails because of it. The analysis only reads: the parsed saves
already in the database and, for the bag, a read-only native inspection of the
accepted bytes. Saves are processed in their attested chain order and the
database keeps one analysis per save, so a replay or a retry adds nothing.
Nothing here can block, sanction or modify anything.
"""

import logging
import queue
import threading

from app.domain.save_audit import DETECTOR_VERSION, analyze, identity_key

log = logging.getLogger(__name__)


def snapshot_facts(reading):
    """Reduce a native reading to what later comparisons need."""
    items, pouches = {}, {}
    for pouch in reading["pouches"]:
        for entry in pouch["items"]:
            key = str(entry["id"])
            items[key] = items.get(key, 0) + entry["count"]
            pouches[key] = pouch["type"]
    friendship = {}
    for member in reading["pokemon"]:
        key = identity_key({"pid": member["pid"], "encryption_constant": member["ec"]})
        if key:
            friendship[key] = member["friendship"]
    return {"items": items, "pouches": pouches}, friendship


class SaveAudit:
    def __init__(self, repository, reader, *, batch=40):
        self.repository, self.reader, self.batch = repository, reader, batch
        self._running = threading.Lock()
        self._queue: queue.Queue = queue.Queue(maxsize=64)
        self._worker = None

    # Worker ---------------------------------------------------------------------
    def enqueue(self, season_id, trainer_id):
        """Best effort: a full queue is simply picked up by the next run."""
        try:
            self._queue.put_nowait((str(season_id), str(trainer_id)))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._drain, name="save-audit", daemon=True)
                self._worker.start()
        except queue.Full:
            log.info("save_audit_queue_full")

    def _drain(self):
        while True:
            season_id, trainer_id = self._queue.get()
            try:
                self.run(season_id, trainer_id, wait=True)
            except Exception:  # a worker failure must never surface anywhere
                log.exception("save_audit_worker_failed")

    # Analysis -------------------------------------------------------------------
    def run(self, season_id=None, trainer_id=None, *, wait=False):
        """Analyse what is pending, oldest first; one trainer's failure stops only them."""
        if not self._running.acquire(blocking=wait):
            return {"processed": 0, "failed": 0, "busy": True}
        processed = failed = 0
        try:
            pending = self.repository.pending(season_id, trainer_id, self.batch) or []
            stopped = set()
            for entry in pending:
                scope = (entry["season_id"], entry["trainer_id"])
                if scope in stopped:
                    continue
                try:
                    self._analyze(entry)
                    processed += 1
                except Exception:
                    log.exception("save_audit_analysis_failed")
                    failed += 1
                    stopped.add(scope)
            return {"processed": processed, "failed": failed, "busy": False}
        finally:
            self._running.release()

    def _facts(self, saved):
        """Bag and friendship of one accepted save, or unknown. Unknown is never zero."""
        try:
            return snapshot_facts(self.reader.audit_snapshot(self.repository.read_raw(saved)))
        except Exception:  # an unreadable bag only skips the inventory comparison
            log.warning("save_audit_facts_unavailable")
            return None, None

    def _analyze(self, entry):
        season_id, trainer_id, save_id = entry["season_id"], entry["trainer_id"], entry["save_file_id"]
        context = self.repository.context(season_id, trainer_id, save_id)
        current, previous = context["current"], context["previous"]
        bag, friendship = self._facts(current["save"])
        request = {
            "season_id": season_id,
            "trainer_id": trainer_id,
            "save_file_id": save_id,
            "previous_save_file_id": previous["save"]["id"] if previous else None,
            "game": current["payload"].get("game", ""),
            "bag": bag,
            "friendship": friendship,
            "detector_version": DETECTOR_VERSION,
        }
        if previous is None:
            # The trainer's first save of the season: the reference, nothing to compare.
            self.repository.record(
                request | {"status": "baseline", "inventory_status": "baseline", "notices": [], "credited_deliveries": []}
            )
            return
        previous_bag, previous_friendship = previous.get("bag"), previous.get("friendship")
        if previous_bag is None:
            previous_bag, previous_friendship = self._facts(previous["save"])
        result = analyze(
            {
                "payload": previous["payload"],
                "uploaded_at": previous["save"]["uploaded_at"],
                "bag": previous_bag,
                "friendship": previous_friendship,
            },
            {
                "payload": current["payload"],
                "uploaded_at": current["save"]["uploaded_at"],
                "bag": bag,
                "friendship": friendship,
            },
            context["operations"],
        )
        compared = {
            "previous": {
                "save_file_id": previous["save"]["id"],
                "sha256": previous["save"]["sha256"],
                "uploaded_at": previous["save"]["uploaded_at"],
                "revision": previous["revision"],
            },
            "current": {
                "save_file_id": current["save"]["id"],
                "sha256": current["save"]["sha256"],
                "uploaded_at": current["save"]["uploaded_at"],
                "revision": current["revision"],
            },
            "inventory_status": result["inventory_status"],
        }
        self.repository.record(
            request
            | {
                "status": "analyzed",
                "inventory_status": result["inventory_status"],
                "notices": [notice | {"compared": compared} for notice in result["notices"]],
                "credited_deliveries": result["credited_deliveries"],
            }
        )
