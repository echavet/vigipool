"""Number platform for Zelia VP."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .models import NUMBER_DESCRIPTIONS, ZeliaNumberEntityDescription

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia numbers."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ZeliaNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )


class ZeliaNumber(ZeliaEntity, NumberEntity):
    """Writable number entity for Zelia."""

    entity_description: ZeliaNumberEntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: ZeliaNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the current value (scaled for display)."""
        value = self.coordinator.get_value(self.entity_description.key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Publish a new desired value."""
        # Clamp to description bounds.
        min_v = self.entity_description.native_min_value
        max_v = self.entity_description.native_max_value
        if min_v is not None:
            value = max(min_v, value)
        if max_v is not None:
            value = min(max_v, value)
        try:
            await self.coordinator.async_publish_desired(
                self.entity_description.key, value
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to set %s", self.entity_description.key)
            raise
