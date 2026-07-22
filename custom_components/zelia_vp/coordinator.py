"""DataUpdateCoordinator for Zelia VP (push-first, raw MQTT store)."""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_AVAILABILITY_TIMEOUT, MODE_ELY_OPTIONS
from .helpers import build_topic, format_payload, parse_numeric, parse_topic
from .models import WRITABLE_DESCRIPTIONS, ZeliaMqttMixin
from .mqtt_client import ZeliaMqttClient

_LOGGER = logging.getLogger(__name__)

# Coordinator data: mqtt_name → raw float (or str if non-numeric).
ZeliaData = dict[str, float | str]


class ZeliaCoordinator(DataUpdateCoordinator[ZeliaData]):
    """Holds raw MQTT values keyed by mqtt_name; entities apply descriptions."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
        port: int,
        device_id: str,
        availability_timeout: int = DEFAULT_AVAILABILITY_TIMEOUT,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Zelia VP {device_id}",
            update_interval=None,
        )
        self.entry = entry
        self.host = host
        self.port = port
        self.device_id = device_id
        self.availability_timeout = availability_timeout
        self._last_message_at: float | None = None
        self.mqtt = ZeliaMqttClient(host, port, device_id, self._handle_message)
        self.data: ZeliaData = {}

    async def async_start(self) -> None:
        """Start MQTT client background task."""
        await self.mqtt.start()

    async def async_shutdown(self) -> None:
        """Stop MQTT client."""
        await self.mqtt.stop()

    @property
    def last_message_age(self) -> float | None:
        """Seconds since last MQTT message, or None if never."""
        if self._last_message_at is None:
            return None
        return time.monotonic() - self._last_message_at

    @property
    def device_available(self) -> bool:
        """Available iff we have received data within the timeout window."""
        if self._last_message_at is None:
            return False
        age = self.last_message_age
        return age is not None and age < self.availability_timeout

    def get_raw(self, mqtt_name: str) -> float | str | None:
        """Return the raw stored value for an MQTT variable name."""
        return self.data.get(mqtt_name)

    def get_raw_number(self, mqtt_name: str) -> float | None:
        """Return raw value as float, or None."""
        value = self.data.get(mqtt_name)
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return parse_numeric(str(value))

    async def async_publish_desired(self, key: str, value: float | int) -> None:
        """Publish a desired value for a writable description key."""
        desc = WRITABLE_DESCRIPTIONS.get(key)
        if desc is None:
            raise ValueError(f"Key {key} is not writable")
        await self._publish_desc(desc, value)

    async def async_set_mode_ely(self, option: str) -> None:
        """Set electrolysis mode and clear shock (choc first, then mode)."""
        if option not in MODE_ELY_OPTIONS:
            raise ValueError(f"Unknown mode: {option}")
        # Clear shock before mode so we never leave shock stuck if mode fails.
        errors: list[Exception] = []
        for key, val in (("mode_choc", 0), ("mode_ely", MODE_ELY_OPTIONS[option])):
            try:
                await self.async_publish_desired(key, val)
            except Exception as err:  # noqa: BLE001
                errors.append(err)
                _LOGGER.error("Failed to publish %s=%s: %s", key, val, err)
        if errors:
            raise errors[-1]

    async def _publish_desc(self, desc: ZeliaMqttMixin, value: float | int) -> None:
        payload_num = float(value) * desc.write_scale
        topic = build_topic(
            self.device_id,
            desc.mqtt_type,
            desc.mqtt_name,
            desc.qualifier,
            "desired",
        )
        await self.mqtt.publish(topic, format_payload(payload_num))
        _LOGGER.debug("Desired %s -> %s (%s)", desc.key, payload_num, topic)

    @callback
    def _handle_message(self, topic: str, payload: str) -> None:
        """Parse a reported topic into the raw store (same event loop)."""
        parsed = parse_topic(topic)
        if parsed is None:
            return
        device_id, _mqtt_type, mqtt_name, _qualifier, direction = parsed
        if device_id != self.device_id or direction != "reported":
            return

        self._last_message_at = time.monotonic()
        raw_num = parse_numeric(payload)
        new_data = dict(self.data)
        # Single source of truth: mqtt_name → raw (entities apply description).
        new_data[mqtt_name] = raw_num if raw_num is not None else payload
        self.async_set_updated_data(new_data)

    async def _async_update_data(self) -> ZeliaData:
        """No polling; return current raw store."""
        return self.data
