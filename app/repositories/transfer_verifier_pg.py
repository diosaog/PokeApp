"""Reuse23D restricted connection checks; never an API or Launcher dependency."""

from app.repositories.errors import PersistenceError
from app.repositories.item_verifier_pg import ItemVerifierPG


class TransferVerifierPG(ItemVerifierPG):
    def __init__(self, connection):
        super().__init__(connection)
        with connection.cursor() as cur:
            cur.execute(
                "select has_table_privilege(current_user,'public.item_use_transfer_legs','INSERT,UPDATE,DELETE')"
            )
            if cur.fetchone() != (False,):
                raise ValueError("Transfer verifier must not have table DML")

    def __call__(self, request):
        import psycopg
        from psycopg.types.json import Jsonb

        try:
            with self.connection.cursor() as cur:
                cur.execute("select public.transfer_verifier(%s)", (Jsonb(request),))
                return cur.fetchone()[0]
        except psycopg.Error:
            raise PersistenceError("transfer_verifier_unavailable") from None
