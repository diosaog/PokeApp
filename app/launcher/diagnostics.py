"""Local diagnostic log for the Launcher core, kept in the profile's logs folder.

Event codes, timings and exception class names only: never tokens, PINs, save
bytes or Pokémon. The Windows user folder and user name are masked, so the
trainer can share the file (or the Launcher's «Copiar diagnóstico») safely.
"""

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_BYTES = 256 * 1024
# Silent until the real core gives it a file: tests and tools print nothing.
logging.getLogger("pokeapp.core").addHandler(logging.NullHandler())


def mask(text):
    """The user's folder and name become placeholders; nothing else changes."""
    text = str(text)
    home = os.environ.get("USERPROFILE") or str(Path.home())
    if home and len(home) > 3:
        text = re.sub(re.escape(home), "%USERPROFILE%", text, flags=re.IGNORECASE)
    user = os.environ.get("USERNAME")
    if user and len(user) > 2:
        text = re.sub(
            r"(?<![\w])" + re.escape(user) + r"(?![\w])",
            "<usuario>",
            text,
            flags=re.IGNORECASE,
        )
    return text


class _Masked(logging.Formatter):
    def format(self, record):
        return mask(super().format(record))


def core_log(profile):
    """The core's logger, writing to this profile. A profile that cannot hold
    a log never stops the core."""
    log = logging.getLogger("pokeapp.core")
    log.setLevel(logging.INFO)
    log.propagate = False
    close_core_log()
    try:
        folder = Path(profile) / "logs"
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            folder / "core.log", maxBytes=LOG_BYTES, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(_Masked("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(handler)
    except (OSError, ValueError):
        pass
    return log


def close_core_log():
    log = logging.getLogger("pokeapp.core")
    for handler in [h for h in log.handlers if isinstance(h, RotatingFileHandler)]:
        log.removeHandler(handler)
        handler.close()


def failure(exc):
    """`ConnectError` / `TLS_UNTRUSTED`…: what kind of failure, never its text."""
    text = str(exc)
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
        return "TLS_UNTRUSTED"
    return type(exc).__name__
