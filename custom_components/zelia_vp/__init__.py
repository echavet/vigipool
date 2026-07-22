"""Zelia VP Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVICE_ID,
    DEFAULT_AVAILABILITY_TIMEOUT,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ZeliaCoordinator

_LOGGER = logging.getLogger(__name__)

type ZeliaConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ZeliaConfigEntry) -> bool:
    """Set up Zelia VP from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)
    device_id: str = entry.data[CONF_DEVICE_ID]
    availability_timeout: int = entry.options.get(
        "availability_timeout", DEFAULT_AVAILABILITY_TIMEOUT
    )

    coordinator = ZeliaCoordinator(
        hass,
        entry,
        host=host,
        port=port,
        device_id=device_id,
        availability_timeout=availability_timeout,
    )
    # Start MQTT in background; availability tracks last message (permissive setup).
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "Zelia VP ready: %s (%s:%s) name=%s",
        device_id,
        host,
        port,
        entry.data.get(CONF_NAME),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZeliaConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ZeliaCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options/data change."""
    await hass.config_entries.async_reload(entry.entry_id)
