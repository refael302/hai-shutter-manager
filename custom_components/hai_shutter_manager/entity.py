"""Shared base entity for HAI Shutter Manager."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from homeassistant.helpers.device_registry import DeviceInfo
except ImportError:  # Home Assistant < 2024.2
    from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, INTEGRATION_ICON
from .coordinator import ShutterCoordinator


class HaiBaseEntity(CoordinatorEntity[ShutterCoordinator]):
    """Base entity tying everything to a single hub device."""

    _attr_has_entity_name = True
    _attr_icon = INTEGRATION_ICON

    def __init__(self, coordinator: ShutterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success or self.coordinator.data is not None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="HAI Shutter Manager",
            manufacturer="HAI",
            model="Shutter Manager",
            configuration_url="https://github.com/refael302/hai-shutter-manager",
        )

    def _cover_name(self, cover_id: str) -> str:
        state = self.hass.states.get(cover_id)
        if state is not None:
            return state.attributes.get("friendly_name", cover_id)
        return cover_id
