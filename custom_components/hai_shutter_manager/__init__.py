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
    SERVICE_SET_TEST_OVERRIDE,
    SERVICE_SET_VIRTUAL_STATE,
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

_SET_TEST_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional("cover_id"): cv.string,
        vol.Required("key"): cv.string,
        vol.Required("value"): vol.Any(cv.string, vol.Coerce(float), cv.boolean),
    }
)

_SET_VIRTUAL_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("cover_id"): cv.string,
        vol.Required("state"): vol.In(["open", "closed"]),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAI Shutter Manager from a config entry."""
    coordinator = ShutterCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        _LOGGER.exception(
            "HAI Shutter Manager: initial refresh failed; using fallback data"
        )
        coordinator.async_set_updated_data(coordinator.build_fallback_data())

    loaded: list[str] = []
    for platform in PLATFORMS:
        try:
            await hass.config_entries.async_forward_entry_setups(entry, [platform])
            loaded.append(platform)
        except Exception:
            _LOGGER.exception(
                "HAI Shutter Manager: failed to set up platform %s", platform
            )
    if not loaded:
        _LOGGER.error("HAI Shutter Manager: no platforms loaded")
        return False

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
            hass.services.async_remove(DOMAIN, SERVICE_SET_TEST_OVERRIDE)
            hass.services.async_remove(DOMAIN, SERVICE_SET_VIRTUAL_STATE)
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

    async def _handle_set_test_override(call: ServiceCall) -> None:
        cover_id = call.data.get("cover_id")
        key = call.data["key"]
        value = call.data["value"]
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if not isinstance(coordinator, ShutterCoordinator):
                continue
            if not coordinator.test_mode:
                _LOGGER.warning("set_test_override ignored: test mode is off")
                return
            if cover_id:
                if coordinator.has_cover(cover_id):
                    await coordinator.async_set_cover_option(cover_id, key, value)
                    await coordinator.async_request_refresh()
                return
            await coordinator.async_set_hub_option(key, value)
            await coordinator.async_request_refresh()
            return
        _LOGGER.warning("set_test_override: no coordinator found")

    async def _handle_set_virtual_state(call: ServiceCall) -> None:
        cover_id = call.data["cover_id"]
        state = call.data["state"]
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, ShutterCoordinator) and coordinator.has_cover(
                cover_id
            ):
                await coordinator.async_set_virtual_state(cover_id, state)
                return
        _LOGGER.warning("set_virtual_state: unknown cover %s", cover_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COVER_OPTION,
        _handle_set_cover_option,
        schema=_SET_OPTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEST_OVERRIDE,
        _handle_set_test_override,
        schema=_SET_TEST_OVERRIDE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VIRTUAL_STATE,
        _handle_set_virtual_state,
        schema=_SET_VIRTUAL_STATE_SCHEMA,
    )
