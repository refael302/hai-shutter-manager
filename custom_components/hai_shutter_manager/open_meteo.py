"""Open-Meteo forecast client (no API key required)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    MIN_FORECAST_PRECIPITATION_MM,
    OPEN_METEO_FORECAST_HOURS,
    OPEN_METEO_FORECAST_URL,
    RAIN_FORECAST_HOURS,
)

_LOGGER = logging.getLogger(__name__)

# WMO weather codes indicating rain (drizzle, rain, showers, thunderstorm).
_RAIN_WEATHER_CODES = frozenset(
    {
        51,
        53,
        55,
        56,
        57,
        61,
        63,
        65,
        66,
        67,
        80,
        81,
        82,
        95,
        96,
        99,
    }
)


@dataclass(frozen=True, slots=True)
class OpenMeteoSnapshot:
    """Parsed Open-Meteo forecast data used by the coordinator."""

    temperature_c: float | None
    current_precipitation_mm: float | None
    forecast_max_precipitation_mm: float | None
    rain_now: bool
    rain_forecast: bool
    fetched_at: datetime


def parse_open_meteo_response(
    payload: dict[str, Any],
    *,
    now: datetime,
    rain_forecast_hours: int = RAIN_FORECAST_HOURS,
) -> OpenMeteoSnapshot | None:
    """Parse an Open-Meteo /forecast JSON payload into a snapshot."""
    current = payload.get("current")
    hourly = payload.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        return None

    temperature = _coerce_float(current.get("temperature_2m"))
    current_precip = _max_float(
        current.get("precipitation"), current.get("rain")
    )
    weather_code = current.get("weather_code")
    rain_now = _is_raining(current_precip, weather_code)

    times = hourly.get("time")
    precip_series = hourly.get("precipitation")
    rain_series = hourly.get("rain")
    if not isinstance(times, list):
        return OpenMeteoSnapshot(
            temperature_c=temperature,
            current_precipitation_mm=current_precip,
            forecast_max_precipitation_mm=None,
            rain_now=rain_now,
            rain_forecast=False,
            fetched_at=now,
        )

    forecast_end = now + timedelta(hours=rain_forecast_hours)
    max_forecast_precip: float | None = None
    rain_forecast = False

    for idx, time_str in enumerate(times):
        when = _parse_hourly_time(time_str)
        if when is None or when <= now or when > forecast_end:
            continue
        hour_precip = _max_float(
            _series_value(precip_series, idx),
            _series_value(rain_series, idx),
        )
        if hour_precip is None:
            continue
        max_forecast_precip = (
            hour_precip
            if max_forecast_precip is None
            else max(max_forecast_precip, hour_precip)
        )
        if hour_precip >= MIN_FORECAST_PRECIPITATION_MM:
            rain_forecast = True

    return OpenMeteoSnapshot(
        temperature_c=temperature,
        current_precipitation_mm=current_precip,
        forecast_max_precipitation_mm=max_forecast_precip,
        rain_now=rain_now,
        rain_forecast=rain_forecast and not rain_now,
        fetched_at=now,
    )


class OpenMeteoClient:
    """Fetch weather forecast data from Open-Meteo."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)

    async def async_fetch(
        self, latitude: float, longitude: float
    ) -> OpenMeteoSnapshot | None:
        """Return parsed forecast data for the given coordinates."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,rain,weather_code",
            "hourly": "precipitation,rain,precipitation_probability,weather_code",
            "forecast_hours": OPEN_METEO_FORECAST_HOURS,
            "timezone": "auto",
        }
        try:
            async with self._session.get(
                OPEN_METEO_FORECAST_URL, params=params, timeout=15
            ) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "Open-Meteo request failed with HTTP %s", response.status
                    )
                    return None
                payload = await response.json()
        except Exception as err:  # noqa: BLE001 - network errors are expected
            _LOGGER.warning("Open-Meteo request failed: %s", err)
            return None

        if not isinstance(payload, dict):
            return None
        return parse_open_meteo_response(payload, now=dt_util.now())


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _max_float(*values: Any) -> float | None:
    parsed = [_coerce_float(v) for v in values]
    valid = [v for v in parsed if v is not None]
    return max(valid) if valid else None


def _series_value(series: Any, index: int) -> Any | None:
    if not isinstance(series, list) or index >= len(series):
        return None
    return series[index]


def _is_raining(precipitation_mm: float | None, weather_code: Any) -> bool:
    if precipitation_mm is not None and precipitation_mm >= MIN_FORECAST_PRECIPITATION_MM:
        return True
    try:
        return int(weather_code) in _RAIN_WEATHER_CODES
    except (TypeError, ValueError):
        return False


def _parse_hourly_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # Open-Meteo returns local wall-clock times when timezone=auto.
        return dt_util.as_local(parsed)
    return parsed
