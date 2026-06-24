"""Select entities for test-mode manual overrides."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TEST_IS_DAY,
    CONF_TEST_IS_RAINING,
    CONF_TEST_MODE,
    CONF_TEST_SEASON,
    CONF_TEST_USE_SUN_OVERRIDE,
    DEFAULT_TEST_IS_DAY,
    DEFAULT_TEST_IS_RAINING,
    DEFAULT_TEST_USE_SUN_OVERRIDE,
    DOMAIN,
    SEASON_OPTIONS,
    TARGET_CLOSED,
    TARGET_OPEN,
)
from .coordinator import ShutterCoordinator
from .entity import HaiBaseEntity

_TEST_DAY_OPTIONS = ("day", "night")
_TEST_RAIN_OPTIONS = ("dry", "rain")
_TEST_SUN_OPTIONS = ("automatic", "manual")
_TEST_MODE_OPTIONS = ("off", "active")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [
        TestModeSelect(coordinator, entry),
        TestSeasonSelect(coordinator, entry),
        TestIsDaySelect(coordinator, entry),
        TestIsRainingSelect(coordinator, entry),
        TestUseSunOverrideSelect(coordinator, entry),
    ]
    for cover_id in coordinator.covers:
        entities.append(TestShutterStateSelect(coordinator, entry, cover_id))
    async_add_entities(entities)


class TestModeSelect(HaiBaseEntity, SelectEntity):
    """Toggle test mode from the Controls section."""

    _attr_icon = "mdi:flask"
    _attr_translation_key = "test_mode"
    _attr_options = list(_TEST_MODE_OPTIONS)

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_mode_select"
        self._attr_name = "Test mode"

    @property
    def current_option(self) -> str | None:
        return "active" if self.coordinator.test_mode else "off"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_hub_option(CONF_TEST_MODE, option == "active")
        await self.coordinator.async_request_refresh()


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


class TestIsDaySelect(HaiBaseEntity, SelectEntity):
    """Manual day/night override while test mode is active."""

    _attr_icon = "mdi:theme-light-dark"
    _attr_translation_key = "test_is_day"
    _attr_options = list(_TEST_DAY_OPTIONS)

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_is_day_select"
        self._attr_name = "Test daytime override"

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def current_option(self) -> str | None:
        is_day = bool(self.coordinator.hub.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY))
        return "day" if is_day else "night"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_hub_option(CONF_TEST_IS_DAY, option == "day")
        await self.coordinator.async_request_refresh()


class TestIsRainingSelect(HaiBaseEntity, SelectEntity):
    """Manual rain override while test mode is active."""

    _attr_icon = "mdi:weather-rainy"
    _attr_translation_key = "test_is_raining"
    _attr_options = list(_TEST_RAIN_OPTIONS)

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_is_raining_select"
        self._attr_name = "Test rain override"

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def current_option(self) -> str | None:
        raining = bool(
            self.coordinator.hub.get(CONF_TEST_IS_RAINING, DEFAULT_TEST_IS_RAINING)
        )
        return "rain" if raining else "dry"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_hub_option(
            CONF_TEST_IS_RAINING, option == "rain"
        )
        await self.coordinator.async_request_refresh()


class TestUseSunOverrideSelect(HaiBaseEntity, SelectEntity):
    """Choose calculated sun vs manual sun angles in test mode."""

    _attr_icon = "mdi:sun-angle"
    _attr_translation_key = "test_use_sun_override"
    _attr_options = list(_TEST_SUN_OPTIONS)

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_use_sun_override_select"
        self._attr_name = "Test sun calculation"

    @property
    def available(self) -> bool:
        return self.coordinator.test_mode

    @property
    def current_option(self) -> str | None:
        manual = bool(
            self.coordinator.hub.get(
                CONF_TEST_USE_SUN_OVERRIDE, DEFAULT_TEST_USE_SUN_OVERRIDE
            )
        )
        return "manual" if manual else "automatic"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_hub_option(
            CONF_TEST_USE_SUN_OVERRIDE, option == "manual"
        )
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
