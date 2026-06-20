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
    CONF_HEMISPHERE,
    CONF_MAX_MOVES_PER_DAY,
    CONF_NOTIFY_LEVELS,
    CONF_OPEN_MORNING,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_RAIN_SENSOR,
    CONF_TELEGRAM_BOT_TOKEN,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_NOTIFY_SERVICE,
    CONF_TEMP_SENSOR,
    CONF_WEATHER_ENTITY,
    CONF_WINDOW_HEIGHT,
    DEFAULT_ACTION_DELAY,
    DEFAULT_CLOSE_EVENING,
    DEFAULT_CLOSE_RAIN,
    DEFAULT_DESIRED_TEMP,
    DEFAULT_EAVE_LENGTH,
    DEFAULT_ENABLED,
    DEFAULT_FOV,
    DEFAULT_HEMISPHERE,
    DEFAULT_MAX_MOVES_PER_DAY,
    DEFAULT_OPEN_MORNING,
    DEFAULT_WINDOW_HEIGHT,
    DIRECTIONS,
    DOMAIN,
    MAX_LOG_ENTRIES,
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    SEASON_WINTER,
    TARGET_CLOSED,
    TARGET_OPEN,
    UPDATE_INTERVAL,
)
from .engine import decide_target
from .notify import TelegramNotifier
from .season import current_season
from .sun_calc import evaluate_window, forecast_window_hits

_LOGGER = logging.getLogger(__name__)

_RAINY_CONDITIONS = {
    "rainy",
    "pouring",
    "lightning-rainy",
    "snowy-rainy",
    "hail",
}

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
        self.observer = Observer(
            latitude=hass.config.latitude, longitude=hass.config.longitude
        )
        self.notifier = TelegramNotifier(hass)

        self._hub: dict[str, Any] = {}
        self._covers: dict[str, dict[str, Any]] = {}
        self._runtime: dict[str, dict[str, Any]] = {}
        self._log: list[dict[str, Any]] = []

        # Computed each update cycle.
        self.season: str = SEASON_WINTER
        self.is_day: bool = True
        self.is_raining: bool = False

        self._unsub_state: Any = None

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Initial setup after entry creation."""
        self.reload_config()

    def reload_config(self) -> None:
        """(Re)read config from the config entry data + options."""
        data = self.entry.data
        options = self.entry.options

        self._hub = {
            CONF_TELEGRAM_CHAT_ID: data.get(CONF_TELEGRAM_CHAT_ID),
            CONF_TELEGRAM_BOT_TOKEN: data.get(CONF_TELEGRAM_BOT_TOKEN),
            CONF_TELEGRAM_NOTIFY_SERVICE: data.get(CONF_TELEGRAM_NOTIFY_SERVICE),
            CONF_RAIN_SENSOR: data.get(CONF_RAIN_SENSOR),
            CONF_OUTDOOR_TEMP_SENSOR: data.get(CONF_OUTDOOR_TEMP_SENSOR),
            CONF_WEATHER_ENTITY: data.get(CONF_WEATHER_ENTITY),
            CONF_NOTIFY_LEVELS: data.get(
                CONF_NOTIFY_LEVELS, [PRIORITY_NORMAL, PRIORITY_EMERGENCY]
            ),
            CONF_HEMISPHERE: data.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE),
        }
        # Hub-level overrides from options.
        for key in list(self._hub):
            if key in options:
                self._hub[key] = options[key]

        data_covers: dict[str, Any] = data.get(CONF_COVERS, {})
        option_covers: dict[str, Any] = options.get(CONF_COVERS, {})

        merged: dict[str, dict[str, Any]] = {}
        for cover_id in set(data_covers) | set(option_covers):
            cfg = dict(COVER_DEFAULTS)
            cfg.update(data_covers.get(cover_id, {}))
            cfg.update(option_covers.get(cover_id, {}))
            merged[cover_id] = cfg
        self._covers = merged

        for cover_id in self._covers:
            self._runtime.setdefault(cover_id, {})

        self.notifier.configure(
            chat_id=self._hub[CONF_TELEGRAM_CHAT_ID],
            bot_token=self._hub[CONF_TELEGRAM_BOT_TOKEN],
            notify_service=self._hub[CONF_TELEGRAM_NOTIFY_SERVICE],
            levels=self._hub[CONF_NOTIFY_LEVELS],
        )

        self._resubscribe()

    def _resubscribe(self) -> None:
        """Track state changes of the managed covers for manual-override detection."""
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        if self._covers:
            self._unsub_state = async_track_state_change_event(
                self.hass, list(self._covers), self._handle_cover_state_change
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
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    # ------------------------------------------------------------------
    # Environment helpers used by the engine
    # ------------------------------------------------------------------
    def _window_azimuth(self, cfg: dict[str, Any]) -> float:
        return float(DIRECTIONS.get(cfg.get(CONF_DIRECTION, "S"), 180))

    def sun_hits_now(self, cover_id: str, cfg: dict[str, Any]) -> bool:
        result = evaluate_window(
            self.observer,
            dt_util.utcnow(),
            self._window_azimuth(cfg),
            float(cfg.get(CONF_EAVE_LENGTH, DEFAULT_EAVE_LENGTH)),
            float(cfg.get(CONF_WINDOW_HEIGHT, DEFAULT_WINDOW_HEIGHT)),
            float(cfg.get(CONF_FOV, DEFAULT_FOV)),
        )
        self._runtime[cover_id]["sunlit_fraction"] = result.sunlit_fraction
        return result.hits

    def sun_hits_soon(self, cover_id: str, cfg: dict[str, Any]) -> bool:
        hits = forecast_window_hits(
            self.observer,
            dt_util.utcnow(),
            self._window_azimuth(cfg),
            float(cfg.get(CONF_EAVE_LENGTH, DEFAULT_EAVE_LENGTH)),
            float(cfg.get(CONF_WINDOW_HEIGHT, DEFAULT_WINDOW_HEIGHT)),
            float(cfg.get(CONF_FOV, DEFAULT_FOV)),
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

        return self._weather_temperature()

    def _weather_temperature(self) -> float | None:
        weather = self._hub.get(CONF_WEATHER_ENTITY)
        if not weather:
            return None
        state = self.hass.states.get(weather)
        if state is None:
            return None
        temp = state.attributes.get("temperature")
        try:
            return float(temp) if temp is not None else None
        except (ValueError, TypeError):
            return None

    def _compute_is_day(self) -> bool:
        sun = self.hass.states.get("sun.sun")
        if sun is not None:
            return sun.state == "above_horizon"
        result = evaluate_window(self.observer, dt_util.utcnow(), 180, 0, 1, 360)
        return result.elevation > 0

    def _compute_is_raining(self) -> bool:
        rain_sensor = self._hub.get(CONF_RAIN_SENSOR)
        if rain_sensor:
            state = self.hass.states.get(rain_sensor)
            if state is not None and state.state not in (
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ):
                if state.state in ("on", "wet", "rain", "raining", "true"):
                    return True
                value = self._read_float_state(rain_sensor)
                if value is not None:
                    return value > 0
                return False

        weather = self._hub.get(CONF_WEATHER_ENTITY)
        if weather:
            state = self.hass.states.get(weather)
            if state is not None and state.state in _RAINY_CONDITIONS:
                return True
        return False

    # ------------------------------------------------------------------
    # Manual-override detection
    # ------------------------------------------------------------------
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
        delay = timedelta(hours=float(cfg.get(CONF_ACTION_DELAY, DEFAULT_ACTION_DELAY)))
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
        now = dt_util.utcnow()
        local_now = dt_util.now()

        self.season = current_season(local_now, self._hub.get(CONF_HEMISPHERE))
        self.is_day = self._compute_is_day()
        self.is_raining = self._compute_is_raining()

        covers_snapshot: dict[str, Any] = {}
        for cover_id, cfg in self._covers.items():
            covers_snapshot[cover_id] = await self._evaluate_cover(
                cover_id, cfg, now
            )

        return {
            "season": self.season,
            "is_day": self.is_day,
            "is_raining": self.is_raining,
            "covers": covers_snapshot,
            "log": list(self._log),
        }

    async def _evaluate_cover(
        self, cover_id: str, cfg: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        runtime = self._runtime.setdefault(cover_id, {})
        state = self.hass.states.get(cover_id)

        snapshot: dict[str, Any] = {
            "config": cfg,
            "state": None,
            "available": False,
            "target": None,
            "reason": "",
            "manual_until": _iso(runtime.get("manual_until")),
            "last_action": _iso(runtime.get("last_action_time")),
            "sun_hit": False,
            "moves_today": runtime.get("moves_today", 0),
        }

        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            await self._notify_unavailable(cover_id, runtime, now)
            return snapshot

        # Device became available again; reset the unavailable flag.
        runtime.pop("unavailable_since", None)
        snapshot["available"] = True
        snapshot["state"] = state.state

        if not cfg.get(CONF_ENABLED, True):
            snapshot["reason"] = "automation disabled"
            return snapshot

        # Reset the daily move counter at midnight.
        self._maybe_reset_daily(runtime, now)

        # Respect manual override window.
        manual_until = runtime.get("manual_until")
        if manual_until is not None and now < manual_until:
            snapshot["reason"] = "manual override active"
            return snapshot

        # Debounce: respect the per-cover action delay.
        delay = timedelta(hours=float(cfg.get(CONF_ACTION_DELAY, DEFAULT_ACTION_DELAY)))
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
            return snapshot

        # Idempotency: do not command if already in the desired state.
        if state.state == decision.target:
            return snapshot

        # Daily move limit guard (motor protection).
        max_moves = int(cfg.get(CONF_MAX_MOVES_PER_DAY, DEFAULT_MAX_MOVES_PER_DAY))
        if runtime.get("moves_today", 0) >= max_moves:
            snapshot["reason"] = f"daily move limit reached ({max_moves})"
            return snapshot

        await self._command_cover(cover_id, decision.target, decision.reason, runtime, now)
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
        snapshot["sun_hit"] = self.sun_hits_now(cover_id, cfg)
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
    ) -> None:
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


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
