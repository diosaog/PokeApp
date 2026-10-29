"""Single-transaction private inbox. No automatic mutation retries."""

from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected


class SupabaseLauncherRepository:
    def __init__(self, client):
        self.client = client

    @classmethod
    def from_url_key(cls, url, key):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def execute(self, operation, request):
        try:
            data = (
                self.client.rpc(
                    "api_launcher_observation",
                    {
                        "p_request": {"operation": operation, **request},
                    },
                )
                .execute()
                .data
            )
        except Exception as exc:
            status = {
                "PT403": 403,
                "PT404": 404,
                "PT409": 409,
                "PT422": 422,
                "PT429": 429,
            }.get(str(getattr(exc, "code", "")))
            if status:
                raise SeasonAdminRejected("OBSERVATION_REJECTED", status) from exc
            raise PersistenceError("Observation backend unavailable") from exc
        if not isinstance(data, dict):
            raise PersistenceError("Invalid observation receipt")
        return data
