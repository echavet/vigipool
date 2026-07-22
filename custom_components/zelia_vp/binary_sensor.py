"""Binary sensor platform for Zelia VP."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities(
        ZeliaBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


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
        value = self.coordinator.get_value(self.entity_description.key)
        if value is None:
            # Fallback to raw numeric for shared topics.
            if self.entity_description.key == "production_active":
                raw = self.coordinator.get_value("prod_on_raw")
                if raw is None:
                    return None
                return raw > 0
            return None
        if isinstance(value, bool):
            return value
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if self.entity_description.on_if_gt is not None:
            return num > self.entity_description.on_if_gt
        if self.entity_description.on_value is not None:
            return num == self.entity_description.on_value
        return bool(num)
