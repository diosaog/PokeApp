"""Private robbery verifier step. No listener, file publication or account access.

Every action re-derives its full server context inside TransferVerification;
the queue is discovery only. Plan, adjudication, re-plan, proof and settlement
are idempotent, so a lost reply is retried by the next scheduled step without
duplicating effects.
"""

from app.application.item_use_verification import VerificationRejected
from app.repositories.errors import PersistenceError
from app.save_parser.models import SaveError
from app.save_parser.writer import NativeWriteError


def run_transfer_step(rpc, verification, *, limit=10):
    jobs = rpc({"operation": "queue"})
    if not isinstance(jobs, list):
        raise PersistenceError("transfer_queue_unavailable")
    results = []
    for job in jobs[:limit]:
        aid, action = job["authorization_id"], job["action"]
        try:
            if action == "plan":
                verification.prepare(aid)
            elif action == "adjudicate":
                verification.adjudicate(aid)
            elif action == "rebase":
                verification.rebase(aid, job["side"])
            elif action == "verify":
                verification.verify(aid, job["side"])
            elif action == "settle":
                verification.settle(aid, job["side"])
            else:
                raise VerificationRejected("TRANSFER_ACTION")
            outcome = "DONE"
        except (VerificationRejected, NativeWriteError, SaveError) as exc:
            # A failed step issues no proof or decision: before the decision
            # nothing is consumed, after it the obligation simply stays pending.
            transient = getattr(exc, "code", None) in (
                "NATIVE_WRITER_FAILURE",
                "PARSER_FAILURE",
            )
            outcome = "RETRY_LATER" if transient else "REJECTED"
        except PersistenceError:
            outcome = "RETRY_LATER"
        results.append({"authorization_id": aid, "action": action, "outcome": outcome})
    return results
