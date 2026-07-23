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
# Field-confirmed on Zelia VP (~24 h observation, ~2 h alternation between 1 and 2):
#   0 = off (no production)
#   1 = producing (forward polarity)
#   2 = polarity reverse / electrode self-clean (still producing)
# Jeedom only documents 0/1; CDC "requested" for 1 was wrong.
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
