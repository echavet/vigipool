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
    last_msg_time = coordinator.last_message_time
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "device_id": coordinator.device_id,
        "mqtt_connected": coordinator.mqtt.connected,
        "device_available": coordinator.device_available,
        "disconnect_grace_seconds": coordinator.disconnect_grace_seconds,
        "last_message_age": coordinator.last_message_age,
        "last_message_time": last_msg_time.isoformat() if last_msg_time else None,
        "raw_store": dict(coordinator.data),
    }
