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
from .helpers import apply_read_scale, is_temp_sentinel
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
        desc = self.entity_description
        raw = self._raw_number()
        if raw is None:
            return None
        if desc.reject_temp_sentinel and is_temp_sentinel(raw):
            return None
        return apply_read_scale(raw, desc.scale)

    async def async_set_native_value(self, value: float) -> None:
        """Publish a new desired value."""
        desc = self.entity_description
        if desc.native_min_value is not None:
            value = max(desc.native_min_value, value)
        if desc.native_max_value is not None:
            value = min(desc.native_max_value, value)
        try:
            await self.coordinator.async_publish_desired(desc.key, value)
        except Exception:
            _LOGGER.exception("Failed to set %s", desc.key)
            raise
