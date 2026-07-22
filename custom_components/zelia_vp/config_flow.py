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
    DEFAULT_AVAILABILITY_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)
from .helpers import normalize_device_id
from .mqtt_client import validate_mqtt_connection

_LOGGER = logging.getLogger(__name__)


class ZeliaVpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zelia VP."""

    VERSION = 1

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
                            "availability_timeout": DEFAULT_AVAILABILITY_TIMEOUT,
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
        """Manage options (host/port/name/timeout). Reload via update listener."""
        errors: dict[str, str] = {}
        entry = self.config_entry

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            name = user_input[CONF_NAME].strip() or DEFAULT_NAME
            timeout = int(user_input["availability_timeout"])

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
                # Update entry; add_update_listener triggers a single reload.
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=name,
                    data={
                        **entry.data,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_NAME: name,
                    },
                    options={
                        **entry.options,
                        "availability_timeout": timeout,
                    },
                )
                return self.async_create_entry(title="", data={})

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
                    "availability_timeout",
                    default=options.get(
                        "availability_timeout", DEFAULT_AVAILABILITY_TIMEOUT
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
