"""Durable original bytes + immutable upload intent, separate from the private inbox."""

from hashlib import sha256
from urllib.parse import urlencode

from app.launcher.backend import BackendError
from app.launcher.cloud_store import CloudStore
from app.launcher.journal import LocalConflict
from app.save_parser.registration import SaveRegistration, observation_digest


class TrustedStore(CloudStore):
    def __init__(self, journal):
        super().__init__(journal)
        with journal.connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS trusted_save_consent (
                origin TEXT NOT NULL, trainer TEXT NOT NULL,
                PRIMARY KEY(origin,trainer));
              CREATE TABLE IF NOT EXISTS trusted_save_outbox (
                origin TEXT NOT NULL, trainer TEXT NOT NULL, season TEXT NOT NULL,
                id TEXT NOT NULL, digest TEXT NOT NULL, raw BLOB,
                expected TEXT, prepared INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0,
                receipt TEXT, verified INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(origin,trainer,season,id));
            """)

    def enabled(self, origin, trainer):
        with self.journal.connection() as db:
            return (
                db.execute(
                    "SELECT 1 FROM trusted_save_consent WHERE origin=? AND trainer=?",
                    (origin, trainer),
                ).fetchone()
                is not None
            )

    def other_consent(self, origin, trainer):
        """Another trainer already synced from this Launcher profile."""
        with self.journal.connection() as db:
            return (
                db.execute(
                    "SELECT 1 FROM trusted_save_consent WHERE origin=? AND trainer<>?",
                    (origin, trainer),
                ).fetchone()
                is not None
            )

    def enable(self, origin, trainer):
        with self.journal.connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO trusted_save_consent VALUES (?,?)",
                (origin, trainer),
            )

    @staticmethod
    def scope(row):
        return tuple(row[k] for k in ("origin", "trainer", "season", "id"))

    def enqueue_raw(self, origin, trainer, season, local, data):
        raw_hash = sha256(data).hexdigest()
        if raw_hash != local.fingerprint.sha256 or len(data) != local.fingerprint.size:
            raise LocalConflict("SAVE_CHANGED_DURING_READ")
        digest = observation_digest(local.observation, local.parser_version)
        with self.journal.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM trusted_save_outbox WHERE origin=? AND trainer=? AND season=? AND id=?",
                (origin, trainer, season, raw_hash),
            ).fetchone()
            if row:
                if row["digest"] != digest:
                    raise LocalConflict("SAVE_PARSE_MISMATCH")
                return raw_hash
            # Unattempted, obsolete snapshots have no possible remote outcome.
            db.execute(
                "DELETE FROM trusted_save_outbox WHERE origin=? AND trainer=? AND season=? AND attempts=0 AND verified=0",
                (origin, trainer, season),
            )
            if (
                db.execute(
                    "SELECT count(*) FROM trusted_save_outbox WHERE raw IS NOT NULL"
                ).fetchone()[0]
                >= 8
            ):
                raise LocalConflict("OUTBOX_FULL")
            db.execute(
                "INSERT INTO trusted_save_outbox(origin,trainer,season,id,digest,raw) VALUES (?,?,?,?,?,?)",
                (origin, trainer, season, raw_hash, digest, data),
            )
        return raw_hash

    def pending(self, origin, trainer):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT * FROM trusted_save_outbox WHERE origin=? AND trainer=? AND verified=0 "
                "AND blocked=0 ORDER BY rowid LIMIT 1",
                (origin, trainer),
            ).fetchone()
        return dict(row) if row else None

    def receipt(self, origin, trainer, season, oid):
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT receipt FROM trusted_save_outbox WHERE origin=? AND trainer=? AND season=? AND id=? AND verified=1",
                (origin, trainer, season, oid),
            ).fetchone()
        return SaveRegistration.model_validate_json(row["receipt"]) if row else None

    def update(self, row, **fields):
        if not set(fields) <= {
            "attempts",
            "expected",
            "prepared",
            "blocked",
            "receipt",
            "verified",
            "raw",
        }:
            raise ValueError("invalid_outbox_update")
        with self.journal.connection() as db:
            db.execute(
                "UPDATE trusted_save_outbox SET "
                + ",".join(k + "=?" for k in fields)
                + " WHERE origin=? AND trainer=? AND season=? AND id=?",
                (*fields.values(), *self.scope(row)),
            )

    def block(self, row):
        self.update(row, blocked=1)

    def retry(self, origin, trainer):
        with self.journal.connection() as db:
            db.execute(
                "UPDATE trusted_save_outbox SET attempts=0 WHERE origin=? AND trainer=? AND blocked=0 AND verified=0",
                (origin, trainer),
            )

    def summary(self, origin, trainer):
        with self.journal.connection() as db:
            return dict(
                db.execute(
                    "SELECT count(*) pending,coalesce(sum(blocked=1),0) paused "
                    "FROM trusted_save_outbox WHERE origin=? AND trainer=? AND verified=0",
                    (origin, trainer),
                ).fetchone()
            )


# Outside an active season the save goes to the trainer's personal record
# (/v1/me/save, migration 065): same protocol, its own readback (/v1/me/pc).
PERSONAL = "personal"


def save_paths(season):
    if season == PERSONAL:
        return "/v1/me/save", "/v1/me/pc"
    return f"/v1/seasons/{season}/saves", f"/v1/read/seasons/{season}/pc"


def deliver_trusted(session, store, row, *, selected_hash):
    """GET receipt first, retain acceptance before readback, never renew a stale CAS."""
    base, pc_path = save_paths(row["season"])
    store.update(row, attempts=row["attempts"] + 1)
    raw = session.request(
        "GET", base + "/receipt?" + urlencode({"sha256": row["id"]}), missing=True
    )
    if raw is None:
        if row["id"] != selected_hash:
            store.update(row, blocked=1, raw=None)
            return None
        if not row["prepared"]:
            context = session.request("GET", base + "/context")
            if "current_save_id" not in context:
                raise BackendError("BACKEND_UNAVAILABLE")
            row["expected"] = context["current_save_id"]
            store.update(row, expected=row["expected"], prepared=1)
        raw = session.upload(
            base
            + "/raw?"
            + urlencode(
                {
                    "sha256": row["id"],
                    "observation_digest": row["digest"],
                    "expected_save_id": row["expected"] or "none",
                }
            ),
            row["raw"],
        )
    receipt = SaveRegistration.model_validate(raw)
    if (
        receipt.trainer_id,
        receipt.season_id,
        receipt.sha256,
        receipt.observation_digest,
    ) != (row["trainer"], row["season"], row["id"], row["digest"]):
        raise BackendError("SAVE_RECEIPT_MISMATCH")
    store.update(row, receipt=receipt.model_dump_json())
    if not receipt.is_current:
        store.update(row, blocked=1, raw=None)
        raise BackendError("SAVE_SUPERSEDED")
    pc = session.request("GET", pc_path)
    if (
        pc.get("status") != "ready"
        or (pc.get("save") or {}).get("id") != receipt.save_id
    ):
        raise BackendError("SAVE_READBACK_PENDING")
    store.update(row, verified=1, raw=None)
    with store.journal.connection() as db:
        db.execute(
            "DELETE FROM trusted_save_outbox WHERE verified=1 AND rowid NOT IN "
            "(SELECT rowid FROM trusted_save_outbox WHERE verified=1 ORDER BY rowid DESC LIMIT 64)"
        )
    return receipt
