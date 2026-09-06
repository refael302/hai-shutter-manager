"""Serve the Lovelace card from the integration and keep the resource current."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import (
    FRONTEND_CARD_FILENAME,
    FRONTEND_URL_BASE,
    INTEGRATION_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _card_url() -> str:
    return f"{FRONTEND_URL_BASE}/{FRONTEND_CARD_FILENAME}"


def _versioned_url() -> str:
    return f"{_card_url()}?v={INTEGRATION_VERSION}"


def _path_only(url: str) -> str:
    return url.split("?", 1)[0]


def _version_of(url: str) -> str:
    if "?v=" not in url:
        return ""
    return url.split("?v=", 1)[1]


class JSModuleRegistration:
    """Register the dashboard card over HTTP and as a Lovelace resource."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = hass.data.get("lovelace")

    async def async_register(self) -> None:
        await self._async_register_path()
        if self.lovelace is None:
            self.lovelace = self.hass.data.get("lovelace")
        mode = getattr(
            self.lovelace, "mode", getattr(self.lovelace, "resource_mode", None)
        )
        if mode == "storage":
            await self._async_wait_for_lovelace_resources()
        else:
            _LOGGER.debug(
                "Lovelace is not in storage mode; card is served at %s",
                _versioned_url(),
            )

    async def _async_register_path(self) -> None:
        frontend_dir = Path(__file__).parent
        try:
            from homeassistant.components.http import StaticPathConfig

            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_BASE, str(frontend_dir), False)]
            )
        except RuntimeError:
            _LOGGER.debug("Frontend path already registered: %s", FRONTEND_URL_BASE)
        except AttributeError:
            self.hass.http.register_static_path(
                FRONTEND_URL_BASE, str(frontend_dir), False
            )

    async def _async_wait_for_lovelace_resources(self) -> None:
        async def _check_loaded(_now: Any) -> None:
            resources = getattr(self.lovelace, "resources", None)
            if resources is not None and getattr(resources, "loaded", False):
                await self._async_register_module()
                return
            _LOGGER.debug("Lovelace resources not loaded yet; retrying")
            async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(None)

    async def _async_register_module(self) -> None:
        resources = self.lovelace.resources
        url = _card_url()
        versioned = _versioned_url()
        ours: list[dict[str, Any]] = []
        legacy: list[dict[str, Any]] = []
        for item in resources.async_items():
            path = _path_only(item.get("url", ""))
            if path == url:
                ours.append(item)
            elif path.endswith(f"/{FRONTEND_CARD_FILENAME}"):
                legacy.append(item)

        # Old /local or /hacsfiles copies would load first and hide updates.
        for item in legacy:
            _LOGGER.info("Replacing legacy Lovelace card resource %s", item.get("url"))
            await resources.async_delete_item(item["id"])

        if not ours:
            _LOGGER.info("Registering Lovelace card %s", versioned)
            await resources.async_create_item(
                {"res_type": "module", "url": versioned}
            )
            return
        for item in ours:
            if _version_of(item.get("url", "")) == INTEGRATION_VERSION:
                continue
            _LOGGER.info("Updating Lovelace card resource to %s", versioned)
            await resources.async_update_item(
                item["id"],
                {"res_type": "module", "url": versioned},
            )
