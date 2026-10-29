"""Pooled HTTP/1.1 transports for every server-side PostgREST and Auth call.

supabase-py gives each client a single shared HTTP/2 connection. FastAPI runs
the sync routes on a thread pool, so every request of a screen is multiplexed
over that one connection; when Supabase's edge drops it, all of them and their
retry fail together. Observed in production on 2026-10-29: a confirmed
«Revividos tras wipe» change followed by ~30 s of 503 on the League and wipe
reads (PostgREST, httpx.ReadError); after that fix, bursts of AUTH_UNAVAILABLE
across unrelated endpoints in the same millisecond (the session check every
request makes against Supabase Auth). Over HTTP/1.1 each request owns a pooled
connection: a stale one is detected and replaced, and a dropped one fails only
its own request.
"""

import threading

import httpx

_lock = threading.Lock()
_session = None
_auth_session = None


def _pool(timeout):
    return httpx.Client(
        http2=False,
        timeout=httpx.Timeout(timeout),
        limits=httpx.Limits(
            max_connections=64,
            max_keepalive_connections=16,
            keepalive_expiry=20,
        ),
        follow_redirects=True,
    )


def postgrest_session():
    """Process-wide pool. Requests carry absolute URLs and their own headers
    (PostgREST builders do), so clients for any key can share it."""
    global _session
    with _lock:
        if _session is None:
            from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT

            _session = _pool(DEFAULT_POSTGREST_CLIENT_TIMEOUT)
        return _session


def auth_session():
    """Same for Supabase Auth (GoTrue builds absolute URLs and passes its
    headers per request), with GoTrue's own 5 s default timeout."""
    global _auth_session
    with _lock:
        if _auth_session is None:
            _auth_session = _pool(5.0)
        return _auth_session


def create_client(url, key):
    """supabase.create_client with PostgREST and Auth (and its admin API) on
    the shared HTTP/1.1 pools. Storage keeps its own client."""
    from postgrest import SyncPostgrestClient

    from supabase import create_client as create

    client = create(url, key)
    client._postgrest = SyncPostgrestClient(
        str(client.rest_url),
        schema=client.options.schema,
        headers=client.options.headers,
        http_client=postgrest_session(),
    )
    client.auth._http_client = auth_session()
    client.auth.admin._http_client = auth_session()
    return client
