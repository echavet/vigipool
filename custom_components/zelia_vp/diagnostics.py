"""Diagnostics support for Zelia VP."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ZeliaCoordinator

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "device_id": coordinator.device_id,
        "mqtt_connected": coordinator.mqtt.connected,
        "device_available": coordinator.device_available,
        "last_message_age": coordinator.last_message_age,
        "data": coordinator.data,
        "raw": coordinator._raw,  # noqa: SLF001 — diagnostics only
    }
