"""Service-role access to trainer_personal_saves (065); the browser has none."""

from app.repositories.errors import PersistenceError

COLUMNS = "trainer_id,sha256,observation_digest,parser_version,game,payload,uploaded_at"


class SupabasePersonalSaveRepository:
    def __init__(self, client):
        self._client = client

    @classmethod
    def from_url_key(cls, url, key):
        from supabase import create_client

        return cls(create_client(url, key))

    def get(self, trainer_id):
        try:
            rows = (
                self._client.table("trainer_personal_saves")
                .select(COLUMNS)
                .eq("trainer_id", trainer_id)
                .execute()
                .data
            )
        except Exception as error:  # noqa: BLE001 - transport boundary, no detail leaks
            raise PersistenceError("personal_save_unavailable") from error
        if len(rows) > 1:
            raise PersistenceError("personal_save_ambiguous")
        return rows[0] if rows else None

    def summaries(self):
        # Progress facts only, selected by JSON path: no Pokémon list travels.
        try:
            rows = (
                self._client.table("trainer_personal_saves")
                .select(
                    "trainer_id,game,uploaded_at,"
                    "observed:payload->observed_progress,native:payload->native_progress"
                )
                .order("trainer_id")
                .limit(500)
                .execute()
                .data
            )
        except Exception as error:  # noqa: BLE001 - transport boundary, no detail leaks
            raise PersistenceError("personal_save_unavailable") from error
        return rows

    def upsert(self, row):
        try:
            self._client.table("trainer_personal_saves").upsert(
                row, on_conflict="trainer_id"
            ).execute()
        except Exception as error:  # noqa: BLE001 - transport boundary, no detail leaks
            raise PersistenceError("personal_save_unavailable") from error
