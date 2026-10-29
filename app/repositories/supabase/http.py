"""One pooled HTTP/1.1 transport for every server-side PostgREST call.

supabase-py gives each client a single shared HTTP/2 connection. FastAPI runs
the sync routes on a thread pool, so every read of a screen is multiplexed over
that one connection; when Supabase's edge drops it, all of them and their retry
fail together with httpx.ReadError. Observed in production on 2026-10-29: a
confirmed «Revividos tras wipe» change followed by ~30 s of 503 on the League
and wipe reads, so the web kept the old figures until the Launcher restarted.
Over HTTP/1.1 each request owns a pooled connection: a stale one is detected
and replaced, and a dropped one fails only its own request.
"""

import threading

import httpx

_lock = threading.Lock()
_session = None


def postgrest_session():
    """Process-wide pool. Requests carry absolute URLs and their own headers
    (PostgREST builders do), so clients for any key can share it."""
    global _session
    with _lock:
        if _session is None:
            from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT

            _session = httpx.Client(
                http2=False,
                timeout=httpx.Timeout(DEFAULT_POSTGREST_CLIENT_TIMEOUT),
                limits=httpx.Limits(
                    max_connections=64,
                    max_keepalive_connections=16,
                    keepalive_expiry=20,
                ),
                follow_redirects=True,
            )
        return _session


def create_client(url, key):
    """supabase.create_client with PostgREST on the shared HTTP/1.1 pool.
    Auth and Storage keep their own clients."""
    from postgrest import SyncPostgrestClient

    from supabase import create_client as create

    client = create(url, key)
    client._postgrest = SyncPostgrestClient(
        str(client.rest_url),
        schema=client.options.schema,
        headers=client.options.headers,
        http_client=postgrest_session(),
    )
    return client
