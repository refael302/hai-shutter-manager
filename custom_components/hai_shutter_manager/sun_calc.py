"""Sun-position and window-geometry calculations.

The core question this module answers is: *does direct sunlight currently reach a
given window?* That requires two independent checks:

1. Azimuth match - the sun must be roughly in front of the window (within the
   window's horizontal field of view). This is what makes an east-facing window
   only relevant in the morning, a west-facing one in the afternoon, etc.
2. Elevation + eave geometry - even when the sun faces the window, an awning/eave
   above the window casts a shadow. The shadow drop is ``eave_length * tan(elevation)``.
   If that drop is smaller than the window height, some sunlight still enters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from astral import Observer
from astral.sun import azimuth as astral_azimuth
from astral.sun import elevation as astral_elevation


@dataclass(slots=True)
class SunHit:
    """Result of a sun-incidence check."""

    hits: bool
    azimuth: float
    elevation: float
    sunlit_fraction: float


def angular_difference(a: float, b: float) -> float:
    """Smallest absolute difference between two azimuths (0-180 degrees)."""
    return abs((a - b + 180) % 360 - 180)


def sun_position(observer: Observer, when: datetime) -> tuple[float, float]:
    """Return (azimuth, elevation) for the observer at the given UTC datetime."""
    return astral_azimuth(observer, when), astral_elevation(observer, when)


def evaluate_window_from_sun(
    sun_azimuth: float,
    sun_elevation: float,
    window_azimuth: float,
    eave_length_cm: float,
    window_height_cm: float,
    fov_deg: float,
) -> SunHit:
    """Evaluate sun incidence using manually supplied sun angles (test mode)."""
    az, el = sun_azimuth, sun_elevation

    if el <= 0:
        return SunHit(False, az, el, 0.0)

    if angular_difference(az, window_azimuth) > fov_deg / 2:
        return SunHit(False, az, el, 0.0)

    shadow_drop = eave_length_cm * math.tan(math.radians(el))
    if shadow_drop >= window_height_cm:
        return SunHit(False, az, el, 0.0)

    sunlit_fraction = max(0.0, 1.0 - shadow_drop / window_height_cm)
    return SunHit(sunlit_fraction > 0.0, az, el, sunlit_fraction)


def evaluate_window(
    observer: Observer,
    when: datetime,
    window_azimuth: float,
    eave_length_cm: float,
    window_height_cm: float,
    fov_deg: float,
) -> SunHit:
    """Evaluate whether direct sun reaches a window at a point in time."""
    az, el = sun_position(observer, when)

    if el <= 0:
        return SunHit(False, az, el, 0.0)

    if angular_difference(az, window_azimuth) > fov_deg / 2:
        return SunHit(False, az, el, 0.0)

    shadow_drop = eave_length_cm * math.tan(math.radians(el))
    if shadow_drop >= window_height_cm:
        # The eave fully shades the window.
        return SunHit(False, az, el, 0.0)

    sunlit_fraction = max(0.0, 1.0 - shadow_drop / window_height_cm)
    return SunHit(sunlit_fraction > 0.0, az, el, sunlit_fraction)


def forecast_window_hits(
    observer: Observer,
    start: datetime,
    window_azimuth: float,
    eave_length_cm: float,
    window_height_cm: float,
    fov_deg: float,
    hours_ahead: int = 24,
    step_minutes: int = 30,
) -> list[datetime]:
    """Return the timestamps within the next ``hours_ahead`` where sun hits.

    Used so the engine can prepare in advance (e.g. know that a west window will
    receive sun in a few hours).
    """
    hits: list[datetime] = []
    steps = int(hours_ahead * 60 / step_minutes)
    for i in range(steps + 1):
        when = start + timedelta(minutes=i * step_minutes)
        result = evaluate_window(
            observer,
            when,
            window_azimuth,
            eave_length_cm,
            window_height_cm,
            fov_deg,
        )
        if result.hits:
            hits.append(when)
    return hits
