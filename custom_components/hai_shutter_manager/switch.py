"""Switch: per-cover automation enable/pause (the conditioning toggle)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENABLED,
    CONF_TEST_IS_DAY,
    CONF_TEST_IS_RAINING,
    CONF_TEST_MODE,
    CONF_TEST_USE_SUN_OVERRIDE,
    DEFAULT_TEST_IS_DAY,
    DEFAULT_TEST_IS_RAINING,
    DEFAULT_TEST_USE_SUN_OVERRIDE,
    DOMAIN,
)
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        TestModeSwitch(coordinator, entry),
        TestIsDaySwitch(coordinator, entry),
        TestIsRainingSwitch(coordinator, entry),
        TestUseSunOverrideSwitch(coordinator, entry),
    ]
    for cover_id in coordinator.covers:
        entities.append(CoverAutomationSwitch(coordinator, entry, cover_id))
    async_add_entities(entities)


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


class TestModeSwitch(HaiBaseEntity, SwitchEntity):
    """Master toggle: enables the virtual test sandbox at runtime.

    While on, the engine works on virtual shutter states and logs decisions to
    Telegram instead of moving real covers. Always available so it can be
    flipped from the dashboard without touching the integration options.
    """

    _attr_icon = "mdi:flask"
    _attr_translation_key = "test_mode"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_mode_switch"
        self._attr_name = "Test mode"

    @property
    def is_on(self) -> bool:
        return self.coordinator.test_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_hub_option(CONF_TEST_MODE, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_hub_option(CONF_TEST_MODE, False)


class _TestHubSwitch(HaiBaseEntity, SwitchEntity):
    """Base class for hub-level test override switches."""

    _hub_key: str
    _default: bool

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.hub.get(self._hub_key, self._default))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_hub_option(self._hub_key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_hub_option(self._hub_key, False)
        await self.coordinator.async_request_refresh()


class TestIsDaySwitch(_TestHubSwitch):
    _hub_key = CONF_TEST_IS_DAY
    _default = DEFAULT_TEST_IS_DAY
    _attr_icon = "mdi:weather-sunny"
    _attr_translation_key = "test_is_day"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_is_day"
        self._attr_name = "Test daytime override"


class TestIsRainingSwitch(_TestHubSwitch):
    _hub_key = CONF_TEST_IS_RAINING
    _default = DEFAULT_TEST_IS_RAINING
    _attr_icon = "mdi:weather-rainy"
    _attr_translation_key = "test_is_raining"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_is_raining"
        self._attr_name = "Test rain override"


class TestUseSunOverrideSwitch(_TestHubSwitch):
    _hub_key = CONF_TEST_USE_SUN_OVERRIDE
    _default = DEFAULT_TEST_USE_SUN_OVERRIDE
    _attr_icon = "mdi:sun-angle"
    _attr_translation_key = "test_use_sun_override"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_use_sun_override"
        self._attr_name = "Test manual sun angles"
