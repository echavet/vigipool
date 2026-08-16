"""Pure helpers (no Home Assistant imports) for Zelia VP."""

from __future__ import annotations

import re
from typing import Any

from .const import (
    ERROR_BIT_HIGH_SALT,
    ERROR_BIT_LABELS,
    ERROR_NONE,
    MODE_ELY_REVERSE,
    PROD_STATE_MAP,
)

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


def _error_int(raw: float | int | None) -> int | None:
    """Coerce the u32 error register to an unsigned 32-bit int."""
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value & 0xFFFFFFFF


def error_bits_from_raw(raw: float | int | None) -> list[int] | None:
    """Return set bit indices (0–31) of the u32 error register."""
    value = _error_int(raw)
    if value is None:
        return None
    return [bit for bit in range(32) if value & (1 << bit)]


def error_e_codes_from_raw(raw: float | int | None) -> list[str] | None:
    """Map set bits to Vigipool app codes (bit n → En)."""
    bits = error_bits_from_raw(raw)
    if bits is None:
        return None
    return [f"E{bit}" for bit in bits]


def error_e_codes_state_from_raw(raw: float | int | None) -> str | None:
    """Human-readable error state: none, E14, or E2+E14."""
    codes = error_e_codes_from_raw(raw)
    if codes is None:
        return None
    if not codes:
        return ERROR_NONE
    return "+".join(codes)


def error_attributes_from_raw(raw: float | int | None) -> dict[str, Any] | None:
    """Extra attributes for the raw and decoded error sensors."""
    value = _error_int(raw)
    if value is None:
        return None
    bits = [bit for bit in range(32) if value & (1 << bit)]
    labels = [ERROR_BIT_LABELS[bit] for bit in bits if bit in ERROR_BIT_LABELS]
    return {
        "error_hex": f"0x{value:X}",
        "error_bits": bits,
        "e_codes": [f"E{bit}" for bit in bits],
        "labels": labels,
        "high_salt": ERROR_BIT_HIGH_SALT in bits,
    }


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
