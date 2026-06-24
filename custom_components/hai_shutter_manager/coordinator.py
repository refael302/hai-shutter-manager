"""DataUpdateCoordinator and motor-protection orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from astral import Observer

from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_LAST_REASON,
    COMMAND_SUPPRESS_SECONDS,
    CONF_ACTION_DELAY,
    CONF_CLOSE_EVENING,
    CONF_CLOSE_RAIN,
    CONF_COVERS,
    CONF_DESIRED_TEMP,
    CONF_DIRECTION,
    CONF_EAVE_LENGTH,
    CONF_ENABLED,
    CONF_FOV,
    CONF_MAX_MOVES_PER_DAY,
    CONF_NOTIFY_LEVELS,
    CONF_OPEN_MORNING,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_RAIN_SENSOR,
    CONF_TELEGRAM_BOT_TOKEN,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_NOTIFY_SERVICE,
    CONF_TEMP_SENSOR,
    CONF_TEST_IS_DAY,
    CONF_TEST_IS_RAINING,
    CONF_TEST_MODE,
    CONF_TEST_OUTDOOR_TEMP,
    CONF_TEST_ROOM_TEMP,
    CONF_TEST_SEASON,
    CONF_TEST_SUN_AZIMUTH,
    CONF_TEST_SUN_ELEVATION,
    CONF_TEST_USE_SUN_OVERRIDE,
    CONF_WINDOW_HEIGHT,
    DEFAULT_ACTION_DELAY,
    DEFAULT_CLOSE_EVENING,
    DEFAULT_CLOSE_RAIN,
    DEFAULT_DESIRED_TEMP,
    DEFAULT_EAVE_LENGTH,
    DEFAULT_ENABLED,
    DEFAULT_FOV,
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
    MAX_LOG_ENTRIES,
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    RAIN_CONFIRM_DELAY,
    RAIN_HEAVY_THRESHOLD_MM,
    SEASON_WINTER,
    TARGET_CLOSED,
    TARGET_OPEN,
    UPDATE_INTERVAL,
)
from .engine import decide_target
from .location import resolve_location
from .notify import TelegramNotifier
from .open_meteo import OpenMeteoClient, OpenMeteoSnapshot
from .season import current_season
from .sun_calc import evaluate_window, evaluate_window_from_sun, forecast_window_hits
from .test_mode import format_test_action_log, format_test_skip_log

_LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _hub_float(hub: dict[str, Any], key: str, default: float) -> float:
    return _safe_float(hub.get(key), default)


COVER_DEFAULTS: dict[str, Any] = {
    CONF_DIRECTION: "S",
    CONF_EAVE_LENGTH: DEFAULT_EAVE_LENGTH,
    CONF_WINDOW_HEIGHT: DEFAULT_WINDOW_HEIGHT,
    CONF_DESIRED_TEMP: DEFAULT_DESIRED_TEMP,
    CONF_ACTION_DELAY: DEFAULT_ACTION_DELAY,
    CONF_FOV: DEFAULT_FOV,
    CONF_ENABLED: DEFAULT_ENABLED,
    CONF_CLOSE_EVENING: DEFAULT_CLOSE_EVENING,
    CONF_OPEN_MORNING: DEFAULT_OPEN_MORNING,
    CONF_CLOSE_RAIN: DEFAULT_CLOSE_RAIN,
    CONF_MAX_MOVES_PER_DAY: DEFAULT_MAX_MOVES_PER_DAY,
    CONF_TEMP_SENSOR: None,
}


class ShutterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Runs the decision engine and protects the motors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self._latitude = hass.config.latitude
        self._longitude = hass.config.longitude
        self.observer = Observer(
            latitude=self._latitude, longitude=self._longitude
        )
        self.notifier = TelegramNotifier(hass)
        self._open_meteo = OpenMeteoClient(hass)
        self._open_meteo_data: OpenMeteoSnapshot | None = None

        self._hub: dict[str, Any] = {}
        self._covers: dict[str, dict[str, Any]] = {}
        self._runtime: dict[str, dict[str, Any]] = {}
        self._log: list[dict[str, Any]] = []

        # Computed each update cycle.
        self.season: str = SEASON_WINTER
        self.is_day: bool = True
        self.is_raining: bool = False
        self.is_raining_raw: bool = False
        self.rain_intensity_mm: float | None = None
        self.rain_forecast_soon: bool = False
        self._rain_since: datetime | None = None

        self._unsub_state: Any = None

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Initial setup after entry creation."""
        self.reload_config()

    def reload_config(self) -> None:
        """(Re)read config from the config entry data + options."""
        try:
            self._reload_config_impl()
        except Exception:
            _LOGGER.exception("Failed to reload HAI Shutter Manager config")

    def _reload_config_impl(self) -> None:
        data = self.entry.data
        options = self.entry.options

        self._hub = {
            CONF_TELEGRAM_CHAT_ID: data.get(CONF_TELEGRAM_CHAT_ID),
            CONF_TELEGRAM_BOT_TOKEN: data.get(CONF_TELEGRAM_BOT_TOKEN),
            CONF_TELEGRAM_NOTIFY_SERVICE: data.get(CONF_TELEGRAM_NOTIFY_SERVICE),
            CONF_RAIN_SENSOR: data.get(CONF_RAIN_SENSOR) or None,
            CONF_OUTDOOR_TEMP_SENSOR: data.get(CONF_OUTDOOR_TEMP_SENSOR) or None,
            CONF_NOTIFY_LEVELS: data.get(
                CONF_NOTIFY_LEVELS, [PRIORITY_NORMAL, PRIORITY_EMERGENCY]
            ),
            CONF_TEST_MODE: data.get(CONF_TEST_MODE, DEFAULT_TEST_MODE),
            CONF_TEST_IS_DAY: data.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY),
            CONF_TEST_IS_RAINING: data.get(
                CONF_TEST_IS_RAINING, DEFAULT_TEST_IS_RAINING
            ),
            CONF_TEST_SEASON: data.get(CONF_TEST_SEASON, DEFAULT_TEST_SEASON),
            CONF_TEST_OUTDOOR_TEMP: data.get(CONF_TEST_OUTDOOR_TEMP),
            CONF_TEST_SUN_AZIMUTH: data.get(
                CONF_TEST_SUN_AZIMUTH, DEFAULT_TEST_SUN_AZIMUTH
            ),
            CONF_TEST_SUN_ELEVATION: data.get(
                CONF_TEST_SUN_ELEVATION, DEFAULT_TEST_SUN_ELEVATION
            ),
            CONF_TEST_USE_SUN_OVERRIDE: data.get(
                CONF_TEST_USE_SUN_OVERRIDE, DEFAULT_TEST_USE_SUN_OVERRIDE
            ),
        }
        # Hub-level overrides from options (skip empty values).
        for key in list(self._hub):
            if key not in options:
                continue
            value = options[key]
            if value in (None, ""):
                continue
            self._hub[key] = value

        self._latitude, self._longitude = resolve_location(
            self.hass, data, options
        )
        try:
            self.observer = Observer(
                latitude=self._latitude, longitude=self._longitude
            )
        except Exception:
            _LOGGER.warning("Invalid coordinates; using Home Assistant home location")
            self._latitude = self.hass.config.latitude
            self._longitude = self.hass.config.longitude
            self.observer = Observer(
                latitude=self._latitude, longitude=self._longitude
            )

        data_covers = _coerce_dict(data.get(CONF_COVERS))
        option_covers = _coerce_dict(options.get(CONF_COVERS))

        merged: dict[str, dict[str, Any]] = {}
        for cover_id in set(data_covers) | set(option_covers):
            cfg = dict(COVER_DEFAULTS)
            cover_data = data_covers.get(cover_id)
            cover_opts = option_covers.get(cover_id)
            if isinstance(cover_data, dict):
                cfg.update(cover_data)
            if isinstance(cover_opts, dict):
                cfg.update(cover_opts)
            merged[cover_id] = cfg
        self._covers = merged

        for cover_id in self._covers:
            self._runtime.setdefault(cover_id, {})

        self.notifier.configure(
            chat_id=self._hub[CONF_TELEGRAM_CHAT_ID],
            bot_token=self._hub[CONF_TELEGRAM_BOT_TOKEN],
            notify_service=self._hub[CONF_TELEGRAM_NOTIFY_SERVICE],
            levels=(
                self._hub[CONF_NOTIFY_LEVELS]
                if isinstance(self._hub.get(CONF_NOTIFY_LEVELS), list)
                else [PRIORITY_NORMAL, PRIORITY_EMERGENCY]
            ),
            test_mode=bool(self._hub.get(CONF_TEST_MODE)),
        )

        self._init_virtual_states()
        self._resubscribe()

    def _init_virtual_states(self) -> None:
        """Ensure each cover has a virtual state when test mode is active."""
        if not self.test_mode:
            return
        for cover_id in self._covers:
            runtime = self._runtime.setdefault(cover_id, {})
            if "virtual_state" not in runtime:
                state = self.hass.states.get(cover_id)
                if state and state.state in (TARGET_OPEN, TARGET_CLOSED):
                    runtime["virtual_state"] = state.state
                else:
                    runtime["virtual_state"] = TARGET_CLOSED

    def _resubscribe(self) -> None:
        """Track cover and rain-sensor state changes."""
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        if self.test_mode:
            return
        tracked: list[str] = list(self._covers)
        rain_sensor = self._hub.get(CONF_RAIN_SENSOR)
        if rain_sensor:
            tracked.append(rain_sensor)
        if tracked:
            self._unsub_state = async_track_state_change_event(
                self.hass, tracked, self._handle_entity_state_change
            )

    async def async_shutdown(self) -> None:
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None

    # ------------------------------------------------------------------
    # Public accessors used by entities / services
    # ------------------------------------------------------------------
    @property
    def covers(self) -> dict[str, dict[str, Any]]:
        return self._covers

    @property
    def hub(self) -> dict[str, Any]:
        return self._hub

    @property
    def test_mode(self) -> bool:
        return bool(self._hub.get(CONF_TEST_MODE))

    def has_cover(self, cover_id: str) -> bool:
        return cover_id in self._covers

    def cover_config(self, cover_id: str) -> dict[str, Any]:
        return self._covers.get(cover_id, {})

    async def async_set_cover_option(
        self, cover_id: str, key: str, value: Any
    ) -> None:
        """Persist a per-cover option change to the config entry options."""
        options = dict(self.entry.options)
        covers = {k: dict(v) for k, v in options.get(CONF_COVERS, {}).items()}
        covers.setdefault(cover_id, {})[key] = value
        options[CONF_COVERS] = covers
        if cover_id in self._covers:
            self._covers[cover_id][key] = value
        else:
            cfg = dict(COVER_DEFAULTS)
            cfg.update(covers.get(cover_id, {}))
            self._covers[cover_id] = cfg
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def async_set_hub_option(self, key: str, value: Any) -> None:
        """Persist a hub-level option (test overrides, etc.)."""
        options = dict(self.entry.options)
        options[key] = value
        self._hub[key] = value
        if key == CONF_TEST_MODE:
            self.notifier.configure(
                chat_id=self._hub[CONF_TELEGRAM_CHAT_ID],
                bot_token=self._hub[CONF_TELEGRAM_BOT_TOKEN],
                notify_service=self._hub[CONF_TELEGRAM_NOTIFY_SERVICE],
                levels=self._hub[CONF_NOTIFY_LEVELS],
                test_mode=bool(value),
            )
            self._init_virtual_states()
            self._resubscribe()
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def async_set_virtual_state(self, cover_id: str, state: str) -> None:
        """Manually set a cover's virtual state in test mode."""
        if not self.test_mode or cover_id not in self._covers:
            return
        if state not in (TARGET_OPEN, TARGET_CLOSED):
            return
        runtime = self._runtime.setdefault(cover_id, {})
        runtime["virtual_state"] = state
        await self.async_request_refresh()

    def _cover_state(self, cover_id: str) -> str | None:
        """Return effective state (virtual in test mode, real otherwise)."""
        if self.test_mode:
            runtime = self._runtime.get(cover_id, {})
            return runtime.get("virtual_state")
        state = self.hass.states.get(cover_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state.state

    def _friendly_name(self, cover_id: str) -> str:
        state = self.hass.states.get(cover_id)
        if state is not None:
            return state.attributes.get("friendly_name", cover_id)
        return cover_id

    def _test_overrides_snapshot(self) -> dict[str, Any]:
        return {
            "outdoor_temp": self._hub.get(CONF_TEST_OUTDOOR_TEMP),
            "sun_azimuth": self._hub.get(CONF_TEST_SUN_AZIMUTH),
            "sun_elevation": self._hub.get(CONF_TEST_SUN_ELEVATION),
        }

    # ------------------------------------------------------------------
    # Environment helpers used by the engine
    # ------------------------------------------------------------------
    def _window_azimuth(self, cfg: dict[str, Any]) -> float:
        return float(DIRECTIONS.get(cfg.get(CONF_DIRECTION, "S"), 180))

    def sun_hits_now(self, cover_id: str, cfg: dict[str, Any]) -> bool:
        eave = _safe_float(cfg.get(CONF_EAVE_LENGTH), DEFAULT_EAVE_LENGTH)
        height = _safe_float(cfg.get(CONF_WINDOW_HEIGHT), DEFAULT_WINDOW_HEIGHT)
        fov = _safe_float(cfg.get(CONF_FOV), DEFAULT_FOV)
        window_az = self._window_azimuth(cfg)
        runtime = self._runtime.setdefault(cover_id, {})

        if self.test_mode and self._hub.get(CONF_TEST_USE_SUN_OVERRIDE):
            result = evaluate_window_from_sun(
                _hub_float(self._hub, CONF_TEST_SUN_AZIMUTH, DEFAULT_TEST_SUN_AZIMUTH),
                _hub_float(
                    self._hub, CONF_TEST_SUN_ELEVATION, DEFAULT_TEST_SUN_ELEVATION
                ),
                window_az,
                eave,
                height,
                fov,
            )
        else:
            result = evaluate_window(
                self.observer,
                dt_util.utcnow(),
                window_az,
                eave,
                height,
                fov,
            )
        runtime["sun_azimuth"] = result.azimuth
        runtime["sun_elevation"] = result.elevation
        runtime["sunlit_fraction"] = result.sunlit_fraction
        return result.hits

    def sun_hits_soon(self, cover_id: str, cfg: dict[str, Any]) -> bool:
        if self.test_mode and self._hub.get(CONF_TEST_USE_SUN_OVERRIDE):
            return self.sun_hits_now(cover_id, cfg)
        hits = forecast_window_hits(
            self.observer,
            dt_util.utcnow(),
            self._window_azimuth(cfg),
            _safe_float(cfg.get(CONF_EAVE_LENGTH), DEFAULT_EAVE_LENGTH),
            _safe_float(cfg.get(CONF_WINDOW_HEIGHT), DEFAULT_WINDOW_HEIGHT),
            _safe_float(cfg.get(CONF_FOV), DEFAULT_FOV),
            hours_ahead=3,
        )
        return bool(hits)

    def _read_float_state(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _area_for_entity(self, entity_id: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        entity = ent_reg.async_get(entity_id)
        if entity is None:
            return None
        if entity.area_id:
            return entity.area_id
        if entity.device_id:
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get(entity.device_id)
            if device and device.area_id:
                return device.area_id
        return None

    def _temp_sensor_in_area(self, area_id: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        for entity in ent_reg.entities.values():
            if entity.domain != "sensor":
                continue
            entity_area = entity.area_id
            if not entity_area and entity.device_id:
                dev_reg = dr.async_get(self.hass)
                device = dev_reg.async_get(entity.device_id)
                entity_area = device.area_id if device else None
            if entity_area != area_id:
                continue
            state = self.hass.states.get(entity.entity_id)
            if state is None:
                continue
            if state.attributes.get("device_class") == "temperature":
                return entity.entity_id
        return None

    def get_area_temp(self, cover_id: str, cfg: dict[str, Any]) -> float | None:
        """Best-effort room temperature for a cover's area."""
        if self.test_mode:
            test_room = cfg.get(CONF_TEST_ROOM_TEMP)
            if test_room is not None:
                try:
                    return float(test_room)
                except (ValueError, TypeError):
                    pass
            hub_temp = self._hub.get(CONF_TEST_OUTDOOR_TEMP)
            if hub_temp is not None:
                try:
                    return float(hub_temp)
                except (ValueError, TypeError):
                    pass

        explicit = cfg.get(CONF_TEMP_SENSOR)
        value = self._read_float_state(explicit)
        if value is not None:
            return value

        area_id = self._area_for_entity(cover_id)
        if area_id:
            sensor = self._temp_sensor_in_area(area_id)
            value = self._read_float_state(sensor)
            if value is not None:
                return value

        value = self._read_float_state(self._hub.get(CONF_OUTDOOR_TEMP_SENSOR))
        if value is not None:
            return value

        return self._open_meteo_temperature()

    def current_outdoor_temp(self) -> float | None:
        """Effective outdoor temperature (test override, sensor, or forecast)."""
        if self.test_mode:
            override = self._hub.get(CONF_TEST_OUTDOOR_TEMP)
            if override is not None:
                try:
                    return float(override)
                except (ValueError, TypeError):
                    pass
            return None
        value = self._read_float_state(self._hub.get(CONF_OUTDOOR_TEMP_SENSOR))
        if value is not None:
            return value
        return self._open_meteo_temperature()

    def _open_meteo_temperature(self) -> float | None:
        if self._open_meteo_data is None:
            return None
        return self._open_meteo_data.temperature_c

    async def _refresh_open_meteo(self) -> None:
        """Fetch the latest Open-Meteo forecast for the configured location."""
        if self.test_mode:
            return
        self._open_meteo_data = await self._open_meteo.async_fetch(
            self._latitude,
            self._longitude,
        )

    def _compute_is_day(self) -> bool:
        if self.test_mode:
            return bool(self._hub.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY))
        sun = self.hass.states.get("sun.sun")
        if sun is not None:
            return sun.state == "above_horizon"
        result = evaluate_window(self.observer, dt_util.utcnow(), 180, 0, 1, 360)
        return result.elevation > 0

    def _read_rain_input(self) -> tuple[bool, float | None, bool]:
        """Return whether rain is detected, optional intensity (mm), forecast flag."""
        if self.test_mode:
            raining = bool(
                self._hub.get(CONF_TEST_IS_RAINING, DEFAULT_TEST_IS_RAINING)
            )
            return raining, None, False

        rain_sensor = self._hub.get(CONF_RAIN_SENSOR)
        if rain_sensor:
            state = self.hass.states.get(rain_sensor)
            if state is not None and state.state not in (
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ):
                if state.state in ("on", "wet", "rain", "raining", "true"):
                    return True, None, False
                value = self._read_float_state(rain_sensor)
                if value is not None:
                    return value > 0, value, False
                return False, None, False

        data = self._open_meteo_data
        if data is None:
            return False, None, False

        if data.rain_now:
            mm = data.current_precipitation_mm
            return True, mm, False

        if data.rain_forecast:
            return True, data.forecast_max_precipitation_mm, True

        return False, None, False

    def _update_rain_tracking(self, now: datetime) -> None:
        """Track continuous rain; set is_raining when close-on-rain should fire."""
        active, mm, from_forecast = self._read_rain_input()
        self.is_raining_raw = active
        self.rain_forecast_soon = from_forecast
        self.rain_intensity_mm = mm if active else None

        if not active:
            self._rain_since = None
            self.is_raining = False
            return

        if self._rain_since is None:
            self._rain_since = now

        if self.test_mode:
            self.is_raining = True
            return

        if from_forecast:
            self.is_raining = True
            return

        if mm is not None and mm > RAIN_HEAVY_THRESHOLD_MM:
            self.is_raining = True
            return

        self.is_raining = (now - self._rain_since) >= RAIN_CONFIRM_DELAY

    # ------------------------------------------------------------------
    # Manual-override detection
    # ------------------------------------------------------------------
    @callback
    def _handle_entity_state_change(self, event: Event) -> None:
        entity_id = event.data[ATTR_ENTITY_ID]
        if entity_id in self._covers:
            self._handle_cover_state_change(event)
            return

        rain_sensor = self._hub.get(CONF_RAIN_SENSOR)
        if entity_id == rain_sensor:
            self._update_rain_tracking(dt_util.utcnow())
            self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _handle_cover_state_change(self, event: Event) -> None:
        entity_id = event.data[ATTR_ENTITY_ID]
        new_state = event.data.get("new_state")
        if new_state is None or entity_id not in self._covers:
            return
        if new_state.state not in (TARGET_OPEN, TARGET_CLOSED):
            return

        runtime = self._runtime.setdefault(entity_id, {})
        now = dt_util.utcnow()
        commanded = runtime.get("commanded_state")
        suppress_until = runtime.get("suppress_until")

        if (
            suppress_until is not None
            and now < suppress_until
            and commanded == new_state.state
        ):
            # This change was caused by us.
            return

        cfg = self._covers[entity_id]
        delay = timedelta(
            hours=_safe_float(cfg.get(CONF_ACTION_DELAY), DEFAULT_ACTION_DELAY)
        )
        runtime["manual_until"] = now + delay
        self._add_log(
            entity_id,
            f"Manual/third-party move detected ({new_state.state}); "
            f"pausing automation for {delay}",
        )
        self.hass.async_create_task(
            self.notifier.async_send(
                f"{entity_id}: manual override detected, pausing automation.",
                PRIORITY_NORMAL,
            )
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self._async_update_data_impl()
        except Exception:
            _LOGGER.exception("Coordinator refresh failed")
            if self.data is not None:
                return self.data
            return self.build_fallback_data()

    def build_fallback_data(self) -> dict[str, Any]:
        """Minimal coordinator payload used when a refresh cannot run."""
        return {
            "test_mode": self.test_mode,
            "season": str(self._hub.get(CONF_TEST_SEASON, DEFAULT_TEST_SEASON)),
            "is_day": bool(self._hub.get(CONF_TEST_IS_DAY, DEFAULT_TEST_IS_DAY)),
            "is_raining": False,
            "is_raining_raw": False,
            "rain_forecast_soon": False,
            "open_meteo_available": False,
            "outdoor_temp": None,
            "covers": {},
            "log": [
                {
                    "time": dt_util.utcnow().isoformat(),
                    "cover": "",
                    "message": "Coordinator fallback — check Home Assistant logs",
                    "reason": "",
                }
            ],
        }

    async def _async_update_data_impl(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        local_now = dt_util.now()

        await self._refresh_open_meteo()

        if self.test_mode and self._hub.get(CONF_TEST_SEASON):
            self.season = str(self._hub[CONF_TEST_SEASON])
        else:
            self.season = current_season(local_now, self._latitude)
        self.is_day = self._compute_is_day()
        self._update_rain_tracking(now)

        covers_snapshot: dict[str, Any] = {}
        for cover_id, cfg in list(self._covers.items()):
            try:
                covers_snapshot[cover_id] = await self._evaluate_cover(
                    cover_id, dict(cfg), now
                )
            except Exception:
                _LOGGER.exception("Failed to evaluate cover %s", cover_id)
                covers_snapshot[cover_id] = {
                    "config": cfg,
                    "state": None,
                    "virtual_state": None,
                    "available": False,
                    "target": None,
                    "reason": "evaluation error",
                    "manual_until": None,
                    "last_action": None,
                    "sun_hit": False,
                    "moves_today": 0,
                    "test_mode": self.test_mode,
                    "room_temp": None,
                }

        return {
            "test_mode": self.test_mode,
            "season": self.season,
            "is_day": self.is_day,
            "is_raining": self.is_raining,
            "is_raining_raw": self.is_raining_raw,
            "rain_forecast_soon": self.rain_forecast_soon,
            "open_meteo_available": self._open_meteo_data is not None,
            "outdoor_temp": self.current_outdoor_temp(),
            "covers": covers_snapshot,
            "log": list(self._log),
        }

    async def _evaluate_cover(
        self, cover_id: str, cfg: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        runtime = self._runtime.setdefault(cover_id, {})
        runtime.pop("last_skip_log", None)
        effective_state = self._cover_state(cover_id)

        snapshot: dict[str, Any] = {
            "config": cfg,
            "state": effective_state,
            "virtual_state": runtime.get("virtual_state") if self.test_mode else None,
            "available": False,
            "target": None,
            "reason": "",
            "manual_until": _iso(runtime.get("manual_until")),
            "last_action": _iso(runtime.get("last_action_time")),
            "sun_hit": False,
            "moves_today": runtime.get("moves_today", 0),
            "test_mode": self.test_mode,
            "room_temp": self.get_area_temp(cover_id, cfg),
        }

        if self.test_mode:
            runtime.pop("unavailable_since", None)
            snapshot["available"] = True
            if effective_state is None:
                runtime["virtual_state"] = TARGET_CLOSED
                effective_state = TARGET_CLOSED
                snapshot["state"] = effective_state
        else:
            state = self.hass.states.get(cover_id)
            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                await self._notify_unavailable(cover_id, runtime, now)
                return snapshot
            runtime.pop("unavailable_since", None)
            snapshot["available"] = True
            snapshot["state"] = state.state
            effective_state = state.state

        if not cfg.get(CONF_ENABLED, True):
            snapshot["reason"] = "automation disabled"
            if self.test_mode:
                await self._maybe_test_skip_log(
                    cover_id, cfg, snapshot, effective_state, "automation disabled"
                )
            return snapshot

        # Reset the daily move counter at midnight.
        self._maybe_reset_daily(runtime, now)

        # Respect manual override window.
        manual_until = runtime.get("manual_until")
        if manual_until is not None and now < manual_until:
            snapshot["reason"] = "manual override active"
            return snapshot

        # Debounce: respect the per-cover action delay.
        delay = timedelta(
            hours=_safe_float(cfg.get(CONF_ACTION_DELAY), DEFAULT_ACTION_DELAY)
        )
        last_action = runtime.get("last_action_time")
        if last_action is not None and now - last_action < delay:
            snapshot["reason"] = "within action delay"
            self._refresh_sun_snapshot(cover_id, cfg, snapshot, runtime)
            return snapshot

        decision = decide_target(self, cover_id, cfg)
        self._refresh_sun_snapshot(cover_id, cfg, snapshot, runtime)
        snapshot["target"] = decision.target
        snapshot["reason"] = decision.reason

        if decision.target is None:
            if self.test_mode:
                await self._maybe_test_skip_log(
                    cover_id, cfg, snapshot, effective_state, decision.reason
                )
            return snapshot

        # Idempotency: do not command if already in the desired state.
        if effective_state == decision.target:
            if self.test_mode:
                await self._maybe_test_skip_log(
                    cover_id,
                    cfg,
                    snapshot,
                    effective_state,
                    f"already {decision.target}",
                )
            return snapshot

        # Daily move limit guard (motor protection).
        max_moves = _safe_int(
            cfg.get(CONF_MAX_MOVES_PER_DAY), DEFAULT_MAX_MOVES_PER_DAY
        )
        if runtime.get("moves_today", 0) >= max_moves:
            snapshot["reason"] = f"daily move limit reached ({max_moves})"
            if self.test_mode:
                await self._maybe_test_skip_log(
                    cover_id, cfg, snapshot, effective_state, snapshot["reason"]
                )
            return snapshot

        await self._command_cover(
            cover_id, decision.target, decision.reason, runtime, now, cfg, snapshot
        )
        snapshot["last_action"] = _iso(runtime.get("last_action_time"))
        snapshot["moves_today"] = runtime.get("moves_today", 0)
        return snapshot

    def _refresh_sun_snapshot(
        self,
        cover_id: str,
        cfg: dict[str, Any],
        snapshot: dict[str, Any],
        runtime: dict[str, Any],
    ) -> None:
        try:
            snapshot["sun_hit"] = self.sun_hits_now(cover_id, cfg)
        except Exception:
            _LOGGER.exception("Sun calculation failed for %s", cover_id)
            snapshot["sun_hit"] = False
        snapshot["sunlit_fraction"] = runtime.get("sunlit_fraction", 0.0)

    def _maybe_reset_daily(self, runtime: dict[str, Any], now: datetime) -> None:
        day = now.date()
        if runtime.get("moves_day") != day:
            runtime["moves_day"] = day
            runtime["moves_today"] = 0

    async def _command_cover(
        self,
        cover_id: str,
        target: str,
        reason: str,
        runtime: dict[str, Any],
        now: datetime,
        cfg: dict[str, Any] | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> None:
        previous = self._cover_state(cover_id)

        if self.test_mode:
            runtime["virtual_state"] = target
            runtime["commanded_state"] = target
            runtime["last_action_time"] = now
            runtime["moves_today"] = runtime.get("moves_today", 0) + 1
            runtime[ATTR_LAST_REASON] = reason
            self._add_log(cover_id, f"[TEST virtual] {target} ({reason})", reason)

            message = format_test_action_log(
                cover_id,
                self._friendly_name(cover_id),
                action=target,
                reason=reason,
                previous_state=previous,
                virtual_state=target,
                season=self.season,
                is_day=self.is_day,
                is_raining=self.is_raining,
                sun_hit=bool(snapshot and snapshot.get("sun_hit")),
                sunlit_fraction=float(
                    runtime.get("sunlit_fraction", 0.0)
                ),
                sun_azimuth=runtime.get("sun_azimuth"),
                sun_elevation=runtime.get("sun_elevation"),
                room_temp=self.get_area_temp(cover_id, cfg or {}),
                cfg=cfg or self.cover_config(cover_id),
                moves_today=runtime.get("moves_today", 0),
                test_overrides=self._test_overrides_snapshot(),
            )
            await self.notifier.async_send_test_log(message)
            return

        service = SERVICE_OPEN_COVER if target == TARGET_OPEN else SERVICE_CLOSE_COVER
        try:
            await self.hass.services.async_call(
                COVER_DOMAIN,
                service,
                {ATTR_ENTITY_ID: cover_id},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - surface as emergency
            self._add_log(cover_id, f"Command failed ({target}): {err}", reason)
            await self.notifier.async_send(
                f"{cover_id}: failed to {target} ({err})", PRIORITY_EMERGENCY
            )
            return

        runtime["commanded_state"] = target
        runtime["suppress_until"] = now + timedelta(seconds=COMMAND_SUPPRESS_SECONDS)
        runtime["last_action_time"] = now
        runtime["moves_today"] = runtime.get("moves_today", 0) + 1
        runtime[ATTR_LAST_REASON] = reason

        self._add_log(cover_id, f"{target} ({reason})", reason)
        await self.notifier.async_send(
            f"{cover_id}: {target} - {reason}", PRIORITY_NORMAL
        )

    async def _notify_unavailable(
        self, cover_id: str, runtime: dict[str, Any], now: datetime
    ) -> None:
        if runtime.get("unavailable_since") is not None:
            return
        runtime["unavailable_since"] = now
        self._add_log(cover_id, "Device unavailable")
        await self.notifier.async_send(
            f"{cover_id}: device unavailable / disconnected.", PRIORITY_EMERGENCY
        )

    def _add_log(self, cover_id: str, message: str, reason: str = "") -> None:
        entry = {
            "time": dt_util.utcnow().isoformat(),
            "cover": cover_id,
            "message": message,
            "reason": reason,
        }
        self._log.insert(0, entry)
        del self._log[MAX_LOG_ENTRIES:]

    async def _maybe_test_skip_log(
        self,
        cover_id: str,
        cfg: dict[str, Any],
        snapshot: dict[str, Any],
        effective_state: str | None,
        reason: str,
    ) -> None:
        """Send a detailed skip log in test mode (once per reason per cycle)."""
        if not self.test_mode:
            return
        runtime = self._runtime.get(cover_id, {})
        skip_key = f"skip:{reason}:{snapshot.get('target')}"
        if runtime.get("last_skip_log") == skip_key:
            return
        runtime["last_skip_log"] = skip_key
        message = format_test_skip_log(
            cover_id,
            self._friendly_name(cover_id),
            reason=reason,
            virtual_state=effective_state,
            season=self.season,
            is_day=self.is_day,
            is_raining=self.is_raining,
            sun_hit=bool(snapshot.get("sun_hit")),
            target=snapshot.get("target"),
        )
        try:
            await self.notifier.async_send_test_log(message)
        except Exception:
            _LOGGER.exception("Failed to send test skip log for %s", cover_id)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
