"""Remove entity-registry entries that belong to retired platforms/entities."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Unique-id suffixes for hub entities created by the current integration.
_HUB_ENTITY_SUFFIXES: tuple[str, ...] = (
    "_log",
    "_season",
    "_outdoor_temp",
    "_covers_overview",
    "_day_night",
    "_rain",
    "_test_mode_select",
    "_test_season",
    "_test_is_day_select",
    "_test_is_raining_select",
    "_test_use_sun_override_select",
    "_test_active_cover",
    "_test_virtual_state",
    "_test_outdoor_temp",
    "_test_sun_azimuth",
    "_test_sun_elevation",
)


def expected_unique_ids(entry_id: str) -> set[str]:
    return {f"{entry_id}{suffix}" for suffix in _HUB_ENTITY_SUFFIXES}


def cleanup_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop orphaned entities from older releases (per-cover entities, switch, etc.)."""
    er_reg = er.async_get(hass)
    allowed = expected_unique_ids(entry.entry_id)
    for entity_entry in er.async_entries_for_config_entry(er_reg, entry.entry_id):
        if entity_entry.platform != DOMAIN:
            continue
        if entity_entry.unique_id in allowed:
            continue
        _LOGGER.info(
            "Removing stale %s entity %s (unique_id=%s)",
            entity_entry.domain,
            entity_entry.entity_id,
            entity_entry.unique_id,
        )
        er_reg.async_remove(entity_entry.entity_id)
