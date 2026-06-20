"""Binary sensors: day/night, rain, and per-cover open/closed state."""

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
    entities: list[BinarySensorEntity] = [
        DayNightSensor(coordinator, entry),
        RainSensor(coordinator, entry),
    ]
    for cover_id in coordinator.covers:
        entities.append(CoverStateSensor(coordinator, entry, cover_id))
    async_add_entities(entities)


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
        return bool((self.coordinator.data or {}).get("is_raining"))


class CoverStateSensor(HaiBaseEntity, BinarySensorEntity):
    """Mirrors a cover's open/closed state and exposes its full config.

    The Lovelace card reads its attributes to render the table.
    """

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self, coordinator: ShutterCoordinator, entry: ConfigEntry, cover_id: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._cover_id = cover_id
        self._attr_unique_id = f"{entry.entry_id}_{cover_id}_state"
        self._attr_name = f"{self._cover_name(cover_id)} state"

    def _snapshot(self) -> dict[str, Any]:
        covers = (self.coordinator.data or {}).get("covers", {})
        return covers.get(self._cover_id, {})

    @property
    def available(self) -> bool:
        return self._snapshot().get("available", False)

    @property
    def is_on(self) -> bool:
        return self._snapshot().get("state") == "open"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        attrs: dict[str, Any] = {
            "cover_id": self._cover_id,
            "target": snapshot.get("target"),
            "reason": snapshot.get("reason"),
            "manual_until": snapshot.get("manual_until"),
            "last_action": snapshot.get("last_action"),
            "sun_hit": snapshot.get("sun_hit"),
            "sunlit_fraction": snapshot.get("sunlit_fraction"),
            "moves_today": snapshot.get("moves_today"),
        }
        attrs.update(snapshot.get("config", {}))
        return attrs
