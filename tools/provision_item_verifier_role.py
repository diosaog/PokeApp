"""Create (or rotate) the hosted verifier's database login, then hand its DSN
to the Railway worker — the password never appears on screen or in a log.

The login role is a member of pokeapp_item_verifier (056) and nothing else:
no superuser, no RLS bypass, no role creation, no table writes; it can only
call the verifier functions granted to that role. Postgres receives only a
SCRAM-SHA-256 verifier, never the plaintext. The plaintext goes once, over
stdin, into the worker's POKEAPP_ITEM_VERIFIER_DATABASE_URL.

Run (owner-authorized): python -m tools.provision_item_verifier_role --railway-dir <dir linked to the worker service>
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import secrets
import shutil
import subprocess
from urllib.parse import quote

from tools.production_readonly import SUPABASE_REF, _supabase, query

ROLE = "pokeapp_verifier_login"
POOLER = "aws-0-eu-central-1.pooler.supabase.com"
CA = "/srv/pokeapp/deploy/certs/supabase-prod-ca-2021.crt"


def scram_verifier(password: str, iterations: int = 4096) -> str:
    salt = secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored = hashlib.sha256(client).digest()
    server = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    b64 = lambda raw: base64.b64encode(raw).decode()
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored)}:{b64(server)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--railway-dir", required=True)
    args = parser.parse_args()
    password = secrets.token_urlsafe(32)
    verifier = scram_verifier(password)
    sql = (
        "do $$ begin "
        f"if not exists (select 1 from pg_roles where rolname='{ROLE}') then "
        f"create role {ROLE} login nosuperuser nocreatedb nocreaterole inherit nobypassrls noreplication connection limit 4; "
        "end if; "
        f"execute format('alter role {ROLE} with login password %L', '{verifier}'); "
        "end $$; "
        f"grant pokeapp_item_verifier to {ROLE}"
    )
    _supabase("POST", f"/v1/projects/{SUPABASE_REF}/database/query", {"query": sql})
    row = query(
        f"select rolcanlogin::text||rolsuper::text||rolbypassrls::text||rolcreaterole::text as flags, "
        f"pg_has_role('{ROLE}','pokeapp_item_verifier','member')::text as member "
        f"from pg_roles where rolname='{ROLE}'"
    )[0]
    assert row == {"flags": "truefalsefalsefalse", "member": "true"}, row
    dsn = (
        f"postgresql://{ROLE}.{SUPABASE_REF}:{quote(password, safe='')}@{POOLER}:5432/postgres"
        f"?sslmode=verify-full&sslrootcert={CA}"
    )
    subprocess.run(
        [shutil.which("railway"), "variable", "set", "POKEAPP_ITEM_VERIFIER_DATABASE_URL", "--stdin", "--skip-deploys"],
        input=dsn,
        text=True,
        cwd=args.railway_dir,
        check=True,
        capture_output=True,
    )
    print("verifier login ready; DSN stored in the worker service (not shown)")


if __name__ == "__main__":
    main()
