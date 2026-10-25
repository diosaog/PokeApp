"""Private verifier worker. No file publication, economy or account mutations."""

from hashlib import sha256
from time import monotonic
from urllib.parse import quote, urlsplit
from uuid import uuid4

import httpx

from app.application.item_use_verification import (
    TrustedItemUseVerification,
    VerificationRejected,
)
from app.repositories.errors import PersistenceError
from app.save_parser.models import SaveError
from app.save_parser.writer import NATIVE_SIZES, NativeWriteError


class SignedArtifactReader:
    def __init__(self, origin, *, client=None):
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.port
        ):
            raise ValueError("Verifier requires an exact HTTPS Storage origin")
        self.origin = origin.rstrip("/")
        self.client = client or httpx.Client(
            timeout=20, follow_redirects=False, trust_env=False
        )

    def read(self, url, key, digest, size=None):
        parsed = urlsplit(url)
        expected = f"/storage/v1/object/sign/raw-saves/{quote(key, safe='/')}"
        if (
            f"{parsed.scheme}://{parsed.netloc}" != self.origin
            or parsed.path != expected
            or not parsed.query.startswith("token=")
            or parsed.fragment
            or parsed.username
            or ".." in key.split("/")
            or not key.startswith(("trusted/", "item-use/"))
        ):
            raise VerificationRejected("ARTIFACT_URL_DENIED")
        data = bytearray()
        deadline = monotonic() + 45
        try:
            with self.client.stream("GET", url, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise PersistenceError("Artifact read unavailable.")
                for chunk in response.iter_bytes():
                    if monotonic() > deadline:
                        raise PersistenceError("Artifact read unavailable.")
                    data.extend(chunk)
                    if len(data) > max(NATIVE_SIZES.values()):
                        raise VerificationRejected("INVALID_RESULT_SIZE")
        except httpx.HTTPError:
            raise PersistenceError("Artifact read unavailable.") from None
        if (
            len(data) not in NATIVE_SIZES.values()
            or (size is not None and len(data) != size)
            or sha256(data).hexdigest() != digest
        ):
            raise VerificationRejected("ARTIFACT_HASH_MISMATCH")
        return bytes(data)


class WorkerRepository:
    def __init__(self, rpc, reader, job):
        self.rpc, self.reader, self.job = rpc, reader, job

    def call(self, operation, **kwargs):
        return self.rpc(
            {
                "operation": operation,
                "authorization_id": self.job["authorization_id"],
                "lease_id": self.job["lease_id"],
                **kwargs,
            }
        )

    def load(self, aid, sid, tid):
        if aid != self.job["authorization_id"]:
            raise VerificationRejected("AUTHORIZATION_SCOPE")
        context = self.call("context")
        if (
            not context
            or context["authorization"]["season_id"] != sid
            or context["authorization"]["trainer_id"] != tid
        ):
            raise VerificationRejected("AUTHORIZATION_SCOPE")
        return context

    def read_source(self, saved):
        return self.reader.read(
            self.job["source_url"], saved["storage_key"], saved["sha256"]
        )

    def record_verified(self, context, proof, result):
        if (
            proof["result_sha256"] != self.job["result_sha256"]
            or sha256(result).hexdigest() != proof["result_sha256"]
        ):
            raise VerificationRejected("ARTIFACT_HASH_MISMATCH")
        # Result is already durably retained by immutable Storage upload. This RPC
        # alone can insert proof, atomically with context/lease rechecks.
        self.call("finish", context=context, proof=proof)


def verify_one(rpc, reader, parser, native):
    job = rpc({"operation": "lease", "lease_id": str(uuid4())})
    if job is None:
        return "IDLE"
    repository = WorkerRepository(rpc, reader, job)
    try:
        context = repository.call("context")
        if not context:
            raise VerificationRejected("AUTHORIZATION_SCOPE")
        a = context["authorization"]
        result = reader.read(
            job["result_url"],
            job["storage_key"],
            job["result_sha256"],
            job["byte_size"],
        )
        TrustedItemUseVerification(repository, parser, native).verify(
            a["id"], a["season_id"], a["trainer_id"], job["claim_id"], result
        )
        return "VERIFIED"
    except (VerificationRejected, NativeWriteError, SaveError) as exc:
        if getattr(exc, "code", None) in ("NATIVE_WRITER_FAILURE", "PARSER_FAILURE"):
            return "RETRY_LATER"
        try:
            repository.call("reject")
        except PersistenceError:
            return "RETRY_LATER"
        return "REJECTED"
    except PersistenceError:
        # Unknown commit/storage/network outcome: lease expires, then reconcile
        # the durable job. Never turn uncertainty into rejection/consumption.
        return "RETRY_LATER"
