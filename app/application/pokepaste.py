"""Pokepast.es transport: one public paste per request, created server-side.

Pokepast.es (github.com/felixphew/pokepaste, v3) creates a paste from a form
POST to /create with the fields paste, title, author and notes, and answers
303 See Other with Location "/<16 hex>". There is no API key or idempotency
key, so outcomes are classified like the Discord transport:

- created: the Location names the new paste.
- retry: nothing usable came back (no connection, 429, 5xx, a lost answer);
  a bounded retry may create one more paste, never an unbounded number.
- rejected: the request was refused (4xx) or answered unexpectedly; sending
  it again cannot help.

Only text built from a Team Lock's public projection is ever sent. Its
content is never logged.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

CREATE_URL = "https://pokepast.es/create"
LOCATION = re.compile(r"^(?:https://pokepast\.es)?/([0-9a-f]{16})$")
TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
MAX_PASTE = 6000
MAX_FIELD = 200


@dataclass(frozen=True)
class PasteOutcome:
    url: str | None
    code: str
    retry: bool = False


class Pokepaste:
    def __init__(self, *, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)

    def create(self, *, paste: str, title: str, author: str, notes: str) -> PasteOutcome:
        if not paste.strip() or len(paste) > MAX_PASTE:
            return PasteOutcome(None, "pokepaste_invalid_paste")
        form = {
            "paste": paste,
            "title": title[:MAX_FIELD],
            "author": author[:MAX_FIELD],
            "notes": notes[:MAX_FIELD],
        }
        try:
            response = self._client.post(
                CREATE_URL, data=form, headers={"User-Agent": "PokeApp"}
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return PasteOutcome(None, "pokepaste_unreachable", retry=True)
        except httpx.HTTPError:
            # The paste may exist; a bounded retry can only add one more.
            return PasteOutcome(None, "pokepaste_response_lost", retry=True)
        status = response.status_code
        if status in (301, 302, 303, 307, 308):
            match = LOCATION.fullmatch(response.headers.get("location", "").strip())
            if match:
                return PasteOutcome(f"https://pokepast.es/{match.group(1)}", "created")
            return PasteOutcome(None, "pokepaste_unexpected_location")
        if status == 429 or status >= 500:
            return PasteOutcome(None, f"pokepaste_http_{status}", retry=True)
        return PasteOutcome(None, f"pokepaste_http_{status}")
