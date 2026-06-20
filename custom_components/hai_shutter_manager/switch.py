"""Switch: per-cover automation enable/pause (the conditioning toggle)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLED, DOMAIN
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CoverAutomationSwitch(coordinator, entry, cover_id)
        for cover_id in coordinator.covers
    )


class CoverAutomationSwitch(HaiBaseEntity, SwitchEntity):
    """Enables or pauses the integration's actions for a single cover."""

    _attr_icon = "mdi:robot"

    def __init__(
        self, coordinator: ShutterCoordinator, entry: ConfigEntry, cover_id: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._cover_id = cover_id
        self._attr_unique_id = f"{entry.entry_id}_{cover_id}_automation"
        self._attr_name = f"{self._cover_name(cover_id)} automation"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.cover_config(self._cover_id).get(CONF_ENABLED, True))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_cover_option(self._cover_id, CONF_ENABLED, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_cover_option(
            self._cover_id, CONF_ENABLED, False
        )
