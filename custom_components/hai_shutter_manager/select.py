"""Select entities for test-mode manual overrides (hub level only)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TEST_ACTIVE_COVER,
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
_TEST_STATE_OPTIONS = (TARGET_OPEN, TARGET_CLOSED)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ShutterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TestModeSelect(coordinator, entry),
            TestSeasonSelect(coordinator, entry),
            TestIsDaySelect(coordinator, entry),
            TestIsRainingSelect(coordinator, entry),
            TestUseSunOverrideSelect(coordinator, entry),
            TestActiveCoverSelect(coordinator, entry),
            TestVirtualStateSelect(coordinator, entry),
        ]
    )


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
    def current_option(self) -> str | None:
        return str(self.coordinator.hub.get(CONF_TEST_SEASON, SEASON_OPTIONS[2]))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_ensure_test_mode()
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
    def current_option(self) -> str | None:
        is_day = bool(self.coordinator.hub.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY))
        return "day" if is_day else "night"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_ensure_test_mode()
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
    def current_option(self) -> str | None:
        raining = bool(
            self.coordinator.hub.get(CONF_TEST_IS_RAINING, DEFAULT_TEST_IS_RAINING)
        )
        return "rain" if raining else "dry"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_ensure_test_mode()
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
    def current_option(self) -> str | None:
        manual = bool(
            self.coordinator.hub.get(
                CONF_TEST_USE_SUN_OVERRIDE, DEFAULT_TEST_USE_SUN_OVERRIDE
            )
        )
        return "manual" if manual else "automatic"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_ensure_test_mode()
        await self.coordinator.async_set_hub_option(
            CONF_TEST_USE_SUN_OVERRIDE, option == "manual"
        )
        await self.coordinator.async_request_refresh()


class TestActiveCoverSelect(HaiBaseEntity, SelectEntity):
    """Pick which managed cover test actions apply to."""

    _attr_icon = "mdi:window-shutter"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_active_cover"
        self._attr_name = "Test active cover"
        self._attr_translation_key = "test_active_cover"

    @property
    def available(self) -> bool:
        return bool(self.coordinator.covers)

    @property
    def options(self) -> list[str]:
        return list(self.coordinator.covers.keys())

    @property
    def current_option(self) -> str | None:
        active = self.coordinator.hub.get(CONF_TEST_ACTIVE_COVER)
        if active in self.coordinator.covers:
            return str(active)
        covers = list(self.coordinator.covers.keys())
        return covers[0] if covers else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_ensure_test_mode()
        await self.coordinator.async_set_hub_option(CONF_TEST_ACTIVE_COVER, option)


class TestVirtualStateSelect(HaiBaseEntity, SelectEntity):
    """Set the virtual open/closed state of the active test cover."""

    _attr_icon = "mdi:window-shutter-open"
    _attr_options = list(_TEST_STATE_OPTIONS)
    _attr_translation_key = "test_virtual_state"

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_virtual_state"
        self._attr_name = "Test virtual state"

    @property
    def available(self) -> bool:
        return self._active_cover() is not None

    def _active_cover(self) -> str | None:
        active = self.coordinator.hub.get(CONF_TEST_ACTIVE_COVER)
        if active in self.coordinator.covers:
            return str(active)
        covers = list(self.coordinator.covers.keys())
        return covers[0] if covers else None

    @property
    def current_option(self) -> str | None:
        cover_id = self._active_cover()
        if cover_id is None:
            return None
        covers = (self.coordinator.data or {}).get("covers", {})
        snapshot = covers.get(cover_id, {})
        return snapshot.get("virtual_state") or snapshot.get("state") or TARGET_CLOSED

    async def async_select_option(self, option: str) -> None:
        cover_id = self._active_cover()
        if cover_id is None:
            return
        await self.coordinator.async_ensure_test_mode()
        await self.coordinator.async_set_virtual_state(cover_id, option)
