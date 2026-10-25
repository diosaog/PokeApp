"""Worker-only direct PG RPC transport; absent from the public API container."""

from app.repositories.errors import PersistenceError


class ItemVerifierPG:
    def __init__(self, connection):
        self.connection = connection
        with connection.cursor() as cur:
            cur.execute(
                "select pg_has_role(current_user,'pokeapp_item_verifier','member'),rolsuper,rolbypassrls,rolcreaterole,"
                "has_table_privilege(current_user,'public.item_use_verifications','INSERT') "
                "from pg_roles where rolname=current_user"
            )
            if cur.fetchone() != (True, False, False, False, False):
                raise ValueError("Verifier requires its restricted database identity")

    def __call__(self, request):
        import psycopg
        from psycopg.types.json import Jsonb

        try:
            with self.connection.cursor() as cur:
                cur.execute("select public.item_verifier_job(%s)", (Jsonb(request),))
                return cur.fetchone()[0]
        except psycopg.Error:
            raise PersistenceError("Verifier database unavailable.") from None
