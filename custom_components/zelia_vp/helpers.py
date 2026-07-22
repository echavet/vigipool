"""Pure helpers (no Home Assistant imports) for Zelia VP."""

from __future__ import annotations

import re

from .const import MODE_ELY_REVERSE, PROD_STATE_MAP

DEVICE_ID_RE_SUFFIX = re.compile(r"^[0-9A-F]{12}$")

# Device error sentinels for temperature-like u16 values.
TEMP_SENTINEL_MIN = 65530


def build_topic(
    device_id: str, mqtt_type: str, name: str, qualifier: str, direction: str
) -> str:
    """Build a full MQTT topic for a Zelia device."""
    return f"{device_id}/{mqtt_type}/{name}/{qualifier}/{direction}"


def parse_topic(topic: str) -> tuple[str, str, str, str, str] | None:
    """
    Parse device_id / type / name / qualifier / direction.

    Returns None if the topic shape is unexpected.
    """
    parts = topic.split("/")
    if len(parts) < 5:
        return None
    return parts[0], parts[1], parts[2], parts[3], parts[4]


def parse_numeric(payload: str) -> float | None:
    """Parse a numeric MQTT payload; return None on failure."""
    try:
        text = payload.strip()
        if text == "":
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def apply_read_scale(raw: float | None, scale: float) -> float | None:
    """Apply a read scale factor to a raw numeric value."""
    if raw is None:
        return None
    if scale == 1.0:
        return raw
    return raw * scale


def is_temp_sentinel(raw: float | None) -> bool:
    """Return True if the raw temperature value is a device error sentinel."""
    return raw is not None and raw >= TEMP_SENTINEL_MIN


def format_payload(value: float | int) -> str:
    """Format a numeric value as a Zelia MQTT payload string."""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def prod_state_from_raw(raw: float | None) -> str | None:
    """Map prod_on raw value to enum option; unknown → None."""
    if raw is None:
        return None
    try:
        return PROD_STATE_MAP.get(int(raw))
    except (TypeError, ValueError):
        return None


def mode_ely_from_raw(raw: float | None) -> str | None:
    """Map mode_ely raw value to select option."""
    if raw is None:
        return None
    try:
        return MODE_ELY_REVERSE.get(int(raw))
    except (TypeError, ValueError):
        return None


def firmware_from_raw(raw: float | None) -> str | None:
    """Map sw_vers raw value to a firmware string."""
    if raw is None:
        return None
    try:
        return str(int(raw))
    except (TypeError, ValueError):
        return None


def normalize_device_id(value: str) -> str:
    """Normalize a Zelia device id to zelix_XXXXXXXXXXXX (uppercase hex).

    Raises ValueError if the value cannot be normalized.
    """
    cleaned = value.strip()
    if cleaned.lower().startswith("zelix_"):
        suffix = cleaned.split("_", 1)[1]
    else:
        suffix = cleaned
    suffix = suffix.replace(":", "").replace("-", "").upper()
    if not DEVICE_ID_RE_SUFFIX.fullmatch(suffix):
        raise ValueError("invalid_device_id")
    return f"zelix_{suffix}"


def mac_from_device_id(device_id: str) -> str | None:
    """Derive a MAC address from zelix_XXXXXXXXXXXX if possible."""
    if "_" not in device_id:
        return None
    suffix = device_id.split("_", 1)[1]
    if len(suffix) != 12:
        return None
    parts = [suffix[i : i + 2] for i in range(0, 12, 2)]
    return ":".join(parts).lower()
