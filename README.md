# HAI Shutter Manager

A custom [Home Assistant](https://www.home-assistant.io/) integration that
intelligently controls your roller shutters / blinds (`cover` entities) based on
the **sun position (azimuth + elevation)**, **season**, **weather** and your
**comfort preferences** - while protecting the shutter motors from excessive
wear.

> Status: early development (`0.1.0`). Expect breaking changes.

## Features

- **Automatic discovery** of all `cover` entities in your home; tick a checkbox to
  manage a shutter.
- **Per-shutter direction** in 45-degree increments (N, NE, E, SE, S, SW, W, NW).
- **Sun-aware control**: computes the sun azimuth and elevation (now and for the
  day ahead) and, together with the **awning/eave length**, decides whether direct
  sunlight actually reaches each window. A morning sun in the east only affects
  east-facing windows; a west window is handled in the afternoon, etc.
- **Season strategy**:
  - Winter: maximize incoming sun.
  - Summer: minimize incoming sun.
  - Transition: keep the room at your desired temperature (using the temperature
    sensor associated with the shutter's area in Home Assistant).
- **Weather forecast fallback** when no rain / outdoor temperature sensor is set.
- **Telegram notifications** split into `normal` and `emergency` priorities, with
  de-duplication and rate-limiting to prevent spam.
- **Manual-override aware**: if you (or any third party) move a shutter manually,
  the integration backs off for the configured delay.
- **Motor protection**: per-shutter debounce (default 3 hours), idempotent
  commands, and a daily move limit.
- **Custom Lovelace table card** to see and edit every setting, one row per
  shutter.

## Installation (HACS)

1. In HACS, add this repository as a custom repository (category: *Integration*).
2. Install **HAI Shutter Manager** and restart Home Assistant.
3. Go to *Settings -> Devices & Services -> Add Integration* and search for
   **HAI Shutter Manager**.

### Manual installation

Copy `custom_components/hai_shutter_manager` into your Home Assistant
`config/custom_components/` directory and restart.

## The Lovelace card

After installation, add the card resource (URL):

```
/hacsfiles/hai_shutter_manager/hai-shutter-table-card.js
```

(or the path where you copied `frontend/hai-shutter-table-card.js`), then add to a
dashboard:

```yaml
type: custom:hai-shutter-table-card
```

## Entities

| Entity | Type | Description |
| --- | --- | --- |
| Action log | `sensor` | Last action + recent history |
| Season | `sensor` | `winter` / `summer` / `transition` |
| Day/Night | `binary_sensor` | On during daytime |
| Rain | `binary_sensor` | On when raining |
| `<cover>` state | `binary_sensor` | On when the shutter is open |
| `<cover>` automation | `switch` | Pause/resume automation for this shutter |
| `<cover>` action delay | `number` | Debounce in hours (default 3) |
| `<cover>` eave length | `number` | Awning length in cm (default 15) |
| `<cover>` desired temp | `number` | Target room temperature |

## Versioning workflow

This project follows [Semantic Versioning](https://semver.org/). On every version
bump we update `custom_components/hai_shutter_manager/manifest.json` and
`CHANGELOG.md`, then commit, tag (`vX.Y.Z`) and push:

```bash
git add -A
git commit -m "Release vX.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

## License

[MIT](LICENSE)
