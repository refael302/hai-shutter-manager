"""Sensors: action log and season."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LogSensor(coordinator, entry), SeasonSensor(coordinator, entry), TestModeSensor(coordinator, entry)])


class LogSensor(HaiBaseEntity, SensorEntity):
    """Exposes the last action and recent history."""

    _attr_icon = "mdi:script-text"
    _attr_translation_key = "action_log"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_log"
        self._attr_name = "Action log"

    @property
    def native_value(self) -> str | None:
        log = (self.coordinator.data or {}).get("log", [])
        if not log:
            return "idle"
        return log[0]["message"][:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        log = (self.coordinator.data or {}).get("log", [])
        return {"history": log}


class SeasonSensor(HaiBaseEntity, SensorEntity):
    """Current season used by the engine."""

    _attr_icon = "mdi:sun-snowflake"
    _attr_translation_key = "season"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_season"
        self._attr_name = "Season"

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("season")


class TestModeSensor(HaiBaseEntity, SensorEntity):
    """Shows whether test mode is active."""

    _attr_icon = "mdi:flask"
    _attr_translation_key = "test_mode"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_mode"
        self._attr_name = "Test mode"

    @property
    def native_value(self) -> str:
        return "active" if self.coordinator.test_mode else "off"
