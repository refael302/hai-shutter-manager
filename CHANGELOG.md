# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] - 2026-06-22

### Fixed

- Correct `DeviceInfo` import path so the integration loads on current Home
  Assistant versions (`homeassistant.helpers.device_registry`).

## [0.4.2] - 2026-06-22

### Changed

- **Hemisphere** config option removed — season is derived automatically from
  latitude.
- **Location** config option added (optional). Defaults to the Home Assistant
  home location for sun calculations, Open-Meteo forecast, and season detection.
  Leave unchanged to keep following the HA home coordinates.

## [0.4.1] - 2026-06-22

### Changed

- Config/options flow now exposes only the **Test mode** toggle. The manual test
  overrides (day/night, rain, season, outdoor temp, sun angles) are controlled
  exclusively through the dashboard entities while test mode is active.

## [0.4.0] - 2026-06-21

### Added

- **Open-Meteo forecast client**: fetches rain and temperature directly from the
  Open-Meteo API using the Home Assistant home location. No weather integration
  or API key required.
- Rain forecast within the next 3 hours closes shutters proactively (no 5-minute
  confirmation delay).
- Rain binary sensor exposes `rain_forecast_soon` and `open_meteo_available`
  attributes.

### Removed

- **Weather entity** config option — replaced by built-in Open-Meteo support.

## [0.3.0] - 2026-06-21

### Added

- **Test mode switch** (`switch.*_test_mode`): toggle the virtual test sandbox at
  runtime directly from the integration/dashboard, without opening the options
  flow. While on, the engine simulates decisions on virtual shutters and logs to
  Telegram; while off, it controls the real covers as usual.

## [0.2.2] - 2026-06-21

### Added

- Rain close delay: shutters close on rain only after 5 minutes of continuous
  detection (> 0 mm), or immediately when intensity exceeds 8 mm.
- Rain binary sensor shows live detection; `confirmed_for_close` attribute
  indicates when close-on-rain would trigger.
- Rain and weather entity state changes trigger an immediate coordinator refresh
  (accurate delay timing without waiting for the 5-minute poll).

## [0.2.1] - 2026-06-21

### Added

- Integration icon (`icon.png`) for Home Assistant and HACS UI.
- Default entity icon `mdi:window-shutter-open` for hub entities.

## [0.2.0] - 2026-06-21

### Added

- **Test mode** in integration settings: simulate shutter actions on virtual
  states without moving real covers.
- Manual test overrides for season, day/night, rain, outdoor temperature, and
  sun azimuth/elevation (plus per-cover test room temperature).
- Live test override entities (switches, numbers, select) available while test
  mode is active.
- Detailed Telegram logs for every virtual action and for skipped decisions in
  test mode.
- Services `set_test_override` and `set_virtual_state`.

## [0.1.0] - 2026-06-21

### Added

- Initial release of HAI Shutter Manager.
- Config flow that scans existing `cover` entities and lets the user select which
  ones to manage, with a per-cover direction picker in 45-degree increments.
- Hub-level settings: Telegram chat id / bot token / notify service, optional rain
  sensor, optional outdoor temperature sensor, weather entity, notification levels.
- Per-cover settings: direction (azimuth), eave/awning length (default 15 cm),
  window height, desired temperature, action delay (default 3 hours), max moves per
  day, evening-close / morning-open / close-on-rain toggles, enable/disable.
- Decision engine using sun azimuth + elevation and eave geometry to determine
  whether direct sun reaches each window, with day-ahead forecasting.
- Season logic (winter maximize sun / summer minimize sun / transition comfort).
- Weather forecast fallback for rain and outdoor temperature.
- Motor-protection guards: per-cover debounce, idempotent commands, max moves per
  day, manual-override detection (including third-party commands).
- Entities: log sensor, season sensor, day/night binary sensor, rain binary sensor,
  per-cover state binary sensor, per-cover automation switch, per-cover number
  controls (action delay, eave length, desired temperature).
- Telegram notifications split by priority (normal / emergency) with
  de-duplication and rate limiting.
- Custom Lovelace table card (`hai-shutter-table-card`) with one row per cover and
  inline editing of settings.
