"""Sensors: hub status and a single overview of all managed covers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    async_add_entities(
        [
            LogSensor(coordinator, entry),
            SeasonSensor(coordinator, entry),
            OutdoorTempSensor(coordinator, entry),
            CoversOverviewSensor(coordinator, entry),
        ]
    )


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


class OutdoorTempSensor(HaiBaseEntity, SensorEntity):
    """Outdoor temperature used by the engine (override-aware in test mode)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"
    _attr_translation_key = "outdoor_temp"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_outdoor_temp"
        self._attr_name = "Outdoor temperature"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("outdoor_temp")


class CoversOverviewSensor(HaiBaseEntity, SensorEntity):
    """Single sensor summarising every managed cover (state, reason, config).

    Used by the Lovelace table card instead of one entity per cover.
    """

    _attr_icon = "mdi:window-shutter"
    _attr_translation_key = "covers_overview"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_covers_overview"
        self._attr_name = "Covers overview"

    @property
    def native_value(self) -> int:
        covers = (self.coordinator.data or {}).get("covers", {})
        return len(covers)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        covers = data.get("covers", {})
        return {
            "test_mode": data.get("test_mode", False),
            "covers": covers,
        }
