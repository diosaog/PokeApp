"""Background delivery of Discord announcements inside the API process.

One daemon thread. It drains the outbox at startup (an app woken from sleep
catches up), right after a request that may have confirmed a fact, and when a
retry falls due. With nothing pending it waits without touching the network,
so Railway's app sleeping still applies. Reads wake it at most once a minute:
the hosted verifier confirms robberies outside the API.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

READ_PROBE_SECONDS = 60.0


class Announcer:
    def __init__(self, dispatcher, *, clock=time.monotonic):
        self._dispatcher = dispatcher
        self._clock = clock
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_run = float("-inf")

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._loop, name="discord-announcer", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def kick(self, *, mutation: bool) -> None:
        if mutation or self._clock() - self._last_run >= READ_PROBE_SECONDS:
            self._wake.set()

    def _loop(self) -> None:
        delay: float | None = 0.0
        while not self._stop.is_set():
            self._wake.wait(delay)
            if self._stop.is_set():
                return
            self._wake.clear()
            self._last_run = self._clock()
            try:
                delay = self._dispatcher.run_once()
            except Exception as error:  # noqa: BLE001 - the API must never fall over for Discord
                logger.warning(
                    "discord_announcer_failed cause=%s", type(error).__name__
                )
                delay = 60.0


def create_announcer(config):
    """None unless a valid webhook and the service-role backend are configured."""
    if not config.discord_webhook_url:
        return None
    from app.application.discord_webhook import DiscordWebhook, valid_webhook_url

    if not valid_webhook_url(config.discord_webhook_url):
        logger.warning("discord_announcements_disabled cause=invalid_webhook_url")
        return None
    if not (config.supabase_url and config.supabase_service_role_key):
        return None
    from app.application.announcements import Dispatcher
    from app.repositories.supabase.announcements import SupabaseAnnouncementRepository

    repository = SupabaseAnnouncementRepository.from_url_key(
        config.supabase_url, config.supabase_service_role_key
    )
    return Announcer(
        Dispatcher(
            outbox=repository,
            read=repository.rows,
            webhook=DiscordWebhook(config.discord_webhook_url),
        )
    )
