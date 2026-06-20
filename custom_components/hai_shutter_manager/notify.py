"""Telegram notifications with priority filtering and anti-spam."""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    NOTIFY_DEDUP_SECONDS,
    NOTIFY_RATE_LIMIT,
    NOTIFY_RATE_WINDOW,
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
)

_LOGGER = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _mask(token: str | None) -> str:
    """Mask a secret token for safe logging."""
    if not token:
        return "<none>"
    if len(token) <= 6:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


class TelegramNotifier:
    """Sends Telegram messages while respecting user preferences and rate limits."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._chat_id: str | None = None
        self._bot_token: str | None = None
        self._notify_service: str | None = None
        self._levels: set[str] = {PRIORITY_NORMAL, PRIORITY_EMERGENCY}
        self._test_mode: bool = False
        # message-hash -> last sent time, for de-duplication
        self._recent: dict[str, datetime] = {}
        # timestamps of sent messages, for rate-limiting
        self._sent_times: deque[datetime] = deque()

    def configure(
        self,
        *,
        chat_id: str | None,
        bot_token: str | None,
        notify_service: str | None,
        levels: list[str] | None,
        test_mode: bool = False,
    ) -> None:
        """Update notifier settings from config."""
        self._chat_id = chat_id or None
        self._bot_token = bot_token or None
        self._notify_service = notify_service or None
        self._test_mode = test_mode
        if levels:
            self._levels = set(levels)

    async def async_send_test_log(self, message: str) -> bool:
        """Send a detailed test-mode log; relaxed dedup/rate limits."""
        if not self._allowed(PRIORITY_NORMAL):
            return False
        text = message
        return await self._dispatch(text)

    def _allowed(self, priority: str) -> bool:
        return priority in self._levels

    def _is_duplicate(self, key: str, now: datetime) -> bool:
        last = self._recent.get(key)
        if last is None:
            return False
        return (now - last).total_seconds() < NOTIFY_DEDUP_SECONDS

    def _rate_limited(self, now: datetime) -> bool:
        while self._sent_times and now - self._sent_times[0] > NOTIFY_RATE_WINDOW:
            self._sent_times.popleft()
        return len(self._sent_times) >= NOTIFY_RATE_LIMIT

    async def async_send(self, message: str, priority: str = PRIORITY_NORMAL) -> bool:
        """Send a message if allowed by level, dedup and rate-limit policies."""
        if not self._allowed(priority):
            return False

        now = dt_util.utcnow()
        key = f"{priority}:{message}"

        if self._is_duplicate(key, now):
            _LOGGER.debug("Suppressing duplicate notification: %s", message)
            return False

        # Emergency messages bypass the rate limiter so critical alerts get through.
        if priority != PRIORITY_EMERGENCY and self._rate_limited(now):
            _LOGGER.warning("Notification rate limit reached; dropping: %s", message)
            return False

        prefix = "[EMERGENCY] " if priority == PRIORITY_EMERGENCY else ""
        text = f"{prefix}{message}"

        sent = await self._dispatch(text)
        if sent:
            self._recent[key] = now
            self._sent_times.append(now)
        return sent

    async def _dispatch(self, text: str) -> bool:
        """Send via the configured transport (notify service or direct API)."""
        if self._notify_service:
            try:
                domain, service = self._notify_service.split(".", 1)
                await self._hass.services.async_call(
                    domain, service, {"message": text}, blocking=True
                )
                return True
            except Exception as err:  # noqa: BLE001 - log and fall through
                _LOGGER.error("Failed to send via notify service: %s", err)

        if self._bot_token and self._chat_id:
            session = async_get_clientsession(self._hass)
            url = _TELEGRAM_API.format(token=self._bot_token)
            try:
                async with session.post(
                    url, json={"chat_id": self._chat_id, "text": text}
                ) as resp:
                    if resp.status == 200:
                        return True
                    body = await resp.text()
                    _LOGGER.error(
                        "Telegram API error %s (token=%s): %s",
                        resp.status,
                        _mask(self._bot_token),
                        body,
                    )
            except Exception as err:  # noqa: BLE001 - network errors
                _LOGGER.error("Telegram request failed: %s", err)
            return False

        _LOGGER.debug("No notification transport configured; message dropped")
        return False
