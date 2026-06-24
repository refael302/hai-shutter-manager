"""Location resolution for sun, weather, and season."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_LOCATION

_LOGGER = logging.getLogger(__name__)

_LOCATION_EPS = 0.0001


def location_form_default(hass: HomeAssistant, defaults: dict[str, Any]) -> dict[str, float]:
    """Default map pin for the config flow (stored override or HA home)."""
    stored = defaults.get(CONF_LOCATION)
    if stored:
        return {
            "latitude": float(stored["latitude"]),
            "longitude": float(stored["longitude"]),
        }
    return {
        "latitude": hass.config.latitude,
        "longitude": hass.config.longitude,
    }


def normalize_location(
    hass: HomeAssistant, location: dict[str, float] | None
) -> dict[str, float] | None:
    """Return a location to store, or None to follow the HA home location."""
    if not location:
        return None
    lat = float(location["latitude"])
    lon = float(location["longitude"])
    if (
        abs(lat - hass.config.latitude) <= _LOCATION_EPS
        and abs(lon - hass.config.longitude) <= _LOCATION_EPS
    ):
        return None
    return {"latitude": lat, "longitude": lon}


def resolve_location(
    hass: HomeAssistant,
    data: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Return the effective latitude and longitude."""
    loc: Any = None
    if options and CONF_LOCATION in options:
        loc = options[CONF_LOCATION]
    else:
        loc = data.get(CONF_LOCATION)
    if isinstance(loc, dict):
        try:
            return float(loc["latitude"]), float(loc["longitude"])
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Invalid location in config; using HA home location")
    return hass.config.latitude, hass.config.longitude
