"""Constants for the Zelia VP integration."""

from __future__ import annotations

DOMAIN = "zelia_vp"
MANUFACTURER = "CCEI"
MODEL = "Zelia VP"

# String platform names (resolved by HA config entries); no homeassistant import.
PLATFORMS: list[str] = [
    "binary_sensor",
    "number",
    "select",
    "sensor",
    "switch",
]

CONF_DEVICE_ID = "device_id"
DEFAULT_PORT = 1883
DEFAULT_NAME = "Zelia VP"

# Seconds without MQTT traffic before entities become unavailable.
DEFAULT_AVAILABILITY_TIMEOUT = 600

# Production state (prod_on) mapping.
PROD_STATE_MAP: dict[int, str] = {
    0: "stopped",
    1: "requested",
    2: "running",
}

# Electrolysis mode (mode_ely).
MODE_ELY_OPTIONS: dict[str, int] = {
    "off": 0,
    "programmed": 1,
    "auto": 2,
    "regulated": 3,
}
MODE_ELY_REVERSE: dict[int, str] = {v: k for k, v in MODE_ELY_OPTIONS.items()}

# Writable keys allowed for desired publishes (whitelist).
WRITABLE_KEYS = frozenset(
    {
        "mode_ely",
        "mode_choc",
        "power_ely",
        "ely_duration_theo",
        "choc_duration",
        "temp_min_off",
        "consigne_orp",
        "winter_mode",
    }
)
