"""Select platform for Zelia VP (electrolysis mode)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaEntity
from .helpers import mode_ely_from_raw
from .models import SELECT_DESCRIPTIONS, ZeliaSelectEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia selects."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ZeliaSelect(coordinator, description) for description in SELECT_DESCRIPTIONS
    )


class ZeliaSelect(ZeliaEntity, SelectEntity):
    """Electrolysis mode select."""

    entity_description: ZeliaSelectEntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: ZeliaSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def current_option(self) -> str | None:
        """Return the current mode option from raw mode_ely."""
        return mode_ely_from_raw(self._raw_number())

    async def async_select_option(self, option: str) -> None:
        """Change electrolysis mode (and clear shock)."""
        if option not in self.entity_description.option_map:
            raise ValueError(f"Invalid option: {option}")
        await self.coordinator.async_set_mode_ely(option)
