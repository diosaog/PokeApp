"""Service-role access to the Discord announcement outbox (067) and the
confirmed records it is rendered from. Rows are queued only by database
triggers; the API claims, delivers and closes them."""

from datetime import datetime

from app.repositories.errors import PersistenceError

TABLE = "discord_announcements"
COLUMNS = "id,kind,season_id,subject,status,revision,delivered_revision,attempts,discord_message_id,created_at,claimed_at"
# Every source read is bounded, below the API's 1000-row cap so that a
# truncated answer is detected instead of read as complete.
READ_LIMIT = 999


def _iso(stamp: datetime) -> str:
    return stamp.isoformat()


class SupabaseAnnouncementRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def _run(self, query):
        try:
            data = query.execute().data
        except Exception as error:  # noqa: BLE001 - transport boundary, no detail leaks
            raise PersistenceError("announcements_unavailable") from error
        if not isinstance(data, list):
            raise PersistenceError("announcements_invalid")
        return data

    def rows(self, table, columns, **filters):
        query = self._client.table(table).select(columns)
        for key, value in filters.items():
            if key.endswith("__lte"):
                query = query.lte(key.removesuffix("__lte"), value)
            elif value is None:
                query = query.is_(key, "null")
            elif isinstance(value, (list, tuple)):
                query = query.in_(key, list(value))
            else:
                query = query.eq(key, value)
        rows = self._run(
            query.order(columns.split(",")[0].split(":")[0]).range(0, READ_LIMIT)
        )
        if len(rows) > READ_LIMIT:
            raise PersistenceError("announcement_source_too_large")
        return rows

    def recover(self, cutoff):
        """A claim older than the lease belongs to a process that died mid-send."""
        stale = self._run(
            self._client.table(TABLE)
            .select("id,discord_message_id,claimed_at")
            .eq("status", "sending")
            .lt("claimed_at", _iso(cutoff))
        )
        for row in stale:
            # A post may have reached Discord: never again. An edit can be redone.
            status = "sent" if row["discord_message_id"] else "uncertain"
            self._run(
                self._client.table(TABLE)
                .update({"status": status, "last_error": "interrupted"})
                .eq("id", row["id"])
                .eq("status", "sending")
                .eq("claimed_at", row["claimed_at"])
            )

    def expire(self, cutoff):
        self._run(
            self._client.table(TABLE)
            .update({"status": "expired", "last_error": "expired"})
            .eq("status", "pending")
            .lt("created_at", _iso(cutoff))
        )

    def due(self, now, limit):
        return self._run(
            self._client.table(TABLE)
            .select(COLUMNS)
            .eq("awaiting_delivery", True)
            .lte("next_attempt_at", _iso(now))
            .order("next_attempt_at")
            .limit(limit)
        )

    def next_due(self):
        rows = self._run(
            self._client.table(TABLE)
            .select("next_attempt_at")
            .eq("awaiting_delivery", True)
            .order("next_attempt_at")
            .limit(1)
        )
        if not rows:
            return None
        return datetime.fromisoformat(rows[0]["next_attempt_at"].replace("Z", "+00:00"))

    def claim(self, row, now):
        """Conditional on the state that was read: one delivery attempt at a time."""
        rows = self._run(
            self._client.table(TABLE)
            .update(
                {
                    "status": "sending",
                    "claimed_at": _iso(now),
                    "attempts": row["attempts"] + 1,
                }
            )
            .eq("id", row["id"])
            .eq("status", row["status"])
            .eq("attempts", row["attempts"])
        )
        if len(rows) != 1:
            return None
        return {key: rows[0][key] for key in COLUMNS.split(",")}

    def update(self, claim, fields):
        rows = self._run(
            self._client.table(TABLE)
            .update(fields)
            .eq("id", claim["id"])
            .eq("status", "sending")
            .eq("claimed_at", claim["claimed_at"])
        )
        if len(rows) != 1:
            raise PersistenceError("announcement_claim_lost")
