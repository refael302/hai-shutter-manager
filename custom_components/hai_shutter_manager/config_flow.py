"""Config and options flow for HAI Shutter Manager."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTION_DELAY,
    CONF_CLOSE_EVENING,
    CONF_CLOSE_RAIN,
    CONF_COVERS,
    CONF_DESIRED_TEMP,
    CONF_DIRECTION,
    CONF_EAVE_LENGTH,
    CONF_HEMISPHERE,
    CONF_MAX_MOVES_PER_DAY,
    CONF_NOTIFY_LEVELS,
    CONF_OPEN_MORNING,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_RAIN_SENSOR,
    CONF_TELEGRAM_BOT_TOKEN,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_NOTIFY_SERVICE,
    CONF_TEST_IS_DAY,
    CONF_TEST_IS_RAINING,
    CONF_TEST_MODE,
    CONF_TEST_OUTDOOR_TEMP,
    CONF_TEST_SEASON,
    CONF_TEST_SUN_AZIMUTH,
    CONF_TEST_SUN_ELEVATION,
    CONF_TEST_USE_SUN_OVERRIDE,
    CONF_WEATHER_ENTITY,
    CONF_WINDOW_HEIGHT,
    CONFIG_VERSION,
    DEFAULT_ACTION_DELAY,
    DEFAULT_CLOSE_EVENING,
    DEFAULT_CLOSE_RAIN,
    DEFAULT_DESIRED_TEMP,
    DEFAULT_EAVE_LENGTH,
    DEFAULT_HEMISPHERE,
    DEFAULT_MAX_MOVES_PER_DAY,
    DEFAULT_OPEN_MORNING,
    DEFAULT_TEST_IS_DAY,
    DEFAULT_TEST_IS_RAINING,
    DEFAULT_TEST_MODE,
    DEFAULT_TEST_SEASON,
    DEFAULT_TEST_SUN_AZIMUTH,
    DEFAULT_TEST_SUN_ELEVATION,
    DEFAULT_TEST_USE_SUN_OVERRIDE,
    DEFAULT_WINDOW_HEIGHT,
    DIRECTIONS,
    DOMAIN,
    NOTIFY_LEVEL_OPTIONS,
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    SEASON_OPTIONS,
)


def _available_covers(hass) -> dict[str, str]:
    """Return a mapping of cover entity_id -> friendly name."""
    result: dict[str, str] = {}
    for state in hass.states.async_all("cover"):
        result[state.entity_id] = state.attributes.get(
            "friendly_name", state.entity_id
        )
    return result


def _hub_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_TELEGRAM_CHAT_ID,
                default=defaults.get(CONF_TELEGRAM_CHAT_ID, ""),
            ): str,
            vol.Optional(
                CONF_TELEGRAM_BOT_TOKEN,
                default=defaults.get(CONF_TELEGRAM_BOT_TOKEN, ""),
            ): str,
            vol.Optional(
                CONF_TELEGRAM_NOTIFY_SERVICE,
                default=defaults.get(CONF_TELEGRAM_NOTIFY_SERVICE, ""),
            ): str,
            vol.Optional(
                CONF_RAIN_SENSOR,
                default=defaults.get(CONF_RAIN_SENSOR, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
            ),
            vol.Optional(
                CONF_OUTDOOR_TEMP_SENSOR,
                default=defaults.get(CONF_OUTDOOR_TEMP_SENSOR, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_WEATHER_ENTITY,
                default=defaults.get(CONF_WEATHER_ENTITY, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(
                CONF_NOTIFY_LEVELS,
                default=defaults.get(
                    CONF_NOTIFY_LEVELS, [PRIORITY_NORMAL, PRIORITY_EMERGENCY]
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=NOTIFY_LEVEL_OPTIONS, multiple=True
                )
            ),
            vol.Optional(
                CONF_HEMISPHERE,
                default=defaults.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["north", "south"])
            ),
            vol.Optional(
                CONF_TEST_MODE,
                default=defaults.get(CONF_TEST_MODE, DEFAULT_TEST_MODE),
            ): bool,
            vol.Optional(
                CONF_TEST_IS_DAY,
                default=defaults.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY),
            ): bool,
            vol.Optional(
                CONF_TEST_IS_RAINING,
                default=defaults.get(CONF_TEST_IS_RAINING, DEFAULT_TEST_IS_RAINING),
            ): bool,
            vol.Optional(
                CONF_TEST_SEASON,
                default=defaults.get(CONF_TEST_SEASON, DEFAULT_TEST_SEASON),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=SEASON_OPTIONS)
            ),
            vol.Optional(
                CONF_TEST_OUTDOOR_TEMP,
                default=defaults.get(CONF_TEST_OUTDOOR_TEMP, 22.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TEST_SUN_AZIMUTH,
                default=defaults.get(CONF_TEST_SUN_AZIMUTH, DEFAULT_TEST_SUN_AZIMUTH),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TEST_SUN_ELEVATION,
                default=defaults.get(
                    CONF_TEST_SUN_ELEVATION, DEFAULT_TEST_SUN_ELEVATION
                ),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TEST_USE_SUN_OVERRIDE,
                default=defaults.get(
                    CONF_TEST_USE_SUN_OVERRIDE, DEFAULT_TEST_USE_SUN_OVERRIDE
                ),
            ): bool,
        }
    )


def _cover_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_DIRECTION, default=defaults.get(CONF_DIRECTION, "S")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(DIRECTIONS))
            ),
            vol.Required(
                CONF_EAVE_LENGTH,
                default=defaults.get(CONF_EAVE_LENGTH, DEFAULT_EAVE_LENGTH),
            ): vol.Coerce(float),
            vol.Required(
                CONF_WINDOW_HEIGHT,
                default=defaults.get(CONF_WINDOW_HEIGHT, DEFAULT_WINDOW_HEIGHT),
            ): vol.Coerce(float),
            vol.Required(
                CONF_DESIRED_TEMP,
                default=defaults.get(CONF_DESIRED_TEMP, DEFAULT_DESIRED_TEMP),
            ): vol.Coerce(float),
            vol.Required(
                CONF_ACTION_DELAY,
                default=defaults.get(CONF_ACTION_DELAY, DEFAULT_ACTION_DELAY),
            ): vol.Coerce(float),
            vol.Required(
                CONF_MAX_MOVES_PER_DAY,
                default=defaults.get(
                    CONF_MAX_MOVES_PER_DAY, DEFAULT_MAX_MOVES_PER_DAY
                ),
            ): vol.Coerce(int),
            vol.Required(
                CONF_CLOSE_EVENING,
                default=defaults.get(CONF_CLOSE_EVENING, DEFAULT_CLOSE_EVENING),
            ): bool,
            vol.Required(
                CONF_OPEN_MORNING,
                default=defaults.get(CONF_OPEN_MORNING, DEFAULT_OPEN_MORNING),
            ): bool,
            vol.Required(
                CONF_CLOSE_RAIN,
                default=defaults.get(CONF_CLOSE_RAIN, DEFAULT_CLOSE_RAIN),
            ): bool,
        }
    )


class HaiShutterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = CONFIG_VERSION

    def __init__(self) -> None:
        self._hub: dict[str, Any] = {}
        self._covers: dict[str, dict[str, Any]] = {}
        self._queue: list[str] = []
        self._names: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        available = _available_covers(self.hass)
        if not available:
            return self.async_abort(reason="no_covers")

        if user_input is not None:
            selected = user_input.pop(CONF_COVERS, [])
            self._hub = {k: v for k, v in user_input.items() if v not in ("", None)}
            self._names = available
            self._queue = list(selected)
            if not self._queue:
                return self.async_abort(reason="no_covers_selected")
            return await self.async_step_cover()

        schema = vol.Schema(
            {
                vol.Required(CONF_COVERS): cv_multi_select(available),
            }
        ).extend(_hub_schema({}).schema)

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self._queue[0]
        if user_input is not None:
            self._covers[current] = user_input
            self._queue.pop(0)
            if self._queue:
                return await self.async_step_cover()
            data = dict(self._hub)
            data[CONF_COVERS] = self._covers
            return self.async_create_entry(title="HAI Shutter Manager", data=data)

        return self.async_show_form(
            step_id="cover",
            data_schema=_cover_schema({}),
            description_placeholders={"cover": self._names.get(current, current)},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return HaiShutterOptionsFlow(entry)


class HaiShutterOptionsFlow(OptionsFlow):
    """Manage hub settings and the set of managed covers."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._queue: list[str] = []
        self._new_covers: dict[str, dict[str, Any]] = {}
        self._selected: list[str] = []
        self._names: dict[str, str] = {}
        self._pending_options: dict[str, Any] = {}

    def _existing_covers(self) -> dict[str, dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for cover_id, cfg in self._entry.data.get(CONF_COVERS, {}).items():
            merged[cover_id] = dict(cfg)
        for cover_id, cfg in self._entry.options.get(CONF_COVERS, {}).items():
            merged.setdefault(cover_id, {}).update(cfg)
        return merged

    def _hub_defaults(self) -> dict[str, Any]:
        defaults = dict(self._entry.data)
        defaults.update(
            {k: v for k, v in self._entry.options.items() if k != CONF_COVERS}
        )
        return defaults

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        available = _available_covers(self.hass)
        existing = self._existing_covers()
        self._names = available

        if user_input is not None:
            selected = user_input.pop(CONF_COVERS, [])
            self._selected = list(selected)
            hub_opts = {k: v for k, v in user_input.items() if v not in ("", None)}

            added = [c for c in selected if c not in existing]
            self._queue = list(added)

            # Start with hub options; covers are rebuilt below.
            self._pending_options = hub_opts
            if self._queue:
                return await self.async_step_cover()
            return self._finalize(existing)

        options_for_select = {**available, **{c: c for c in existing}}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_COVERS, default=list(existing)
                ): cv_multi_select(options_for_select),
            }
        ).extend(_hub_schema(self._hub_defaults()).schema)

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self._queue[0]
        if user_input is not None:
            self._new_covers[current] = user_input
            self._queue.pop(0)
            if self._queue:
                return await self.async_step_cover()
            return self._finalize(self._existing_covers())

        return self.async_show_form(
            step_id="cover",
            data_schema=_cover_schema({}),
            description_placeholders={"cover": self._names.get(current, current)},
        )

    def _finalize(self, existing: dict[str, dict[str, Any]]) -> ConfigFlowResult:
        kept = {
            cover_id: cfg
            for cover_id, cfg in existing.items()
            if cover_id in self._selected
        }
        kept.update(self._new_covers)

        options = dict(self._pending_options)
        options[CONF_COVERS] = kept
        return self.async_create_entry(title="", data=options)


def cv_multi_select(options: dict[str, str]):
    """Wrap a multi-select selector for entity ids."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=value, label=label)
                for value, label in options.items()
            ],
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )
