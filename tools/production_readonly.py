"""Read-only transport to PokeApp V2 production, for audits and pre-flights.

Nothing here can change production by construction:

* Supabase: Management API GETs and SQL through ``database/query`` with
  ``read_only: true`` (the platform runs it as a read-only role), and the
  statement must be a single SELECT/WITH. No migration endpoint is reachable.
* Railway: GraphQL ``query`` operations only, and the CLI's ``deployment list``.
* Public HTTP: GET/HEAD/OPTIONS only.

Tokens come from the owner's own CLI sessions (Windows Credential Manager entry
of the Supabase CLI, Railway CLI config) and live in memory only: they are never
printed, logged, written to a file or included in an error message.
"""

from __future__ import annotations

import ctypes
import json
import re
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path

import httpx

SUPABASE_REF = "uwleqeuzsveqlugugzba"
SUPABASE_NAME = "Pokeapp 2.0"
RAILWAY_PROJECT = "f5c4666a-508f-4e5a-8aae-a54581814f29"
RAILWAY_ENVIRONMENT = "d05ccec3-7a85-4eeb-9b01-c0f8d2111896"
RAILWAY_SERVICE = "9a78e086-c927-471f-8bb9-befe62c77de7"
WEB = "https://pokeapp-web.pokeapp-v2.workers.dev"


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _supabase_token() -> str:
    advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_Credential)),
    ]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    pointer = ctypes.POINTER(_Credential)()
    if not advapi.CredReadW("Supabase CLI:supabase", 1, 0, ctypes.byref(pointer)):
        raise RuntimeError("Supabase CLI session unavailable")
    try:
        raw = ctypes.string_at(
            pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize
        )
        for encoding in ("utf-16-le", "utf-8"):
            try:
                value = raw.decode(encoding).rstrip("\0")
            except UnicodeError:
                continue
            if value.startswith("sbp_"):
                return value
        raise RuntimeError("Unsupported Supabase CLI credential encoding")
    finally:
        advapi.CredFree(pointer)


def _supabase(method: str, path: str, body: dict | None = None):
    assert path == f"/v1/projects/{SUPABASE_REF}" or path.startswith(
        f"/v1/projects/{SUPABASE_REF}/"
    ), "only the pinned V2 project"
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        response = client.request(
            method,
            "https://api.supabase.com" + path,
            headers={"Authorization": "Bearer " + _supabase_token()},
            json=body,
        )
    if response.status_code not in (200, 201):
        # A SQL error message names the failing object; no credential is in it.
        detail = (
            response.json().get("message", "")[:300]
            if response.status_code == 400
            else ""
        )
        raise RuntimeError(
            f"Supabase Management HTTP {response.status_code} on {path} {detail}"
        )
    return response.json() if response.content else None


def supabase_get(path: str):
    return _supabase("GET", f"/v1/projects/{SUPABASE_REF}{path}")


_READ = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def query(sql: str) -> list[dict]:
    """One SELECT/WITH statement, executed by the platform in read-only mode."""
    body = sql.strip().rstrip(";")
    assert _READ.match(body) and ";" not in body, "single read statement only"
    return _supabase(
        "POST",
        f"/v1/projects/{SUPABASE_REF}/database/query",
        {"query": body, "read_only": True},
    )


def railway(graphql: str, variables: dict | None = None) -> dict:
    """A Railway GraphQL read (``query`` operation only)."""
    assert re.match(r"^\s*(query\b|\{)", graphql), "GraphQL queries only"
    config = json.loads((Path.home() / ".railway/config.json").read_text())
    token = config["user"].get("accessToken") or config["user"].get("token")
    response = httpx.post(
        "https://backboard.railway.com/graphql/v2",
        headers={"Authorization": "Bearer " + token},
        json={"query": graphql, "variables": variables or {}},
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Railway GraphQL HTTP {response.status_code}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError("Railway GraphQL rejected the query; no values emitted")
    return data["data"]


def railway_variables() -> dict[str, str]:
    """Service variables, for the caller to reduce to names and flags. Never print it."""
    # The CLI owns the current GraphQL contract. Its JSON includes secrets, so
    # capture it in memory and never include stdout/stderr in an exception.
    result = subprocess.run(
        [shutil.which("railway"), "variables", "--json", "--project", RAILWAY_PROJECT,
         "--environment", RAILWAY_ENVIRONMENT, "--service", RAILWAY_SERVICE],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode:
        raise RuntimeError("Railway CLI variables unavailable; no values emitted")
    return json.loads(result.stdout)


def railway_deployments(limit: int = 5) -> list[dict]:
    result = subprocess.run(
        [
            shutil.which("railway"),
            "deployment",
            "list",
            "--limit",
            str(limit),
            "--json",
            "--project",
            RAILWAY_PROJECT,
            "--environment",
            RAILWAY_ENVIRONMENT,
            "--service",
            RAILWAY_SERVICE,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Railway CLI deployment list failed: {result.returncode}")
    return json.loads(result.stdout)


def http(method: str, url: str, **kwargs) -> httpx.Response:
    assert method in ("GET", "HEAD", "OPTIONS")
    headers = {"User-Agent": "PokeApp-release-audit/1.0", **kwargs.pop("headers", {})}
    return httpx.request(method, url, headers=headers, timeout=60, **kwargs)
