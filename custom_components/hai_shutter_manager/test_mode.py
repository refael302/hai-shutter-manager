"""Helpers for test mode logging."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_ACTION_DELAY,
    CONF_DESIRED_TEMP,
    CONF_DIRECTION,
    CONF_EAVE_LENGTH,
    CONF_MAX_MOVES_PER_DAY,
    DEFAULT_ACTION_DELAY,
    DEFAULT_DESIRED_TEMP,
    DEFAULT_EAVE_LENGTH,
    DEFAULT_MAX_MOVES_PER_DAY,
)


def format_test_action_log(
    cover_id: str,
    friendly_name: str,
    *,
    action: str,
    reason: str,
    previous_state: str | None,
    virtual_state: str,
    season: str,
    is_day: bool,
    is_raining: bool,
    sun_hit: bool,
    sunlit_fraction: float,
    sun_azimuth: float | None,
    sun_elevation: float | None,
    room_temp: float | None,
    cfg: dict[str, Any],
    moves_today: int,
    test_overrides: dict[str, Any],
) -> str:
    """Build a detailed Telegram message for a virtual test action."""
    direction = cfg.get(CONF_DIRECTION, "S")
    desired = cfg.get(CONF_DESIRED_TEMP, DEFAULT_DESIRED_TEMP)
    eave = cfg.get(CONF_EAVE_LENGTH, DEFAULT_EAVE_LENGTH)
    delay = cfg.get(CONF_ACTION_DELAY, DEFAULT_ACTION_DELAY)
    max_moves = cfg.get(CONF_MAX_MOVES_PER_DAY, DEFAULT_MAX_MOVES_PER_DAY)

    lines = [
        "[TEST MODE]",
        f"Shutter: {friendly_name}",
        f"Entity: {cover_id}",
        f"Virtual action: {action.upper()}",
        f"Reason: {reason}",
        "---",
        f"Previous virtual state: {previous_state or 'unknown'}",
        f"New virtual state: {virtual_state}",
        "---",
        "Environment (manual overrides applied):",
        f"  Season: {season}",
        f"  Daytime: {'yes' if is_day else 'no'}",
        f"  Rain: {'yes' if is_raining else 'no'}",
        f"  Room temp: {_fmt_temp(room_temp)} (target: {desired}°C)",
        f"  Outdoor temp override: {_fmt_temp(test_overrides.get('outdoor_temp'))}",
        "---",
        "Sun:",
        f"  Hits window: {'yes' if sun_hit else 'no'} ({sunlit_fraction:.0%} lit)",
        f"  Window direction: {direction}",
    ]
    if sun_azimuth is not None and sun_elevation is not None:
        lines.append(
            f"  Sun azimuth/elevation (override): {sun_azimuth:.1f}° / {sun_elevation:.1f}°"
        )
    lines.extend(
        [
            f"  Eave length: {eave} cm",
            "---",
            f"Action delay: {delay} h | Moves today: {moves_today}/{max_moves}",
            "Real shutter was NOT moved.",
        ]
    )
    return "\n".join(lines)


def format_test_skip_log(
    cover_id: str,
    friendly_name: str,
    *,
    reason: str,
    virtual_state: str | None,
    season: str,
    is_day: bool,
    is_raining: bool,
    sun_hit: bool,
    target: str | None,
) -> str:
    """Detailed log when the engine decides not to act in test mode."""
    return "\n".join(
        [
            "[TEST MODE - no action]",
            f"Shutter: {friendly_name} ({cover_id})",
            f"Virtual state: {virtual_state or 'unknown'}",
            f"Would target: {target or 'none'}",
            f"Skipped: {reason}",
            f"Season={season} | Day={'yes' if is_day else 'no'} | "
            f"Rain={'yes' if is_raining else 'no'} | Sun hit={'yes' if sun_hit else 'no'}",
        ]
    )


def _fmt_temp(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}°C"
