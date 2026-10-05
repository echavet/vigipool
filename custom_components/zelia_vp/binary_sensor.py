"""Binary sensor platform for Zelia VP."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .models import BINARY_SENSOR_DESCRIPTIONS, ZeliaBinarySensorEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia binary sensors."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [
        ZeliaBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]
    entities.append(ZeliaMqttConnectedSensor(coordinator))
    async_add_entities(entities)


class ZeliaBinarySensor(ZeliaEntity, BinarySensorEntity):
    """Representation of a Zelia binary sensor."""

    entity_description: ZeliaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: ZeliaBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        raw = self._raw_number()
        if raw is None:
            return None
        desc = self.entity_description
        if desc.on_if_gt is not None:
            return raw > desc.on_if_gt
        if desc.on_value is not None:
            return raw == desc.on_value
        return bool(raw)


class ZeliaMqttConnectedSensor(BinarySensorEntity):
    """Diagnostic binary sensor showing MQTT connection state.

    This sensor is always available (it reports the connection itself).
    On = MQTT connected; Off = disconnected.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "mqtt_connected"

    def __init__(self, coordinator: ZeliaCoordinator) -> None:
        """Initialize the MQTT connected sensor."""
        from homeassistant.helpers.device_registry import DeviceInfo

        from .const import MANUFACTURER, MODEL
        from .helpers import firmware_from_raw, mac_from_device_id

        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_mqtt_connected"

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
        """Always available; this sensor reports connectivity itself."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True if MQTT is connected."""
        return self.coordinator.mqtt_connected

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        """Expose last message age for diagnostics."""
        return {"last_message_age_seconds": self.coordinator.last_message_age}

    async def async_added_to_hass(self) -> None:
        """Register update callback when added."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
