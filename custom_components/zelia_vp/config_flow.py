"""Config flow for Zelia VP."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEVICE_ID,
    CONF_DISCONNECT_GRACE,
    DEFAULT_DISCONNECT_GRACE_SECONDS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)
from .helpers import normalize_device_id
from .mqtt_client import validate_mqtt_connection

_LOGGER = logging.getLogger(__name__)


class ZeliaVpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zelia VP."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            name = (user_input.get(CONF_NAME) or DEFAULT_NAME).strip()

            try:
                device_id = normalize_device_id(user_input[CONF_DEVICE_ID])
            except ValueError:
                errors["base"] = "invalid_device_id"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                try:
                    await validate_mqtt_connection(host, port, device_id, timeout=6.0)
                except TimeoutError:
                    errors["base"] = "timeout"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Cannot connect to Zelia MQTT")
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_DEVICE_ID: device_id,
                            CONF_NAME: name,
                        },
                        options={
                            CONF_DISCONNECT_GRACE: DEFAULT_DISCONNECT_GRACE_SECONDS,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return ZeliaVpOptionsFlow()


class ZeliaVpOptionsFlow(OptionsFlow):
    """Handle options for an existing Zelia entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options (host/port/name/grace period). Reload via update listener."""
        errors: dict[str, str] = {}
        entry = self.config_entry

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            name = user_input[CONF_NAME].strip() or DEFAULT_NAME
            grace = int(user_input[CONF_DISCONNECT_GRACE])

            try:
                await validate_mqtt_connection(
                    host,
                    port,
                    entry.data[CONF_DEVICE_ID],
                    timeout=6.0,
                )
            except TimeoutError:
                errors["base"] = "timeout"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                # Update data (host/port/name); options are returned via async_create_entry.
                # Note: async_create_entry(data=...) in OptionsFlow sets the entry's options.
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=name,
                    data={
                        **entry.data,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_NAME: name,
                    },
                )
                # Return new options; triggers add_update_listener for reload.
                return self.async_create_entry(
                    title="",
                    data={CONF_DISCONNECT_GRACE: grace},
                )

        data = entry.data
        options = entry.options
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): cv.string,
                vol.Required(
                    CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)
                ): cv.port,
                vol.Required(
                    CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)
                ): cv.string,
                vol.Required(
                    CONF_DISCONNECT_GRACE,
                    default=options.get(
                        CONF_DISCONNECT_GRACE, DEFAULT_DISCONNECT_GRACE_SECONDS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
