"""Sensor platform for Zelia VP."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .helpers import (
    apply_read_scale,
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
        return apply_read_scale(raw, desc.scale)

    @property
    def extra_state_attributes(self) -> dict[str, int | float] | None:
        """Expose raw prod_on on the human-readable production state sensor."""
        if self.entity_description.value_kind != "prod_state":
            return None
        raw = self._raw_number()
        if raw is None:
            return None
        return {"prod_on_code": int(raw)}
