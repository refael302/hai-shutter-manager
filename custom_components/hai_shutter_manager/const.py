"""Constants for the HAI Shutter Manager integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "hai_shutter_manager"

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number", "select"]

CONFIG_VERSION = 1

# How often the decision engine runs.
UPDATE_INTERVAL = timedelta(minutes=5)

# ---------------------------------------------------------------------------
# Hub-level config keys (stored in entry.data / entry.options)
# ---------------------------------------------------------------------------
CONF_COVERS = "covers"
CONF_TELEGRAM_CHAT_ID = "telegram_chat_id"
CONF_TELEGRAM_BOT_TOKEN = "telegram_bot_token"
CONF_TELEGRAM_NOTIFY_SERVICE = "telegram_notify_service"
CONF_RAIN_SENSOR = "rain_sensor"
CONF_OUTDOOR_TEMP_SENSOR = "outdoor_temp_sensor"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_NOTIFY_LEVELS = "notify_levels"
CONF_HEMISPHERE = "hemisphere"
CONF_TEST_MODE = "test_mode"
CONF_TEST_IS_DAY = "test_is_day"
CONF_TEST_IS_RAINING = "test_is_raining"
CONF_TEST_SEASON = "test_season"
CONF_TEST_OUTDOOR_TEMP = "test_outdoor_temp"
CONF_TEST_SUN_AZIMUTH = "test_sun_azimuth"
CONF_TEST_SUN_ELEVATION = "test_sun_elevation"
CONF_TEST_USE_SUN_OVERRIDE = "test_use_sun_override"
CONF_TEST_ROOM_TEMP = "test_room_temp"

# ---------------------------------------------------------------------------
# Per-cover config keys
# ---------------------------------------------------------------------------
CONF_DIRECTION = "direction"
CONF_EAVE_LENGTH = "eave_length"
CONF_WINDOW_HEIGHT = "window_height"
CONF_DESIRED_TEMP = "desired_temp"
CONF_ACTION_DELAY = "action_delay_hours"
CONF_ENABLED = "enabled"
CONF_TEMP_SENSOR = "temp_sensor"
CONF_FOV = "fov"
CONF_CLOSE_EVENING = "close_evening"
CONF_OPEN_MORNING = "open_morning"
CONF_CLOSE_RAIN = "close_rain"
CONF_MAX_MOVES_PER_DAY = "max_moves_per_day"

# Seasons
SEASON_WINTER = "winter"
SEASON_SUMMER = "summer"
SEASON_TRANSITION = "transition"
SEASON_OPTIONS = [SEASON_WINTER, SEASON_SUMMER, SEASON_TRANSITION]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_EAVE_LENGTH = 15  # cm
DEFAULT_WINDOW_HEIGHT = 150  # cm
DEFAULT_ACTION_DELAY = 3  # hours
DEFAULT_DESIRED_TEMP = 22.0  # Celsius
DEFAULT_FOV = 180  # total horizontal field of view (degrees)
DEFAULT_MAX_MOVES_PER_DAY = 6
DEFAULT_HEMISPHERE = "north"
DEFAULT_ENABLED = True
DEFAULT_CLOSE_EVENING = True
DEFAULT_OPEN_MORNING = True
DEFAULT_CLOSE_RAIN = True
DEFAULT_TEST_MODE = False
DEFAULT_TEST_IS_DAY = True
DEFAULT_TEST_IS_RAINING = False
DEFAULT_TEST_SEASON = SEASON_TRANSITION
DEFAULT_TEST_SUN_AZIMUTH = 90.0
DEFAULT_TEST_SUN_ELEVATION = 35.0
DEFAULT_TEST_USE_SUN_OVERRIDE = True

# Window of time after we issue a command in which a matching state change is
# considered "ours" and not a manual override.
COMMAND_SUPPRESS_SECONDS = 45

# Anti-spam settings for notifications.
NOTIFY_DEDUP_SECONDS = 600  # do not resend an identical message within this window
NOTIFY_RATE_LIMIT = 10  # max messages
NOTIFY_RATE_WINDOW = timedelta(minutes=10)

MAX_LOG_ENTRIES = 50

# ---------------------------------------------------------------------------
# Directions in 45-degree increments -> azimuth (degrees, clockwise from N)
# ---------------------------------------------------------------------------
DIRECTIONS: dict[str, int] = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}

# Notification priorities
PRIORITY_NORMAL = "normal"
PRIORITY_EMERGENCY = "emergency"
NOTIFY_LEVEL_OPTIONS = [PRIORITY_NORMAL, PRIORITY_EMERGENCY]

# Cover logical targets
TARGET_OPEN = "open"
TARGET_CLOSED = "closed"

# Services
SERVICE_SET_COVER_OPTION = "set_cover_option"
SERVICE_SET_TEST_OVERRIDE = "set_test_override"
SERVICE_SET_VIRTUAL_STATE = "set_virtual_state"

# Used to mark the source of a state change in our runtime bookkeeping.
ATTR_LAST_REASON = "last_reason"
