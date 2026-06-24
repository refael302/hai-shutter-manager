"""Number entities: hub-level test overrides only."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TEST_OUTDOOR_TEMP,
    CONF_TEST_SUN_AZIMUTH,
    CONF_TEST_SUN_ELEVATION,
    DEFAULT_TEST_SUN_AZIMUTH,
    DEFAULT_TEST_SUN_ELEVATION,
    DOMAIN,
)
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


@dataclass(frozen=True, kw_only=True)
class HaiNumberDescription:
    key: str
    name: str
    icon: str
    unit: str
    min_value: float
    max_value: float
    step: float
    default: float


_TEST_NUMBERS: tuple[HaiNumberDescription, ...] = (
    HaiNumberDescription(
        key=CONF_TEST_OUTDOOR_TEMP,
        name="test outdoor temperature",
        icon="mdi:thermometer-lines",
        unit=UnitOfTemperature.CELSIUS,
        min_value=-30,
        max_value=50,
        step=0.5,
        default=22.0,
    ),
    HaiNumberDescription(
        key=CONF_TEST_SUN_AZIMUTH,
        name="test sun azimuth",
        icon="mdi:compass",
        unit="°",
        min_value=0,
        max_value=359,
        step=1,
        default=DEFAULT_TEST_SUN_AZIMUTH,
    ),
    HaiNumberDescription(
        key=CONF_TEST_SUN_ELEVATION,
        name="test sun elevation",
        icon="mdi:angle-acute",
        unit="°",
        min_value=0,
        max_value=90,
        step=1,
        default=DEFAULT_TEST_SUN_ELEVATION,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HaiTestHubNumber(coordinator, entry, description)
        for description in _TEST_NUMBERS
    )


class HaiTestHubNumber(HaiBaseEntity, NumberEntity):
    """Hub-level test override (available only in test mode)."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: ShutterCoordinator,
        entry: ConfigEntry,
        description: HaiNumberDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name.title()
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

    @property
    def native_value(self) -> float:
        value = self.coordinator.hub.get(self._description.key)
        if value is None:
            return self._description.default
        try:
            return float(value)
        except (TypeError, ValueError):
            return self._description.default

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_ensure_test_mode()
        await self.coordinator.async_set_hub_option(self._description.key, value)
        await self.coordinator.async_request_refresh()
