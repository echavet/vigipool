"""Base entity for Zelia VP."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ZeliaCoordinator
from .helpers import mac_from_device_id


class ZeliaEntity(CoordinatorEntity[ZeliaCoordinator]):
    """Base class for all Zelia entities."""

    _attr_has_entity_name = True

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
            sw_version=coordinator.get_value("firmware"),
            configuration_url="https://www.ccei-pool.com/fr/produit/zelia-vp",
        )

    @property
    def available(self) -> bool:
        """Return True if the device is considered online."""
        return self.coordinator.device_available

    def _handle_coordinator_update(self) -> None:
        """Refresh device firmware when available."""
        fw = self.coordinator.get_value("firmware")
        if fw and self.device_info is not None:
            # device_info is frozen in practice; update via registry happens
            # through HA when sw_version changes on DeviceInfo at creation.
            # Keep entity state updates only here.
            pass
        super()._handle_coordinator_update()
