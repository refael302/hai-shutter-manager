"""Select entities for test-mode manual overrides."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TEST_SEASON, DOMAIN, SEASON_OPTIONS
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TestSeasonSelect(coordinator, entry)])


class TestSeasonSelect(HaiBaseEntity, SelectEntity):
    """Manual season override used while test mode is active."""

    _attr_icon = "mdi:calendar-sync"
    _attr_translation_key = "test_season"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_season"
        self._attr_name = "Test season override"
        self._attr_options = list(SEASON_OPTIONS)

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def current_option(self) -> str | None:
        return str(self.coordinator.hub.get(CONF_TEST_SEASON, SEASON_OPTIONS[2]))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_hub_option(CONF_TEST_SEASON, option)
        await self.coordinator.async_request_refresh()
