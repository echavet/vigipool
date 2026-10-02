"""Base entity for Zelia VP."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ZeliaCoordinator
from .helpers import firmware_from_raw, mac_from_device_id
from .models import ZeliaMqttMixin


class ZeliaEntity(CoordinatorEntity[ZeliaCoordinator]):
    """Base class for all Zelia entities."""

    _attr_has_entity_name = True
    entity_description: EntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

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
        """Return True if we have recent MQTT data."""
        return self.coordinator.device_available

    def _mqtt_desc(self) -> ZeliaMqttMixin:
        """Cast entity_description to MQTT mixin (all Zelia descs have it)."""
        return self.entity_description  # type: ignore[return-value]

    def _raw_number(self) -> float | None:
        """Raw numeric value for this entity's mqtt_name."""
        return self.coordinator.get_raw_number(self._mqtt_desc().mqtt_name)


class ZeliaWritableEntity(ZeliaEntity):
    """Base class for writable Zelia entities (number, switch, select).

    Writable entities remain available as long as the MQTT broker is connected,
    so that commands can be published even when the device has been quiet.
    """

    @property
    def available(self) -> bool:
        """Return True if MQTT is connected (commands can be sent)."""
        return self.coordinator.mqtt_connected
