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

# Grace period (seconds) after MQTT disconnection before entities go unavailable.
# Allows brief network hiccups without flapping. TomTuT reference uses 180s.
# Note: availability is now based on MQTT session, not message age.
DEFAULT_DISCONNECT_GRACE_SECONDS = 180

# Legacy option key (pre-2026.10.5); migrated to disconnect_grace_seconds.
# Kept for migration code reference only.
LEGACY_AVAILABILITY_TIMEOUT = "availability_timeout"

# New option key for disconnect grace period.
CONF_DISCONNECT_GRACE = "disconnect_grace_seconds"

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

# MQTT u32_r/error is a bitmask. Vigipool app code E{n} = bit n.
# Field-confirmed 2026-08-16: 16384 (1<<14) + app notification "Code E14 —
# Taux de sel trop élevé" (high current / too much salt). Other bits decode
# as E{n} without a label until independently confirmed.
ERROR_NONE = "none"
ERROR_BIT_HIGH_SALT = 14
ERROR_MASK_HIGH_SALT = 1 << ERROR_BIT_HIGH_SALT  # 16384

# bit → machine label for confirmed codes only (exposed as attributes).
ERROR_BIT_LABELS: dict[int, str] = {
    ERROR_BIT_HIGH_SALT: "high_salt",
}

# Bus event fired when a bit of u32_r/state turns on or off.
# See helpers.StatusEdgeTracker for the no-spurious-edge rules.
EVENT_ZELIA_STATUS = "zelia_vp_status"

# MQTT u32_r/state is a bitmask. Vigipool app code S{n} = bit n.
# Field-confirmed 2026-10-24 (HA diagnostics raw_store, same device):
#   state = 2151677952 (0x80400000) = bit 22 + bit 31
#   value_temp = 130 (13.0 °C) < temp_min_off_ely = 150 (15.0 °C)
#   prod_on = 0
#   app text: "Température minimale de l'eau atteinte. Arrêt du traitement
#   - Code S22"
# Bit 31 is also set in the 2026-07-22 capture (2147483648 = 0x80000000,
# production running). Its meaning is not confirmed — rendered as unknown.
# Confirmed message texts live only in translations (entity.sensor.zelia_status).
STATUS_BIT_MIN_WATER_TEMP = 22

# Diagnostic leaves. Ranges match the MQTT type in tests/fixtures (sanity
# checks). These topics are exposed read-only; water_hardness and temp_adjust
# are device-writable but their scales are unconfirmed, so we never publish.
SERVER_ON_RANGE = (0, 1)
MODEL_ID_RANGE = (0, 255)
HW_VERS_RANGE = (0, 255)
WATER_HARDNESS_RANGE = (0, 255)
TEMP_ADJUST_RANGE = (-128, 127)  # i8_w
SERIAL_MAX_LENGTH = 32  # s33_r: 32 hex chars observed (type width includes NUL)
