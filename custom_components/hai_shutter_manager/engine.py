"""Decision engine: decide the desired target state for a single cover.

The engine is intentionally pure-ish: it reads state from the coordinator and
returns a decision. The coordinator is responsible for applying motor-protection
guards (debounce, manual override, idempotency, daily limits) and for actually
issuing commands.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import (
    CONF_CLOSE_EVENING,
    CONF_CLOSE_RAIN,
    CONF_DESIRED_TEMP,
    DEFAULT_DESIRED_TEMP,
    PRIORITY_NORMAL,
    RAIN_HEAVY_THRESHOLD_MM,
    SEASON_SUMMER,
    SEASON_TRANSITION,
    SEASON_WINTER,
    TARGET_CLOSED,
    TARGET_OPEN,
)

# Hysteresis around the desired temperature (Celsius) to avoid oscillation.
TEMP_HYSTERESIS = 0.5


@dataclass(slots=True)
class Decision:
    """A decision produced by the engine."""

    target: str | None
    reason: str
    priority: str = PRIORITY_NORMAL


def decide_target(coordinator, cover_id: str, cfg: dict) -> Decision:
    """Return the desired logical target (open/closed) for a cover, or None."""
    raining = coordinator.is_raining
    is_day = coordinator.is_day

    # 1. Rain protection has the highest priority among comfort goals.
    if raining and cfg.get(CONF_CLOSE_RAIN):
        mm = coordinator.rain_intensity_mm
        if coordinator.rain_forecast_soon:
            if mm is not None:
                return Decision(
                    TARGET_CLOSED, f"rain forecast ({mm:.1f} mm in next hours)"
                )
            return Decision(TARGET_CLOSED, "rain forecast")
        if mm is not None and mm > RAIN_HEAVY_THRESHOLD_MM:
            return Decision(TARGET_CLOSED, f"heavy rain ({mm:.1f} mm)")
        return Decision(TARGET_CLOSED, "rain protection")

    # 2. Night handling.
    if not is_day:
        if cfg.get(CONF_CLOSE_EVENING):
            return Decision(TARGET_CLOSED, "evening close")
        return Decision(None, "night - no action")

    # 3. Daytime: combine season strategy with sun incidence.
    sun_hit = coordinator.sun_hits_now(cover_id, cfg)
    upcoming = coordinator.sun_hits_soon(cover_id, cfg)
    season = coordinator.season

    if season == SEASON_WINTER:
        # Maximize incoming sun: keep open, especially when sun reaches the window
        # or is about to.
        if sun_hit or upcoming:
            return Decision(TARGET_OPEN, "winter: capture sun")
        return Decision(TARGET_OPEN, "winter: keep open for daylight")

    if season == SEASON_SUMMER:
        # Minimize incoming sun: close while direct sun hits, otherwise open.
        if sun_hit:
            return Decision(TARGET_CLOSED, "summer: block sun")
        return Decision(TARGET_OPEN, "summer: no direct sun")

    # 4. Transition season: aim for the desired room temperature.
    try:
        desired = float(cfg.get(CONF_DESIRED_TEMP, DEFAULT_DESIRED_TEMP))
    except (TypeError, ValueError):
        desired = DEFAULT_DESIRED_TEMP
    room_temp = coordinator.get_area_temp(cover_id, cfg)

    if room_temp is None:
        # No temperature reference: default to letting light in without forcing
        # repeated moves.
        return Decision(None, "transition: no temperature reference")

    if room_temp > desired + TEMP_HYSTERESIS and sun_hit:
        return Decision(TARGET_CLOSED, f"transition: cooling ({room_temp} > {desired})")

    if room_temp < desired - TEMP_HYSTERESIS:
        return Decision(TARGET_OPEN, f"transition: heating ({room_temp} < {desired})")

    return Decision(None, "transition: within comfort band")
