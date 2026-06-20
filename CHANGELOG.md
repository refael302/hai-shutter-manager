# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
