"""Select entities for test-mode manual overrides."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TEST_SEASON,
    DOMAIN,
    SEASON_OPTIONS,
    TARGET_CLOSED,
    TARGET_OPEN,
)
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [TestSeasonSelect(coordinator, entry)]
    for cover_id in coordinator.covers:
        entities.append(TestShutterStateSelect(coordinator, entry, cover_id))
    async_add_entities(entities)


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


class TestShutterStateSelect(HaiBaseEntity, SelectEntity):
    """Manually set a cover's virtual open/closed state while test mode is active."""

    _attr_icon = "mdi:window-shutter"
    _attr_options = [TARGET_OPEN, TARGET_CLOSED]

    def __init__(
        self, coordinator: ShutterCoordinator, entry: ConfigEntry, cover_id: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._cover_id = cover_id
        self._attr_unique_id = f"{entry.entry_id}_{cover_id}_test_state"
        self._attr_name = f"{self._cover_name(cover_id)} test shutter state"

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def current_option(self) -> str | None:
        covers = (self.coordinator.data or {}).get("covers", {})
        snapshot = covers.get(self._cover_id, {})
        return snapshot.get("virtual_state") or snapshot.get("state")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_virtual_state(self._cover_id, option)
