"""Scope-bound cache and immutable outbox in the existing local SQLite journal."""

import json
import time

from app.launcher.journal import LocalConflict
from app.save_parser.cloud import CloudObservation, ObservationReceipt


class CloudStore:
    def __init__(self, journal):
        self.journal = journal
        with journal.connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS cloud_cache (
                origin TEXT NOT NULL, trainer TEXT NOT NULL, payload TEXT NOT NULL,
                refreshed REAL NOT NULL, PRIMARY KEY(origin,trainer));
              CREATE TABLE IF NOT EXISTS cloud_outbox (
                origin TEXT NOT NULL, trainer TEXT NOT NULL, season TEXT NOT NULL,
                id TEXT NOT NULL, body TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                receipt TEXT, blocked INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(origin,trainer,season,id));
            """)

    def cache(self, origin, trainer):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT payload,refreshed FROM cloud_cache WHERE origin=? AND trainer=?",
                (origin, trainer),
            ).fetchone()
        return (
            {"data": json.loads(row["payload"]), "refreshed_at": row["refreshed"]}
            if row
            else None
        )

    def save_cache(self, origin, trainer, data):
        with self.journal.connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO cloud_cache VALUES (?,?,?,?)",
                (origin, trainer, json.dumps(data), time.time()),
            )

    def enqueue(self, origin, trainer, season, body: CloudObservation):
        oid = body.identifier(trainer, season)
        with self.journal.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT body FROM cloud_outbox WHERE origin=? AND trainer=? AND season=? AND id=?",
                (origin, trainer, season, oid),
            ).fetchone()
            if existing:
                if existing["body"] != body.model_dump_json():
                    raise LocalConflict("OUTBOX_CONFLICT")
                return oid
            count = db.execute(
                "SELECT count(*) FROM cloud_outbox WHERE receipt IS NULL"
            ).fetchone()[0]
            if count >= 64:
                raise LocalConflict("OUTBOX_FULL")
            db.execute(
                "INSERT INTO cloud_outbox(origin,trainer,season,id,body) VALUES (?,?,?,?,?)",
                (origin, trainer, season, oid, body.model_dump_json()),
            )
        return oid

    def pending(self, origin, trainer):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT * FROM cloud_outbox WHERE origin=? AND trainer=? AND receipt IS NULL "
                "AND attempts<5 AND blocked=0 ORDER BY rowid LIMIT 1",
                (origin, trainer),
            ).fetchone()
        return dict(row) if row else None

    def receipt(self, origin, trainer, season, oid):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT receipt FROM cloud_outbox WHERE origin=? AND trainer=? AND season=? AND id=?",
                (origin, trainer, season, oid),
            ).fetchone()
        return (
            ObservationReceipt.model_validate_json(row["receipt"])
            if row and row["receipt"]
            else None
        )

    def attempt(self, row):
        with self.journal.connection() as db:
            db.execute(
                "UPDATE cloud_outbox SET attempts=attempts+1 WHERE origin=? AND trainer=? AND season=? AND id=?",
                tuple(row[k] for k in ("origin", "trainer", "season", "id")),
            )

    def accept(self, row, raw):
        receipt = ObservationReceipt.model_validate(raw)
        body = CloudObservation.model_validate_json(row["body"])
        if (
            receipt.id,
            receipt.trainer_id,
            receipt.season_id,
            receipt.payload_digest,
        ) != (row["id"], row["trainer"], row["season"], body.digest()):
            raise LocalConflict("RECEIPT_MISMATCH")
        with self.journal.connection() as db:
            db.execute(
                "UPDATE cloud_outbox SET receipt=? WHERE origin=? AND trainer=? AND season=? AND id=?",
                (
                    receipt.model_dump_json(),
                    *(row[k] for k in ("origin", "trainer", "season", "id")),
                ),
            )
            # Keep bounded local receipts; server receipt remains reconcilable by deterministic ID.
            db.execute(
                "DELETE FROM cloud_outbox WHERE receipt IS NOT NULL AND rowid NOT IN "
                "(SELECT rowid FROM cloud_outbox WHERE receipt IS NOT NULL ORDER BY rowid DESC LIMIT 64)"
            )
        return receipt

    def block(self, row):
        with self.journal.connection() as db:
            db.execute(
                "UPDATE cloud_outbox SET blocked=1 WHERE origin=? AND trainer=? AND season=? AND id=?",
                tuple(row[k] for k in ("origin", "trainer", "season", "id")),
            )

    def retry(self, origin, trainer):
        with self.journal.connection() as db:
            db.execute(
                "UPDATE cloud_outbox SET attempts=0 WHERE origin=? AND trainer=? AND blocked=0 AND receipt IS NULL",
                (origin, trainer),
            )

    def summary(self, origin, trainer):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT count(*) pending,coalesce(sum(attempts>=5 OR blocked=1),0) paused "
                "FROM cloud_outbox WHERE origin=? AND trainer=? AND receipt IS NULL",
                (origin, trainer),
            ).fetchone()
        return dict(row)


def deliver(session, store, row):
    """Always reconcile before PUT, including after process death/unknown outcome."""
    path = f"/v1/launcher/seasons/{row['season']}/observations/{row['id']}"
    store.attempt(row)
    receipt = session.request("GET", path, missing=True)
    if receipt is None:
        receipt = session.request("PUT", path, body=json.loads(row["body"]))
    return store.accept(row, receipt)
