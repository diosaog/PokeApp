"""Administración › Avisos: service-only RPCs and read-only raw save access (084)."""

from hashlib import sha256

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected

ERRORS = {
    "admin_required": ("ADMIN_REQUIRED", 403),
    "season_not_found": ("SEASON_NOT_FOUND", 404),
    "notice_not_found": ("NOTICE_NOT_FOUND", 404),
    "idempotency_conflict": ("IDEMPOTENCY_CONFLICT", 409),
    "notice_note_required": ("NOTICE_NOTE_REQUIRED", 422),
    "invalid_notice_request": ("INVALID_NOTICE_REQUEST", 422),
}


class SupabaseSaveAuditRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def _rpc(self, name, params):
        try:
            return self.client.rpc(name, params).execute().data
        except Exception as exc:  # noqa: BLE001 - every client failure maps to a stable code or a 503
            text = f"{getattr(exc, 'message', '')} {exc}"
            for marker, (code, status) in ERRORS.items():
                if marker in text:
                    raise SeasonAdminRejected(code, status) from None
            raise PersistenceError("Save audit backend unavailable") from None

    # Analysis -----------------------------------------------------------------
    def pending(self, season, trainer, limit):
        return self._rpc(
            "save_audit_pending",
            {"p_season": season, "p_trainer": trainer, "p_limit": limit},
        )

    def context(self, season, trainer, save_file):
        return self._rpc(
            "save_audit_context",
            {"p_season": season, "p_trainer": trainer, "p_save": save_file},
        )

    def record(self, request):
        return self._rpc("save_audit_record", {"p_request": request})

    def read_raw(self, saved):
        """The immutable accepted bytes, by server-owned key; read-only."""
        key = saved["storage_key"]
        expected = f"trusted/{saved['trainer_id']}/{saved['season_id']}/{saved['sha256']}.sav"
        if saved["storage_bucket"] != "raw-saves" or key != expected:
            raise PersistenceError("Save audit source is not trusted")
        try:
            data = self.client.storage.from_("raw-saves").download(key)
        except Exception:  # noqa: BLE001
            raise PersistenceError("Save audit source unavailable") from None
        if type(data) is not bytes or sha256(data).hexdigest() != saved["sha256"]:
            raise PersistenceError("Save audit source changed")
        return data

    # Administration ------------------------------------------------------------
    def read(self, actor, season):
        return self._rpc("admin_save_audit_read", {"p_actor": actor, "p_season": season})

    def summary(self, actor, season):
        return self._rpc("admin_save_audit_summary", {"p_actor": actor, "p_season": season})

    def update(self, actor, season, notice, status, note, operation, digest):
        return self._rpc(
            "admin_save_audit_update",
            {
                "p_actor": actor,
                "p_season": season,
                "p_notice": notice,
                "p_status": status,
                "p_note": note,
                "p_operation": operation,
                "p_hash": digest,
            },
        )
