"""The HAI Shutter Manager integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONFIG_VERSION,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_COVER_OPTION,
)
from .coordinator import ShutterCoordinator

_LOGGER = logging.getLogger(__name__)

_SET_OPTION_SCHEMA = vol.Schema(
    {
        vol.Required("cover_id"): cv.string,
        vol.Required("key"): cv.string,
        vol.Required("value"): vol.Any(cv.string, vol.Coerce(float), cv.boolean),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAI Shutter Manager from a config entry."""
    coordinator = ShutterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates without a full reload."""
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.reload_config()
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ShutterCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_COVER_OPTION)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to the current version."""
    if entry.version > CONFIG_VERSION:
        return False
    # No migrations yet; bump version handling lives here for future releases.
    return True


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_COVER_OPTION):
        return

    async def _handle_set_cover_option(call: ServiceCall) -> None:
        cover_id = call.data["cover_id"]
        key = call.data["key"]
        value = call.data["value"]
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, ShutterCoordinator) and coordinator.has_cover(
                cover_id
            ):
                await coordinator.async_set_cover_option(cover_id, key, value)
                return
        _LOGGER.warning("set_cover_option: unknown cover %s", cover_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COVER_OPTION,
        _handle_set_cover_option,
        schema=_SET_OPTION_SCHEMA,
    )
