"""Server-side scope must originate from verified identity, never a public DTO.

This engineering repository is deliberately not wired into the API container.
"""

from app.repositories.errors import PersistenceError


class TransferRepository:
    def __init__(self, client):
        self.client = client

    def _call(self, name, request):
        try:
            return self.client.rpc(name, {"p_request": request}).execute().data
        except Exception:  # noqa: BLE001 - sanitized repository boundary; no fallback/retry
            raise PersistenceError("transfer_unavailable") from None

    def reserve(self, request):
        return self._call("api_prepare_transfer", request)

    def leg(self, request):
        return self._call("api_transfer_leg", request)
