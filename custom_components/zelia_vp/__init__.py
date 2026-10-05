"""Zelia VP Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVICE_ID,
    CONF_DISCONNECT_GRACE,
    DEFAULT_DISCONNECT_GRACE_SECONDS,
    DEFAULT_PORT,
    DOMAIN,
    LEGACY_AVAILABILITY_TIMEOUT,
    PLATFORMS,
)
from .coordinator import ZeliaCoordinator

_LOGGER = logging.getLogger(__name__)

type ZeliaConfigEntry = ConfigEntry


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry from older versions.

    Version 1 → 2: availability_timeout (message-age based) is removed.
    The new logic ties availability to the MQTT session + grace period.
    Old stored availability_timeout values are ignored; we use the default
    disconnect_grace_seconds instead. This fixes false unavailability for
    devices that publish infrequently (~915s–3610s).
    """
    if entry.version < 2:
        _LOGGER.info(
            "Migrating Zelia VP entry %s from version %s to 2",
            entry.entry_id,
            entry.version,
        )
        new_options = dict(entry.options)
        # Remove legacy availability_timeout (no longer used).
        new_options.pop(LEGACY_AVAILABILITY_TIMEOUT, None)
        # Set the new disconnect_grace_seconds option.
        new_options[CONF_DISCONNECT_GRACE] = DEFAULT_DISCONNECT_GRACE_SECONDS

        hass.config_entries.async_update_entry(
            entry,
            version=2,
            options=new_options,
        )
        _LOGGER.info(
            "Migrated Zelia VP entry %s to version 2 (disconnect_grace=%ds)",
            entry.entry_id,
            DEFAULT_DISCONNECT_GRACE_SECONDS,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZeliaConfigEntry) -> bool:
    """Set up Zelia VP from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)
    device_id: str = entry.data[CONF_DEVICE_ID]

    # Migration: convert legacy availability_timeout to disconnect_grace_seconds.
    # Old entries stored availability_timeout (message-age based), which caused
    # false unavailability. New logic uses MQTT session + grace period.
    disconnect_grace = entry.options.get(
        CONF_DISCONNECT_GRACE, DEFAULT_DISCONNECT_GRACE_SECONDS
    )

    coordinator = ZeliaCoordinator(
        hass,
        entry,
        host=host,
        port=port,
        device_id=device_id,
        disconnect_grace_seconds=disconnect_grace,
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
