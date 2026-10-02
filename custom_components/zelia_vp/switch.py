"""Switch platform for Zelia VP."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZeliaCoordinator
from .entity import ZeliaWritableEntity
from .models import SWITCH_DESCRIPTIONS, ZeliaSwitchEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zelia switches."""
    coordinator: ZeliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ZeliaSwitch(coordinator, description) for description in SWITCH_DESCRIPTIONS
    )


class ZeliaSwitch(ZeliaWritableEntity, SwitchEntity):
    """Writable switch entity for Zelia."""

    entity_description: ZeliaSwitchEntityDescription

    def __init__(
        self,
        coordinator: ZeliaCoordinator,
        description: ZeliaSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        raw = self._raw_number()
        if raw is None:
            return None
        return raw == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.coordinator.async_publish_desired(self.entity_description.key, 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.coordinator.async_publish_desired(self.entity_description.key, 0)
