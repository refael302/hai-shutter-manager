"""Binary sensors: day/night and rain (hub level only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    async_add_entities(
        [
            DayNightSensor(coordinator, entry),
            RainSensor(coordinator, entry),
        ]
    )


class DayNightSensor(HaiBaseEntity, BinarySensorEntity):
    _attr_translation_key = "day_night"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_day_night"
        self._attr_name = "Daytime"

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get("is_day"))


class RainSensor(HaiBaseEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_translation_key = "rain"
    _attr_icon = "mdi:weather-rainy"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_rain"
        self._attr_name = "Rain"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("is_raining_raw"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "confirmed_for_close": bool(data.get("is_raining")),
            "rain_forecast_soon": bool(data.get("rain_forecast_soon")),
            "open_meteo_available": bool(data.get("open_meteo_available")),
        }
