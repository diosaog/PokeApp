"""Run one private verifier job. No listener; disabled without explicit config.

Schedule repeated invocations in the restricted worker service. Never pass its
database credential on a command line or place it in the public API environment.
"""

import os
from pathlib import Path

from app.application.item_use_worker import SignedArtifactReader, verify_one
from app.repositories.item_verifier_pg import ItemVerifierPG
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.writer import PkhexProcessWriter


def main():
    if os.environ.get("POKEAPP_ITEM_VERIFIER_ENABLED") != "true":
        print("DISABLED")
        return 0
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    dsn = os.environ["POKEAPP_ITEM_VERIFIER_DATABASE_URL"]
    # This entry point has no local/insecure override. Disposable tests inject a
    # loopback connection directly into the restricted adapter instead.
    if conninfo_to_dict(dsn).get("sslmode") != "verify-full":
        raise ValueError("Verified TLS required")
    executable = Path(os.environ["POKEAPP_NATIVE_PARSER_PATH"])
    reader = SignedArtifactReader(os.environ["POKEAPP_ITEM_VERIFIER_STORAGE_ORIGIN"])
    try:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as connection:
            print(
                verify_one(
                    ItemVerifierPG(connection),
                    reader,
                    PkhexProcessParser(executable),
                    PkhexProcessWriter(executable),
                )
            )
    finally:
        reader.client.close()
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:  # noqa: BLE001 -- final CLI boundary must redact connection secrets
        # Credentials, signed URLs, SQL/rows and parser bytes never enter logs.
        print("VERIFIER_UNAVAILABLE")
        code = 1
    raise SystemExit(code)
