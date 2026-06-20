"""Number entities: per-cover action delay, eave length and desired temperature."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTION_DELAY,
    CONF_DESIRED_TEMP,
    CONF_EAVE_LENGTH,
    CONF_TEST_OUTDOOR_TEMP,
    CONF_TEST_ROOM_TEMP,
    CONF_TEST_SUN_AZIMUTH,
    CONF_TEST_SUN_ELEVATION,
    DEFAULT_ACTION_DELAY,
    DEFAULT_DESIRED_TEMP,
    DEFAULT_EAVE_LENGTH,
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


_NUMBERS: tuple[HaiNumberDescription, ...] = (
    HaiNumberDescription(
        key=CONF_ACTION_DELAY,
        name="action delay",
        icon="mdi:timer-sand",
        unit=UnitOfTime.HOURS,
        min_value=0,
        max_value=24,
        step=0.5,
        default=DEFAULT_ACTION_DELAY,
    ),
    HaiNumberDescription(
        key=CONF_EAVE_LENGTH,
        name="eave length",
        icon="mdi:ruler",
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=300,
        step=1,
        default=DEFAULT_EAVE_LENGTH,
    ),
    HaiNumberDescription(
        key=CONF_DESIRED_TEMP,
        name="desired temperature",
        icon="mdi:thermometer",
        unit=UnitOfTemperature.CELSIUS,
        min_value=10,
        max_value=35,
        step=0.5,
        default=DEFAULT_DESIRED_TEMP,
    ),
)


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

_TEST_COVER_NUMBERS: tuple[HaiNumberDescription, ...] = (
    HaiNumberDescription(
        key=CONF_TEST_ROOM_TEMP,
        name="test room temperature",
        icon="mdi:home-thermometer",
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=40,
        step=0.5,
        default=DEFAULT_DESIRED_TEMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    for cover_id in coordinator.covers:
        for description in _NUMBERS:
            entities.append(
                HaiCoverNumber(coordinator, entry, cover_id, description)
            )
        for description in _TEST_COVER_NUMBERS:
            entities.append(
                HaiTestCoverNumber(coordinator, entry, cover_id, description)
            )
    for description in _TEST_NUMBERS:
        entities.append(HaiTestHubNumber(coordinator, entry, description))
    async_add_entities(entities)


class HaiCoverNumber(HaiBaseEntity, NumberEntity):
    """A per-cover configurable number stored in the config entry options."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: ShutterCoordinator,
        entry: ConfigEntry,
        cover_id: str,
        description: HaiNumberDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self._cover_id = cover_id
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{cover_id}_{description.key}"
        self._attr_name = f"{self._cover_name(cover_id)} {description.name}"
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

    @property
    def native_value(self) -> float:
        cfg = self.coordinator.cover_config(self._cover_id)
        return float(cfg.get(self._description.key, self._description.default))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_cover_option(
            self._cover_id, self._description.key, value
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
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def native_value(self) -> float:
        value = self.coordinator.hub.get(self._description.key)
        if value is None:
            return self._description.default
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_hub_option(self._description.key, value)
        await self.coordinator.async_request_refresh()


class HaiTestCoverNumber(HaiBaseEntity, NumberEntity):
    """Per-cover test room temperature override."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: ShutterCoordinator,
        entry: ConfigEntry,
        cover_id: str,
        description: HaiNumberDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self._cover_id = cover_id
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{cover_id}_{description.key}"
        self._attr_name = f"{self._cover_name(cover_id)} {description.name}"
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def native_value(self) -> float | None:
        cfg = self.coordinator.cover_config(self._cover_id)
        value = cfg.get(self._description.key)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_cover_option(
            self._cover_id, self._description.key, value
        )
        await self.coordinator.async_request_refresh()
