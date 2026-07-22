"""Declarative MQTT entity descriptions and registry for Zelia VP."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)

from .const import MODE_ELY_OPTIONS, PROD_STATE_MAP


@dataclass(frozen=True, kw_only=True)
class ZeliaMqttMixin:
    """MQTT addressing shared by all Zelia entity descriptions."""

    mqtt_type: str
    mqtt_name: str
    qualifier: str = "info"
    scale: float = 1.0
    write_scale: float = 1.0
    # Treat raw >= 65530 as invalid (temperature-style sensors).
    reject_temp_sentinel: bool = False

    @property
    def path(self) -> tuple[str, str, str]:
        """Reported-topic path components."""
        return (self.mqtt_type, self.mqtt_name, self.qualifier)

    @property
    def is_writable(self) -> bool:
        """True if this topic accepts desired publishes."""
        return self.mqtt_type.endswith("_w")


@dataclass(frozen=True, kw_only=True)
class ZeliaSensorEntityDescription(SensorEntityDescription, ZeliaMqttMixin):
    """Sensor description with MQTT mapping."""

    # How to interpret the scaled numeric value for native_value.
    # "number" | "prod_state" | "firmware"
    value_kind: str = "number"


@dataclass(frozen=True, kw_only=True)
class ZeliaBinarySensorEntityDescription(BinarySensorEntityDescription, ZeliaMqttMixin):
    """Binary sensor description with MQTT mapping."""

    on_value: float | None = 1.0
    on_if_gt: float | None = None


@dataclass(frozen=True, kw_only=True)
class ZeliaNumberEntityDescription(NumberEntityDescription, ZeliaMqttMixin):
    """Number description with MQTT mapping."""


@dataclass(frozen=True, kw_only=True)
class ZeliaSwitchEntityDescription(SwitchEntityDescription, ZeliaMqttMixin):
    """Switch description with MQTT mapping."""


@dataclass(frozen=True, kw_only=True)
class ZeliaSelectEntityDescription(SelectEntityDescription, ZeliaMqttMixin):
    """Select description with MQTT mapping."""

    option_map: dict[str, int]


SENSOR_DESCRIPTIONS: tuple[ZeliaSensorEntityDescription, ...] = (
    ZeliaSensorEntityDescription(
        key="water_temp",
        translation_key="water_temp",
        mqtt_type="u16_r",
        mqtt_name="value_temp",
        qualifier="value",
        scale=0.1,
        reject_temp_sentinel=True,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ZeliaSensorEntityDescription(
        key="chlorine_prod",
        translation_key="chlorine_prod",
        mqtt_type="u8_r",
        mqtt_name="prod_chlore",
        qualifier="value",
        native_unit_of_measurement="g/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="voltage_ely",
        translation_key="voltage_ely",
        mqtt_type="u16_r",
        mqtt_name="voltage_ely",
        qualifier="value",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="current_ely",
        translation_key="current_ely",
        mqtt_type="u16_r",
        mqtt_name="current_ely",
        qualifier="value",
        scale=0.1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
    ZeliaSensorEntityDescription(
        key="ely_duration_min",
        translation_key="ely_duration_min",
        mqtt_type="u16_r",
        mqtt_name="ely_duration_in_minut",
        qualifier="value",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="ely_duration_compensated",
        translation_key="ely_duration_compensated",
        mqtt_type="u16_r",
        mqtt_name="ely_duration_compensated",
        qualifier="value",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="conductivity",
        translation_key="conductivity",
        mqtt_type="u16_r",
        mqtt_name="value_cond",
        qualifier="value",
        native_unit_of_measurement="mS/cm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="internal_temp",
        translation_key="internal_temp",
        mqtt_type="u16_r",
        mqtt_name="value_temp_int",
        qualifier="value",
        scale=0.1,
        reject_temp_sentinel=True,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
    ZeliaSensorEntityDescription(
        key="prod_state",
        translation_key="prod_state",
        mqtt_type="u8_r",
        mqtt_name="prod_on",
        qualifier="value",
        device_class=SensorDeviceClass.ENUM,
        options=list(PROD_STATE_MAP.values()),
        value_kind="prod_state",
    ),
    # Raw prod_on code (0/1/2) for automations / diagnostics.
    ZeliaSensorEntityDescription(
        key="prod_on_code",
        translation_key="prod_on_code",
        mqtt_type="u8_r",
        mqtt_name="prod_on",
        qualifier="value",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_kind="number",
    ),
    ZeliaSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        mqtt_type="i8_r",
        mqtt_name="rssi",
        qualifier="info",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="error",
        translation_key="error",
        mqtt_type="u32_r",
        mqtt_name="error",
        qualifier="info",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    ZeliaSensorEntityDescription(
        key="firmware",
        translation_key="firmware",
        mqtt_type="u16_r",
        mqtt_name="sw_vers",
        qualifier="info",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_kind="firmware",
    ),
    ZeliaSensorEntityDescription(
        key="cell_type",
        translation_key="cell_type",
        mqtt_type="u8_r",
        mqtt_name="cell_type",
        qualifier="value",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
)

BINARY_SENSOR_DESCRIPTIONS: tuple[ZeliaBinarySensorEntityDescription, ...] = (
    ZeliaBinarySensorEntityDescription(
        key="production_active",
        translation_key="production_active",
        mqtt_type="u8_r",
        mqtt_name="prod_on",
        qualifier="value",
        device_class=BinarySensorDeviceClass.RUNNING,
        on_if_gt=0.0,
        on_value=None,
    ),
    ZeliaBinarySensorEntityDescription(
        key="flow",
        translation_key="flow",
        mqtt_type="u8_r",
        mqtt_name="flow_on",
        qualifier="value",
        on_value=1.0,
    ),
    ZeliaBinarySensorEntityDescription(
        key="cover",
        translation_key="cover",
        mqtt_type="u8_r",
        mqtt_name="couv_on",
        qualifier="value",
        on_value=1.0,
    ),
)

NUMBER_DESCRIPTIONS: tuple[ZeliaNumberEntityDescription, ...] = (
    ZeliaNumberEntityDescription(
        key="power_ely",
        translation_key="power_ely",
        mqtt_type="u8_w",
        mqtt_name="power_ely",
        qualifier="info",
        native_min_value=0,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    ZeliaNumberEntityDescription(
        key="ely_duration_theo",
        translation_key="ely_duration_theo",
        mqtt_type="u8_w",
        mqtt_name="ely_duration_theo",
        qualifier="info",
        native_min_value=1,
        native_max_value=24,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    ZeliaNumberEntityDescription(
        key="choc_duration",
        translation_key="choc_duration",
        mqtt_type="u8_w",
        mqtt_name="choc_duration",
        qualifier="info",
        native_min_value=1,
        native_max_value=24,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    ZeliaNumberEntityDescription(
        key="temp_min_off",
        translation_key="temp_min_off",
        mqtt_type="u16_w",
        mqtt_name="temp_min_off_ely",
        qualifier="info",
        scale=0.1,
        write_scale=10.0,
        reject_temp_sentinel=True,
        native_min_value=10,
        native_max_value=25,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    ZeliaNumberEntityDescription(
        key="consigne_orp",
        translation_key="consigne_orp",
        mqtt_type="u16_w",
        mqtt_name="consigne_orp",
        qualifier="info",
        native_min_value=500,
        native_max_value=800,
        native_step=10,
        native_unit_of_measurement="mV",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)

SWITCH_DESCRIPTIONS: tuple[ZeliaSwitchEntityDescription, ...] = (
    ZeliaSwitchEntityDescription(
        key="winter_mode",
        translation_key="winter_mode",
        mqtt_type="u8_w",
        mqtt_name="winter_mode",
        qualifier="info",
        entity_category=EntityCategory.CONFIG,
    ),
    ZeliaSwitchEntityDescription(
        key="mode_choc",
        translation_key="mode_choc",
        mqtt_type="u8_w",
        mqtt_name="mode_choc",
        qualifier="info",
        entity_category=EntityCategory.CONFIG,
    ),
)

SELECT_DESCRIPTIONS: tuple[ZeliaSelectEntityDescription, ...] = (
    ZeliaSelectEntityDescription(
        key="mode_ely",
        translation_key="mode_ely",
        mqtt_type="u8_w",
        mqtt_name="mode_ely",
        qualifier="info",
        options=list(MODE_ELY_OPTIONS.keys()),
        option_map=MODE_ELY_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
)


def _all_descriptions() -> tuple[ZeliaMqttMixin, ...]:
    return (
        *SENSOR_DESCRIPTIONS,
        *BINARY_SENSOR_DESCRIPTIONS,
        *NUMBER_DESCRIPTIONS,
        *SWITCH_DESCRIPTIONS,
        *SELECT_DESCRIPTIONS,
    )


def _build_by_key(
    descriptions: Iterable[ZeliaMqttMixin],
) -> dict[str, ZeliaMqttMixin]:
    return {d.key: d for d in descriptions}  # type: ignore[attr-defined]


DESCRIPTIONS_BY_KEY: dict[str, ZeliaMqttMixin] = _build_by_key(_all_descriptions())
WRITABLE_DESCRIPTIONS: dict[str, ZeliaMqttMixin] = {
    key: desc for key, desc in DESCRIPTIONS_BY_KEY.items() if desc.is_writable
}
