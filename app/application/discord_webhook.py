"""Discord webhook transport for «Aaron Avisa!»: at most one message per request.

Discord webhooks take no idempotency key, so every failure is classified by
whether Discord can have created the message:

- ``retry``: it cannot (no connection, 429). Sending again is safe.
- ``uncertain``: it may have (the request was sent and the answer was lost,
  or Discord failed while handling it). A new message is never sent again.
- ``rejected``: Discord refused the payload; sending it again cannot help.

The URL holds the webhook token: it is never logged, echoed or stored.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import logging
import threading
import time

import httpx

URL = re.compile(
    r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api(?:/v\d{1,2})?/webhooks/"
    r"\d{1,25}/[A-Za-z0-9_-]{20,200}"
)
# The webhook itself is gone or its token is wrong: nothing was created.
WEBHOOK_REJECTED = {401, 403, 404}
UNKNOWN_MESSAGE = 10008
TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
# Discord allows about 30 messages a minute per channel; stay below it.
SPACING_SECONDS = 2.1
# Longer waits go back to the dispatcher instead of blocking its thread.
MAX_WAIT_SECONDS = 30.0


class _RedactWebhook(logging.Filter):
    def filter(self, record):
        # httpx logs full request URLs at INFO, including webhook credentials.
        record.msg = URL.sub(
            "https://discord.com/api/webhooks/<redacted>", record.getMessage()
        )
        record.args = ()
        return True


logging.getLogger("httpx").addFilter(_RedactWebhook())


def valid_webhook_url(url: str) -> bool:
    return bool(URL.fullmatch(url or ""))


@dataclass(frozen=True)
class Outcome:
    result: str  # delivered | retry | uncertain | rejected
    code: str
    message_id: str | None = None
    retry_after: float = 0.0


class DiscordWebhook:
    def __init__(
        self,
        url: str,
        *,
        client: httpx.Client | None = None,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        if not valid_webhook_url(url):
            raise ValueError("Invalid Discord webhook URL")
        self._url = url
        self._client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)
        self._clock, self._sleep = clock, sleep
        self._next_request_at = 0.0
        self._lock = threading.Lock()

    def __repr__(self) -> str:  # never the token
        return "DiscordWebhook(<configured>)"

    def post(self, payload: dict) -> Outcome:
        return self._send("POST", self._url, {"wait": "true"}, payload)

    def edit(self, message_id: str, payload: dict) -> Outcome:
        if not re.fullmatch(r"\d{1,25}", message_id or ""):
            return Outcome("rejected", "invalid_message_id")
        return self._send("PATCH", f"{self._url}/messages/{message_id}", None, payload)

    def ready_in(self) -> float:
        """Seconds before Discord's limits allow the next request."""
        return max(0.0, self._next_request_at - self._clock())

    def _hold(self, seconds: float) -> None:
        self._next_request_at = max(self._next_request_at, self._clock() + seconds)

    def _send(self, method, url, params, payload) -> Outcome:
        # No @everyone, @here, role or user ping can come out of any announcement.
        body = {**payload, "allowed_mentions": {"parse": []}}
        with self._lock:
            wait = self._next_request_at - self._clock()
            if wait > MAX_WAIT_SECONDS:
                return Outcome("retry", "rate_limited", retry_after=wait)
            if wait > 0:
                self._sleep(wait)
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    json=body,
                    headers={"User-Agent": "PokeApp"},
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
                outcome = Outcome("retry", "connect_failed")
            except (httpx.WriteError, httpx.WriteTimeout):
                # A failed write does not prove that the peer received no body.
                outcome = Outcome("uncertain", "send_unknown")
            except httpx.TimeoutException:
                outcome = Outcome("uncertain", "response_timeout")
            except httpx.HTTPError:
                outcome = Outcome("uncertain", "response_lost")
            else:
                outcome = _classify(response)
                if outcome.code == "rate_limited":
                    self._hold(outcome.retry_after)
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    self._hold(
                        _seconds(response.headers.get("X-RateLimit-Reset-After"))
                    )
            self._hold(SPACING_SECONDS)
        return outcome


def _seconds(value) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(seconds, 0.0), 3600.0) if seconds == seconds else 0.0


def _json(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _classify(response: httpx.Response) -> Outcome:
    status = response.status_code
    if 200 <= status < 300:
        message_id = str(_json(response).get("id", ""))
        if not re.fullmatch(r"\d{1,25}", message_id):
            return Outcome("uncertain", "message_receipt_missing")
        return Outcome("delivered", "delivered", message_id=message_id)
    if status == 429:
        after = max(
            _seconds(_json(response).get("retry_after")),
            _seconds(response.headers.get("Retry-After")),
            1.0,
        )
        return Outcome("retry", "rate_limited", retry_after=after)
    if status == 404 and _json(response).get("code") == UNKNOWN_MESSAGE:
        return Outcome("rejected", "message_missing")
    if status in WEBHOOK_REJECTED:
        return Outcome("retry", "webhook_rejected", retry_after=600.0)
    if status >= 500:
        return Outcome("uncertain", f"http_{status}")
    return Outcome("rejected", f"http_{status}")
