"""DataUpdateCoordinator for Zelia VP (push-first, raw MQTT store)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_DISCONNECT_GRACE_SECONDS, MODE_ELY_OPTIONS
from .helpers import build_topic, format_payload, parse_numeric, parse_topic
from .models import WRITABLE_DESCRIPTIONS, ZeliaMqttMixin
from .mqtt_client import ZeliaMqttClient

_LOGGER = logging.getLogger(__name__)

AVAILABILITY_CHECK_INTERVAL = timedelta(seconds=10)

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
        disconnect_grace_seconds: int = DEFAULT_DISCONNECT_GRACE_SECONDS,
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
        self.disconnect_grace_seconds = disconnect_grace_seconds
        self._last_message_at: float | None = None
        self._last_message_utc: datetime | None = None
        self._disconnected_at: float | None = None
        self._last_availability_state: tuple[bool, bool] | None = None
        self._cancel_availability_timer: Any = None
        self.mqtt = ZeliaMqttClient(
            host, port, device_id, self._handle_message, self._handle_connection_change
        )
        self.data: ZeliaData = {}

    async def async_start(self) -> None:
        """Start MQTT client background task and availability timer."""
        await self.mqtt.start()
        self._cancel_availability_timer = async_track_time_interval(
            self.hass, self._check_availability, AVAILABILITY_CHECK_INTERVAL
        )

    async def async_shutdown(self) -> None:
        """Stop MQTT client and cancel availability timer."""
        if self._cancel_availability_timer is not None:
            self._cancel_availability_timer()
            self._cancel_availability_timer = None
        await self.mqtt.stop()

    @property
    def last_message_age(self) -> float | None:
        """Seconds since last MQTT message, or None if never."""
        if self._last_message_at is None:
            return None
        return time.monotonic() - self._last_message_at

    @property
    def last_message_time(self) -> datetime | None:
        """UTC datetime of the last MQTT message, or None if never."""
        return self._last_message_utc

    @property
    def device_available(self) -> bool:
        """Available if MQTT connected OR within grace period after disconnect.

        This ensures entities stay available during the normal long silence
        periods of the Zelia device (~915s pump on, ~3610s pump off) and only
        become unavailable after a genuine communication loss.
        """
        if self.mqtt.connected:
            return True
        if self._disconnected_at is None:
            return False
        grace_elapsed = time.monotonic() - self._disconnected_at
        return grace_elapsed < self.disconnect_grace_seconds

    @property
    def mqtt_connected(self) -> bool:
        """Return True if the MQTT client is connected to the broker."""
        return self.mqtt.connected

    @callback
    def _check_availability(self, _now: Any = None) -> None:
        """Periodic check to update entity states when availability changes.

        Tracks (device_available, mqtt_connected) so both read-only and
        writable entities get updated when either flag changes.
        """
        current_state = (self.device_available, self.mqtt_connected)
        if self._last_availability_state != current_state:
            self._last_availability_state = current_state
            self.async_set_updated_data(self.data)

    @callback
    def _handle_connection_change(self, connected: bool) -> None:
        """Called by MQTT client on connect/disconnect transitions."""
        if connected:
            self._disconnected_at = None
            _LOGGER.info("MQTT connected to %s:%s", self.host, self.port)
        else:
            self._disconnected_at = time.monotonic()
            _LOGGER.warning(
                "MQTT disconnected from %s:%s; grace period %ds",
                self.host,
                self.port,
                self.disconnect_grace_seconds,
            )
        self._check_availability()

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
        self._last_message_utc = datetime.now(timezone.utc)
        raw_num = parse_numeric(payload)
        new_data = dict(self.data)
        # Single source of truth: mqtt_name → raw (entities apply description).
        new_data[mqtt_name] = raw_num if raw_num is not None else payload
        self.async_set_updated_data(new_data)

    async def _async_update_data(self) -> ZeliaData:
        """No polling; return current raw store."""
        return self.data
