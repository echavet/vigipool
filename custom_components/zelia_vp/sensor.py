"""Sensor platform for Zelia VP."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .models import SENSOR_DESCRIPTIONS, ZeliaSensorEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia sensors."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ZeliaSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


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
        """Return the sensor value."""
        raw = self.coordinator.get_value(self.entity_description.key)
        if self.entity_description.value_fn is not None:
            # value_fn may expect already-scaled or enum raw depending on key
            if self.entity_description.key == "prod_state":
                return raw
            if self.entity_description.key == "firmware":
                return raw
            return self.entity_description.value_fn(raw)
        return raw
