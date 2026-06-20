"""Season detection helpers."""

from __future__ import annotations

from datetime import datetime

from .const import (
    DEFAULT_HEMISPHERE,
    SEASON_SUMMER,
    SEASON_TRANSITION,
    SEASON_WINTER,
)

# Month -> season for the northern hemisphere.
_NORTH = {
    12: SEASON_WINTER,
    1: SEASON_WINTER,
    2: SEASON_WINTER,
    3: SEASON_TRANSITION,
    4: SEASON_TRANSITION,
    5: SEASON_TRANSITION,
    6: SEASON_SUMMER,
    7: SEASON_SUMMER,
    8: SEASON_SUMMER,
    9: SEASON_TRANSITION,
    10: SEASON_TRANSITION,
    11: SEASON_TRANSITION,
}

# Southern hemisphere = shift winter/summer.
_SOUTH = {
    month: (
        SEASON_SUMMER
        if season == SEASON_WINTER
        else SEASON_WINTER
        if season == SEASON_SUMMER
        else SEASON_TRANSITION
    )
    for month, season in _NORTH.items()
}


def current_season(now: datetime, hemisphere: str = DEFAULT_HEMISPHERE) -> str:
    """Return the meteorological season for the given datetime."""
    table = _SOUTH if hemisphere == "south" else _NORTH
    return table[now.month]
