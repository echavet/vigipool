"""Constants for the Zelia VP integration."""

from __future__ import annotations

DOMAIN = "zelia_vp"
MANUFACTURER = "CCEI"
MODEL = "Zelia VP"

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

# Production state (prod_on).
# Evidence (live + Jeedom): 0 = off, 1 = producing.
# Value 2 also coincides with cell current/voltage (not "requested"); treated as
# reverse-polarity / self-clean phase (common on salt cells; not officially documented).
# Unknown codes → None (enum stays strict).
PROD_STATE_MAP: dict[int, str] = {
    0: "off",
    1: "on",
    2: "reverse",
}

# Electrolysis mode (mode_ely).
MODE_ELY_OPTIONS: dict[str, int] = {
    "off": 0,
    "programmed": 1,
    "auto": 2,
    "regulated": 3,
}
MODE_ELY_REVERSE: dict[int, str] = {v: k for k, v in MODE_ELY_OPTIONS.items()}
