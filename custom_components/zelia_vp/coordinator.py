"""DataUpdateCoordinator for Zelia VP (push-first MQTT)."""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_AVAILABILITY_TIMEOUT, DOMAIN, WRITABLE_KEYS
from .helpers import apply_scale, build_topic, is_temp_sentinel, parse_numeric, prod_state_value
from .models import (
    BINARY_SENSOR_DESCRIPTIONS,
    NUMBER_DESCRIPTIONS,
    SELECT_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
    SWITCH_DESCRIPTIONS,
)
from .mqtt_client import ZeliaMqttClient

_LOGGER = logging.getLogger(__name__)


def _index_mqtt_paths() -> dict[tuple[str, str, str], str]:
    """Map (type, name, qualifier) -> entity key for reported topics."""
    index: dict[tuple[str, str, str], str] = {}
    for desc in (
        *SENSOR_DESCRIPTIONS,
        *BINARY_SENSOR_DESCRIPTIONS,
        *NUMBER_DESCRIPTIONS,
        *SWITCH_DESCRIPTIONS,
        *SELECT_DESCRIPTIONS,
    ):
        index[(desc.mqtt_type, desc.mqtt_name, desc.qualifier)] = desc.key
    return index


MQTT_PATH_INDEX = _index_mqtt_paths()

# Scale lookup for known keys (used when parsing into store).
_SCALE_BY_KEY: dict[str, float] = {
    desc.key: desc.scale
    for desc in (
        *SENSOR_DESCRIPTIONS,
        *BINARY_SENSOR_DESCRIPTIONS,
        *NUMBER_DESCRIPTIONS,
        *SWITCH_DESCRIPTIONS,
        *SELECT_DESCRIPTIONS,
    )
}

# Also store raw mqtt_name values for diagnostics / unknown fields.
_TEMP_KEYS = {"water_temp", "internal_temp", "temp_min_off"}


class ZeliaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds latest values pushed from the device MQTT broker."""

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
            update_interval=None,  # push-only
        )
        self.entry = entry
        self.host = host
        self.port = port
        self.device_id = device_id
        self.availability_timeout = availability_timeout
        self._raw: dict[str, str] = {}
        self._last_message_at: float | None = None
        self.mqtt = ZeliaMqttClient(host, port, device_id, self._handle_message)
        # Initial empty data so entities can set up before first push.
        self.data = {}

    async def async_start(self) -> None:
        """Start MQTT client."""
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
        """True if MQTT is connected and recent data was received."""
        if not self.mqtt.connected:
            # Still available briefly if we have recent data during reconnect.
            if self._last_message_at is None:
                return False
        if self._last_message_at is None:
            # Connected but no data yet: treat as available to avoid flapping at setup.
            return self.mqtt.connected
        return self.last_message_age is not None and self.last_message_age < self.availability_timeout

    def get_value(self, key: str) -> Any:
        """Return a parsed value from the store."""
        return self.data.get(key)

    def get_raw(self, key: str) -> str | None:
        """Return raw payload string for a key if known."""
        return self._raw.get(key)

    async def async_publish_desired(self, key: str, value: float | int) -> None:
        """Publish a desired value for a whitelisted writable key."""
        if key not in WRITABLE_KEYS:
            raise ValueError(f"Key {key} is not writable")

        desc = next(
            (
                d
                for d in (
                    *NUMBER_DESCRIPTIONS,
                    *SWITCH_DESCRIPTIONS,
                    *SELECT_DESCRIPTIONS,
                )
                if d.key == key
            ),
            None,
        )
        if desc is None:
            raise ValueError(f"No description for writable key {key}")

        write_scale = getattr(desc, "write_scale", 1.0)
        payload_num = value * write_scale
        # Device expects integer-like string payloads.
        if float(payload_num).is_integer():
            payload = str(int(payload_num))
        else:
            payload = str(payload_num)

        topic = build_topic(
            self.device_id,
            desc.mqtt_type,
            desc.mqtt_name,
            desc.qualifier,
            "desired",
        )
        await self.mqtt.publish(topic, payload)
        _LOGGER.debug("Desired %s -> %s (%s)", key, payload, topic)

    async def async_set_mode_ely(self, option: str) -> None:
        """Set electrolysis mode and clear shock mode."""
        from .const import MODE_ELY_OPTIONS

        if option not in MODE_ELY_OPTIONS:
            raise ValueError(f"Unknown mode: {option}")
        await self.async_publish_desired("mode_ely", MODE_ELY_OPTIONS[option])
        await self.async_publish_desired("mode_choc", 0)

    @callback
    def _handle_message(self, topic: str, payload: str) -> None:
        """Process an incoming MQTT message (called from MQTT task)."""
        # Schedule on HA loop for thread-safety / coordinator updates.
        self.hass.loop.call_soon_threadsafe(
            self._process_message_sync, topic, payload
        )

    @callback
    def _process_message_sync(self, topic: str, payload: str) -> None:
        """Parse topic and update coordinator data."""
        parts = topic.split("/")
        # Expected: device_id / type / name / qualifier / reported|desired
        if len(parts) < 5:
            return
        device_id, mqtt_type, mqtt_name, qualifier, direction = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
        )
        if device_id != self.device_id:
            return
        if direction != "reported":
            return

        self._last_message_at = time.monotonic()
        self._raw[mqtt_name] = payload

        key = MQTT_PATH_INDEX.get((mqtt_type, mqtt_name, qualifier))
        new_data = dict(self.data)

        # Always keep raw mqtt_name for diagnostics.
        new_data[f"raw_{mqtt_name}"] = payload

        raw_num = parse_numeric(payload)

        if key is not None:
            scale = _SCALE_BY_KEY.get(key, 1.0)
            # Temperature sentinels: mark as None before scaling.
            if key in _TEMP_KEYS and is_temp_sentinel(raw_num):
                new_data[key] = None
            elif key == "firmware":
                new_data[key] = None if raw_num is None else str(int(raw_num))
            elif key == "prod_state":
                new_data[key] = prod_state_value(raw_num)
                new_data["prod_on_raw"] = raw_num
            else:
                new_data[key] = apply_scale(raw_num, scale)

            # Binary sensors share prod_on topic.
            if mqtt_name == "prod_on" and raw_num is not None:
                new_data["prod_on_raw"] = raw_num
                new_data["production_active"] = raw_num > 0
                new_data["prod_state"] = prod_state_value(raw_num)
            if mqtt_name == "flow_on" and raw_num is not None:
                new_data["flow"] = raw_num == 1
            if mqtt_name == "couv_on" and raw_num is not None:
                new_data["cover"] = raw_num == 1
            if mqtt_name == "winter_mode" and raw_num is not None:
                new_data["winter_mode"] = raw_num == 1
            if mqtt_name == "mode_choc" and raw_num is not None:
                new_data["mode_choc"] = raw_num == 1
            if mqtt_name == "mode_ely" and raw_num is not None:
                from .const import MODE_ELY_REVERSE

                new_data["mode_ely"] = MODE_ELY_REVERSE.get(int(raw_num))
                new_data["mode_ely_raw"] = int(raw_num)
            if mqtt_name == "sw_vers" and raw_num is not None:
                new_data["firmware"] = str(int(raw_num))
        else:
            # Unmapped but useful raw.
            if raw_num is not None:
                new_data[mqtt_name] = raw_num
            else:
                new_data[mqtt_name] = payload

        self.async_set_updated_data(new_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """No polling; return current data (used if something requests refresh)."""
        return self.data
