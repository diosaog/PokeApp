"""Run one private verifier job. No listener; disabled without explicit config.

Schedule repeated invocations in the restricted worker service. Never pass its
database credential on a command line or place it in the public API environment.
Robbery steps (27A) run only with their own explicit switch and storage key.
"""

import os
from pathlib import Path

from app.application.item_use_worker import SignedArtifactReader, verify_one
from app.application.transfer_verification import TransferVerification
from app.application.transfer_worker import run_transfer_step
from app.repositories.item_verifier_pg import ItemVerifierPG
from app.repositories.transfer_verifier_pg import TransferVerifierPG
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.writer import PkhexProcessWriter

MAX_ITEM_JOBS = 5
MAX_TRANSFER_PASSES = 4


def transfer_once(connection, storage, reader, parser, native):
    """Robbery steps until the queue stops advancing (each one is idempotent).

    A request needs plan, then adjudicate; a side needs verify, then settle.
    Bounded passes in one turn, instead of a whole 60 s turn per step.
    """
    rpc = TransferVerifierPG(connection)
    verification = TransferVerification(
        rpc,
        storage.read_source,
        reader,
        parser,
        native,
        store_raw=storage.store_raw,
    )
    outcomes = []
    for _ in range(MAX_TRANSFER_PASSES):
        step = run_transfer_step(rpc, verification)
        outcomes += step
        if not any(o["outcome"] == "DONE" for o in step):
            break
    return outcomes


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
    parser, native = PkhexProcessParser(executable), PkhexProcessWriter(executable)
    try:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as connection:
            for _ in range(MAX_ITEM_JOBS):
                outcome = verify_one(ItemVerifierPG(connection), reader, parser, native)
                print(outcome)
                if outcome == "IDLE":
                    break
            if os.environ.get("POKEAPP_TRANSFER_VERIFIER_ENABLED") == "true":
                from app.repositories.supabase.transfer_storage import (
                    PrivateTransferStorage,
                )
                from supabase import create_client

                storage = PrivateTransferStorage(
                    create_client(
                        os.environ["POKEAPP_TRANSFER_STORAGE_URL"],
                        os.environ["POKEAPP_TRANSFER_STORAGE_KEY"],
                    )
                )
                # Outcomes only: no ids, bytes, URLs or rows in logs.
                outcomes = transfer_once(connection, storage, reader, parser, native)
                print("TRANSFER", [o["outcome"] for o in outcomes])
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
