"""Sensor platform for Zelia VP."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .helpers import (
    apply_read_scale,
    error_attributes_from_raw,
    error_e_codes_state_from_raw,
    firmware_from_raw,
    is_temp_sentinel,
    prod_state_from_raw,
)
from .models import SENSOR_DESCRIPTIONS, ZeliaSensorEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia sensors."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ZeliaSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(ZeliaLastSeenSensor(coordinator))
    async_add_entities(entities)


class ZeliaSensor(ZeliaEntity, SensorEntity):
    """Representation of a Zelia sensor."""

    entity_description: ZeliaSensorEntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: ZeliaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def native_value(self):
        """Return scaled / mapped value from raw store + description."""
        desc = self.entity_description
        raw = self._raw_number()
        if raw is None:
            return None
        if desc.reject_temp_sentinel and is_temp_sentinel(raw):
            return None
        if desc.value_kind == "prod_state":
            return prod_state_from_raw(raw)
        if desc.value_kind == "firmware":
            return firmware_from_raw(raw)
        if desc.value_kind == "error_e_codes":
            return error_e_codes_state_from_raw(raw)
        return apply_read_scale(raw, desc.scale)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose raw codes and decoded error bits."""
        kind = self.entity_description.value_kind
        raw = self._raw_number()
        if raw is None:
            return None
        if kind == "prod_state":
            return {"prod_on_code": int(raw)}
        if kind in ("error_raw", "error_e_codes"):
            return error_attributes_from_raw(raw)
        return None


class ZeliaLastSeenSensor(SensorEntity):
    """Diagnostic sensor showing the last MQTT message timestamp.

    Always available; shows when the device last sent data.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_seen"

    def __init__(self, coordinator: ZeliaCoordinator) -> None:
        """Initialize the last seen sensor."""
        from homeassistant.helpers.device_registry import DeviceInfo

        from .const import MANUFACTURER, MODEL
        from .helpers import firmware_from_raw, mac_from_device_id

        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_last_seen"

        connections: set[tuple[str, str]] = set()
        mac = mac_from_device_id(coordinator.device_id)
        if mac:
            connections.add(("mac", mac))

        name = coordinator.entry.data.get("name") or MODEL
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            connections=connections or None,
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=name,
            sw_version=firmware_from_raw(coordinator.get_raw_number("sw_vers")),
            configuration_url="https://www.ccei-pool.com/fr/produit/zelia-vp",
        )

    @property
    def available(self) -> bool:
        """Always available; shows last seen time even when disconnected."""
        return True

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last MQTT message."""
        return self.coordinator.last_message_time

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        """Expose age in seconds for convenience."""
        return {"age_seconds": self.coordinator.last_message_age}

    async def async_added_to_hass(self) -> None:
        """Register update callback when added."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
