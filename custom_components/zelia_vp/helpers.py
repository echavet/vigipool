"""Pure helpers (no Home Assistant imports) for Zelia VP."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .const import (
    ERROR_BIT_HIGH_SALT,
    ERROR_BIT_LABELS,
    ERROR_NONE,
    MODE_ELY_REVERSE,
    PROD_STATE_MAP,
    SERIAL_MAX_LENGTH,
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


def status_u32(raw: float | int | None) -> int | None:
    """Coerce a status register to an integer in ``0 .. 0xFFFFFFFF``.

    Non-integers, non-finite values, and out-of-range numbers are rejected.
    Unlike the error register, negatives are not reinterpreted as unsigned:
    a bogus payload must not light every S-code.
    """
    if raw is None or isinstance(raw, bool):
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    value = int(number)
    if value < 0 or value > 0xFFFFFFFF:
        return None
    return value


def bounded_int(raw: float | int | None, low: int, high: int) -> int | None:
    """Return ``raw`` as an int when it is an in-range integer, else None."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    value = int(number)
    if value < low or value > high:
        return None
    return value


_SERIAL_RE = re.compile(rf"^[0-9A-Fa-f]{{1,{SERIAL_MAX_LENGTH}}}$")


def serial_from_raw(raw: float | str | None) -> str | None:
    """Accept a hex serial string; reject numbers, blanks, and overlong values."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if _SERIAL_RE.fullmatch(text) is None:
        return None
    return text


_STATUS_CATALOG_CACHE: dict[str, dict[str, str]] = {}
_STATUS_CODE_KEY = re.compile(r"^s(\d+)$")


def normalize_status_language(language: str | None) -> str:
    """Map a Home Assistant language to the catalogs we ship (fr or en)."""
    if not language:
        return "en"
    primary = language.replace("_", "-").split("-", 1)[0].lower()
    if primary == "fr":
        return "fr"
    return "en"


def _read_status_catalog(path: Path) -> dict[str, str]:
    """Read ``entity.sensor.zelia_status.state`` from a translation file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    state = (
        data.get("entity", {})
        .get("sensor", {})
        .get("zelia_status", {})
        .get("state", {})
    )
    if not isinstance(state, dict):
        return {}
    catalog: dict[str, str] = {}
    for key, value in state.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            catalog[key] = value
    return catalog


def load_status_catalog(language: str | None) -> dict[str, str]:
    """Load confirmed S-code texts and the none/unknown templates.

    French falls back to English for any missing key. The message table is
    the translation file: a code is confirmed only when ``s{n}`` is present.
    """
    lang = normalize_status_language(language)
    cached = _STATUS_CATALOG_CACHE.get(lang)
    if cached is not None:
        return cached
    path = Path(__file__).parent / "translations" / f"{lang}.json"
    catalog = _read_status_catalog(path)
    if lang != "en":
        english = load_status_catalog("en")
        merged = dict(english)
        merged.update(catalog)
        catalog = merged
    _STATUS_CATALOG_CACHE[lang] = catalog
    return catalog


def status_confirmed_bits(catalog: dict[str, str]) -> dict[int, str]:
    """Map bit → confirmed message body. Unknown bits are absent."""
    found: dict[int, str] = {}
    for key, text in catalog.items():
        match = _STATUS_CODE_KEY.fullmatch(key)
        if match is None:
            continue
        bit = int(match.group(1))
        if 0 <= bit <= 31 and text.strip():
            found[bit] = text
    return found


def _render_unknown(catalog: dict[str, str], bit: int) -> str:
    template = catalog.get("unknown") or "S{code} (unknown)"
    try:
        return template.format(code=bit)
    except (IndexError, KeyError, ValueError):
        return f"S{bit} (unknown)"


def status_display_for_bit(bit: int, catalog: dict[str, str]) -> str:
    """One code as shown to the user: ``S22 : …`` or ``S{n} (inconnu)``."""
    body = status_confirmed_bits(catalog).get(bit)
    if body:
        return f"S{bit} : {body}"
    return _render_unknown(catalog, bit)


def _status_bits(value: int) -> list[int]:
    return [bit for bit in range(32) if value & (1 << bit)]


def _main_status_bit(bits: list[int], confirmed: dict[int, str]) -> int | None:
    """Headline bit: lowest confirmed code, else the lowest set bit.

    Confirmed text wins over a lower unknown bit so a known stop reason
    (S22) stays the headline when an unconfirmed bit is also set.
    """
    if not bits:
        return None
    confirmed_on = [bit for bit in bits if bit in confirmed]
    if confirmed_on:
        return confirmed_on[0]
    return bits[0]


def status_state_from_raw(
    raw: float | int | None, catalog: dict[str, str]
) -> str | None:
    """Headline state: ``aucun`` / ``none``, or the main code and its message."""
    value = status_u32(raw)
    if value is None:
        return None
    bits = _status_bits(value)
    if not bits:
        return catalog.get("none") or "none"
    main = _main_status_bit(bits, status_confirmed_bits(catalog))
    assert main is not None
    return status_display_for_bit(main, catalog)


def status_attributes_from_raw(
    raw: float | int | None, catalog: dict[str, str]
) -> dict[str, Any] | None:
    """Attributes kept in history: raw, hex, active codes, messages."""
    value = status_u32(raw)
    if value is None:
        return None
    bits = _status_bits(value)
    return {
        "raw": value,
        "hex": f"0x{value:X}",
        "s_codes": [f"S{bit}" for bit in bits],
        "messages": [status_display_for_bit(bit, catalog) for bit in bits],
    }


def status_edge_payloads(
    previous: int | None,
    current: int,
    catalog: dict[str, str],
    device_id: str,
) -> list[dict[str, Any]]:
    """One event payload per bit that flipped. No payload for the baseline."""
    if previous is None or previous == current:
        return []
    payloads: list[dict[str, Any]] = []
    for bit in range(32):
        mask = 1 << bit
        was = bool(previous & mask)
        now = bool(current & mask)
        if was == now:
            continue
        payloads.append(
            {
                "device_id": device_id,
                "code": f"S{bit}",
                "message": status_display_for_bit(bit, catalog),
                "active": now,
                "raw": current,
            }
        )
    return payloads


class StatusEdgeTracker:
    """Edge detector for the Zelia ``state`` bitmask.

    Choice (no spurious ``zelia_vp_status`` events):

    * The first valid sample in this process is a baseline only. Retained
      messages at startup, and the first sample after a config-entry reload,
      do not emit. Bits that are already on are visible on the sensor, not
      replayed as rising edges.
    * The baseline is not cleared when MQTT drops or entities go unavailable.
      A reconnect that replays the same retained value stays silent.
    * A later sample whose mask actually differs still emits one event per
      flipped bit (including a real change that happened during the outage).
    * Identical republications (the device repeats its last values) emit
      nothing, so the ``info`` and ``value`` copies of ``state`` do not
      double-fire when they carry the same integer.
    * Invalid payloads are ignored and do not move the baseline, so they
      cannot look like "every code turned off".
    """

    def __init__(self) -> None:
        self.raw: int | None = None

    def observe(
        self,
        raw: float | int | None,
        catalog: dict[str, str],
        device_id: str,
    ) -> list[dict[str, Any]]:
        """Record ``raw`` and return event payloads for real bit edges."""
        value = status_u32(raw)
        if value is None:
            return []
        previous = self.raw
        self.raw = value
        return status_edge_payloads(previous, value, catalog, device_id)


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
