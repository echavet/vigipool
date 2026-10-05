"""Unit tests for pure helpers and raw-store interpretation (no Home Assistant)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "zelia_vp"


def _load(name: str, path: Path):
    """Load a module file under the zelia_vp package without importing __init__.py."""
    if "zelia_vp" not in sys.modules:
        pkg = types.ModuleType("zelia_vp")
        pkg.__path__ = [str(PKG_DIR)]
        sys.modules["zelia_vp"] = pkg
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


const = _load("zelia_vp.const", PKG_DIR / "const.py")
helpers = _load("zelia_vp.helpers", PKG_DIR / "helpers.py")


def test_build_topic() -> None:
    assert (
        helpers.build_topic(
            "zelix_8C4B14821190", "u16_r", "value_temp", "value", "reported"
        )
        == "zelix_8C4B14821190/u16_r/value_temp/value/reported"
    )
    assert (
        helpers.build_topic(
            "zelix_8C4B14821190", "u8_w", "power_ely", "info", "desired"
        )
        == "zelix_8C4B14821190/u8_w/power_ely/info/desired"
    )


def test_parse_topic() -> None:
    parsed = helpers.parse_topic(
        "zelix_8C4B14821190/u16_r/value_temp/value/reported"
    )
    assert parsed == (
        "zelix_8C4B14821190",
        "u16_r",
        "value_temp",
        "value",
        "reported",
    )
    assert helpers.parse_topic("too/short") is None


def test_live_capture_scales() -> None:
    # value_temp 285 -> 28.5 °C
    assert helpers.apply_read_scale(helpers.parse_numeric("285"), 0.1) == 28.5
    # temp_min_off 150 -> 15.0 °C
    assert helpers.apply_read_scale(helpers.parse_numeric("150"), 0.1) == 15.0
    # current_ely 32 -> 3.2 A
    assert helpers.apply_read_scale(helpers.parse_numeric("32"), 0.1) == 3.2
    # consigne_orp 650 mV (no scale)
    assert helpers.apply_read_scale(helpers.parse_numeric("650"), 1.0) == 650.0
    # write temp_min: 15.0 * 10 = 150
    assert helpers.format_payload(15.0 * 10.0) == "150"


def test_prod_state_map() -> None:
    # Live: prod_on=1 with prod_chlore=19 / current → producing, not "requested"
    assert helpers.prod_state_from_raw(0) == "off"
    assert helpers.prod_state_from_raw(1) == "on"
    assert helpers.prod_state_from_raw(2) == "reverse"
    assert helpers.prod_state_from_raw(9) is None
    assert set(const.PROD_STATE_MAP) == {0, 1, 2}


def test_mode_ely_from_raw() -> None:
    assert helpers.mode_ely_from_raw(0) == "off"
    assert helpers.mode_ely_from_raw(2) == "auto"
    assert helpers.mode_ely_from_raw(99) is None


def test_temp_sentinel() -> None:
    assert helpers.is_temp_sentinel(65534)
    assert helpers.is_temp_sentinel(65530)
    assert not helpers.is_temp_sentinel(285)


def test_normalize_device_id() -> None:
    assert helpers.normalize_device_id("zelix_8c4b14821190") == "zelix_8C4B14821190"
    assert helpers.normalize_device_id("8C4B14821190") == "zelix_8C4B14821190"
    assert helpers.normalize_device_id("8c:4b:14:82:11:90") == "zelix_8C4B14821190"


def test_error_bitmask_e14() -> None:
    # Live 2026-08-16: MQTT 16384 + Vigipool app E14 (taux de sel trop élevé)
    assert const.ERROR_MASK_HIGH_SALT == 16384
    assert const.ERROR_MASK_HIGH_SALT == 1 << 14
    assert helpers.error_bits_from_raw(16384) == [14]
    assert helpers.error_bits_from_raw(16384.0) == [14]
    assert helpers.error_e_codes_from_raw(16384) == ["E14"]
    assert helpers.error_e_codes_state_from_raw(16384) == "E14"
    assert helpers.error_e_codes_state_from_raw(0) == "none"
    assert helpers.error_e_codes_from_raw(0) == []
    assert helpers.error_e_codes_state_from_raw(None) is None
    assert helpers.error_attributes_from_raw(None) is None
    attrs = helpers.error_attributes_from_raw(16384)
    assert attrs is not None
    assert attrs["error_hex"] == "0x4000"
    assert attrs["error_bits"] == [14]
    assert attrs["e_codes"] == ["E14"]
    assert attrs["labels"] == ["high_salt"]
    assert attrs["high_salt"] is True
    # Combined bits: En = bit n
    assert helpers.error_e_codes_state_from_raw((1 << 2) | 16384) == "E2+E14"
    none_attrs = helpers.error_attributes_from_raw(0)
    assert none_attrs is not None
    assert none_attrs["high_salt"] is False
    assert none_attrs["e_codes"] == []
    # 13384 is not 1<<14; it must not decode as a lone E14.
    assert helpers.error_e_codes_state_from_raw(13384) != "E14"
    assert 14 not in helpers.error_bits_from_raw(13384)


def test_mode_ely_options() -> None:
    assert const.MODE_ELY_OPTIONS["off"] == 0
    assert const.MODE_ELY_OPTIONS["programmed"] == 1
    assert const.MODE_ELY_OPTIONS["auto"] == 2
    assert const.MODE_ELY_OPTIONS["regulated"] == 3


def test_raw_store_interpretation_pipeline() -> None:
    """Simulate coordinator raw store + entity-layer transforms."""
    store: dict[str, float | str] = {
        "value_temp": 285.0,
        "temp_min_off_ely": 150.0,
        "prod_on": 1.0,
        "mode_ely": 2.0,
        "sw_vers": 832.0,
        "power_ely": 100.0,
    }

    assert helpers.apply_read_scale(float(store["value_temp"]), 0.1) == 28.5
    assert helpers.apply_read_scale(float(store["temp_min_off_ely"]), 0.1) == 15.0
    assert helpers.prod_state_from_raw(float(store["prod_on"])) == "on"
    assert float(store["prod_on"]) > 0  # production_active
    assert helpers.mode_ely_from_raw(float(store["mode_ely"])) == "auto"
    assert helpers.firmware_from_raw(float(store["sw_vers"])) == "832"


def test_default_disconnect_grace_seconds() -> None:
    """Default grace period allows network hiccups without flapping."""
    # Fix: availability is now based on MQTT session, not message age.
    # Grace period (180s) allows reconnection after brief disconnects.
    assert const.DEFAULT_DISCONNECT_GRACE_SECONDS == 180


def test_format_payload_integer() -> None:
    """format_payload must produce integer strings for u8/u16 values."""
    # Integer values
    assert helpers.format_payload(76) == "76"
    assert helpers.format_payload(76.0) == "76"
    assert helpers.format_payload(0) == "0"
    assert helpers.format_payload(100) == "100"
    # Fractional values (for temp with write_scale)
    assert helpers.format_payload(155.0) == "155"
    # Non-integer values are preserved (should be rounded before calling)
    assert helpers.format_payload(72.5) == "72.5"


def test_format_payload_rounding_for_u8() -> None:
    """Simulate u8 value rounding as done in number.py async_set_native_value."""
    # u8 registers require integer values; round before publishing.
    value = 76.5
    rounded = round(value)
    assert rounded == 76
    # After rounding, format_payload produces integer string
    payload_num = float(rounded) * 1.0  # write_scale=1.0 for power_ely
    assert helpers.format_payload(payload_num) == "76"


def test_u8_rounding_76_4_becomes_76() -> None:
    """ZeliaNumber.async_set_native_value rounds 76.4 to 76 for u8_w registers.

    This simulates the rounding logic in number.py without HA imports.
    The actual code does: if desc.mqtt_type.startswith("u8_w"): value = round(value)
    """
    mqtt_type = "u8_w"
    value = 76.4

    # Simulate number.py logic
    if mqtt_type.startswith("u8_w"):
        value = round(value)

    assert value == 76
    # Then coordinator multiplies by write_scale (1.0) and formats
    payload_num = float(value) * 1.0
    assert helpers.format_payload(payload_num) == "76"


class FakeCoordinatorAvailability:
    """Minimal fake to test _check_availability logic without HA imports."""

    def __init__(self) -> None:
        self._last_availability_state: tuple[bool, bool] | None = None
        self._device_available = False
        self._mqtt_connected = False
        self.update_count = 0
        self.data: dict = {}

    @property
    def device_available(self) -> bool:
        return self._device_available

    @property
    def mqtt_connected(self) -> bool:
        return self._mqtt_connected

    def async_set_updated_data(self, data: dict) -> None:
        self.update_count += 1

    def _check_availability(self, _now=None) -> None:
        """Same logic as ZeliaCoordinator._check_availability."""
        current_state = (self.device_available, self.mqtt_connected)
        if self._last_availability_state != current_state:
            self._last_availability_state = current_state
            self.async_set_updated_data(self.data)


def test_check_availability_fires_on_device_change() -> None:
    """_check_availability fires update when device_available changes."""
    fake = FakeCoordinatorAvailability()
    assert fake.update_count == 0

    # First call: state changes from None to (False, False)
    fake._check_availability()
    assert fake.update_count == 1

    # No change: should not fire
    fake._check_availability()
    assert fake.update_count == 1

    # device_available changes
    fake._device_available = True
    fake._check_availability()
    assert fake.update_count == 2


def test_check_availability_fires_on_mqtt_change() -> None:
    """_check_availability fires update when mqtt_connected changes."""
    fake = FakeCoordinatorAvailability()

    # Initialize
    fake._check_availability()
    assert fake.update_count == 1

    # mqtt_connected changes
    fake._mqtt_connected = True
    fake._check_availability()
    assert fake.update_count == 2

    # No change
    fake._check_availability()
    assert fake.update_count == 2

    # mqtt disconnects
    fake._mqtt_connected = False
    fake._check_availability()
    assert fake.update_count == 3


def test_check_availability_fires_on_both_changes() -> None:
    """_check_availability fires when both flags change together."""
    fake = FakeCoordinatorAvailability()

    fake._check_availability()
    assert fake.update_count == 1

    # Both change at once
    fake._device_available = True
    fake._mqtt_connected = True
    fake._check_availability()
    assert fake.update_count == 2


def test_power_ely_step() -> None:
    """power_ely should accept any integer 0-100 (native_step=1).

    Bug fix: step was 5, but device accepts any integer (official app set 76).
    This test reads the models.py file directly to avoid homeassistant dependency.
    """
    models_path = PKG_DIR / "models.py"
    content = models_path.read_text()

    # Check native_step=1 for power_ely description
    # Look for the pattern in the file
    assert "native_step=1," in content, "power_ely should have native_step=1"

    # Verify it's associated with power_ely by checking the context
    import re

    # Find the power_ely description block
    pattern = r'key="power_ely".*?native_step=(\d+)'
    match = re.search(pattern, content, re.DOTALL)
    assert match is not None, "power_ely description not found"
    assert match.group(1) == "1", f"power_ely native_step should be 1, got {match.group(1)}"


# =============================================================================
# New tests for session-based availability (2026.10.5 fix)
# =============================================================================


class FakeMqttClient:
    """Minimal MQTT client stub for testing coordinator availability logic."""

    def __init__(self) -> None:
        self.connected = False


class FakeCoordinatorSessionAvailability:
    """Test fixture mimicking new ZeliaCoordinator availability logic.

    Availability is based on MQTT session + grace period, NOT message age.
    """

    def __init__(self, disconnect_grace_seconds: int = 180) -> None:
        self.mqtt = FakeMqttClient()
        self.disconnect_grace_seconds = disconnect_grace_seconds
        self._disconnected_at: float | None = None
        self._last_message_at: float | None = None
        self._monotonic_now = 0.0

    def set_time(self, t: float) -> None:
        """Advance fake monotonic time."""
        self._monotonic_now = t

    def connect(self) -> None:
        """Simulate MQTT connect."""
        self.mqtt.connected = True
        self._disconnected_at = None

    def disconnect(self) -> None:
        """Simulate MQTT disconnect."""
        self.mqtt.connected = False
        self._disconnected_at = self._monotonic_now

    def receive_message(self) -> None:
        """Simulate receiving an MQTT message."""
        self._last_message_at = self._monotonic_now

    @property
    def device_available(self) -> bool:
        """Same logic as ZeliaCoordinator.device_available."""
        if self.mqtt.connected:
            return True
        if self._disconnected_at is None:
            return False
        grace_elapsed = self._monotonic_now - self._disconnected_at
        return grace_elapsed < self.disconnect_grace_seconds


def test_silence_longer_than_old_timeout_keeps_available() -> None:
    """MQTT silence > old 600s timeout does NOT cause unavailable.

    This was the bug: availability was based on message age with 600s timeout,
    but the device only publishes every ~915s (pump on) or ~3610s (pump off).
    Now availability is based on MQTT session, not message age.
    """
    coord = FakeCoordinatorSessionAvailability(disconnect_grace_seconds=180)
    coord.set_time(0)
    coord.connect()
    coord.receive_message()

    # Verify available immediately after connect + message
    assert coord.device_available is True

    # Simulate 1000s of silence (> old 600s timeout, > ~915s pump-on period)
    coord.set_time(1000)
    # Still connected → still available despite long silence
    assert coord.device_available is True

    # Simulate 4000s of silence (> ~3610s pump-off period)
    coord.set_time(4000)
    assert coord.device_available is True


def test_mqtt_disconnect_triggers_grace_period() -> None:
    """MQTT disconnect starts grace period; unavailable after it expires."""
    coord = FakeCoordinatorSessionAvailability(disconnect_grace_seconds=180)
    coord.set_time(0)
    coord.connect()
    coord.receive_message()
    assert coord.device_available is True

    # Disconnect at t=100
    coord.set_time(100)
    coord.disconnect()

    # Still in grace period (0s elapsed)
    assert coord.device_available is True

    # 179s elapsed → still in grace period
    coord.set_time(100 + 179)
    assert coord.device_available is True

    # 180s elapsed → grace period expired → unavailable
    coord.set_time(100 + 180)
    assert coord.device_available is False

    # 300s elapsed → still unavailable
    coord.set_time(100 + 300)
    assert coord.device_available is False


def test_reconnect_restores_availability() -> None:
    """Reconnecting after grace period expiry restores availability."""
    coord = FakeCoordinatorSessionAvailability(disconnect_grace_seconds=180)
    coord.set_time(0)
    coord.connect()
    coord.receive_message()

    # Disconnect and wait past grace period
    coord.set_time(100)
    coord.disconnect()
    coord.set_time(100 + 200)  # 200s > 180s grace
    assert coord.device_available is False

    # Reconnect
    coord.connect()
    assert coord.device_available is True

    # Stays available even without new messages
    coord.set_time(100 + 500)
    assert coord.device_available is True


def test_reconnect_during_grace_period_clears_disconnect() -> None:
    """Reconnecting during grace period resets the timer."""
    coord = FakeCoordinatorSessionAvailability(disconnect_grace_seconds=180)
    coord.set_time(0)
    coord.connect()

    # Disconnect
    coord.set_time(100)
    coord.disconnect()

    # 90s into grace period
    coord.set_time(190)
    assert coord.device_available is True

    # Reconnect
    coord.connect()
    assert coord._disconnected_at is None  # Timer cleared

    # Still available after what would have been expiry
    coord.set_time(300)
    assert coord.device_available is True


def test_never_connected_is_unavailable() -> None:
    """Device is unavailable if MQTT was never connected."""
    coord = FakeCoordinatorSessionAvailability(disconnect_grace_seconds=180)
    coord.set_time(0)
    assert coord.device_available is False

    coord.set_time(1000)
    assert coord.device_available is False


def test_migration_removes_legacy_availability_timeout() -> None:
    """Migration from v1 to v2 removes availability_timeout option.

    Old entries stored availability_timeout (message-age based), which caused
    false unavailability. New logic uses MQTT session + grace period.
    """
    # Simulate old v1 options
    old_options = {
        "availability_timeout": 600,  # The problematic old option
    }

    # Migration logic (same as in __init__.py async_migrate_entry)
    new_options = dict(old_options)
    new_options.pop(const.LEGACY_AVAILABILITY_TIMEOUT, None)
    new_options[const.CONF_DISCONNECT_GRACE] = const.DEFAULT_DISCONNECT_GRACE_SECONDS

    # Verify migration result
    assert "availability_timeout" not in new_options
    assert new_options[const.CONF_DISCONNECT_GRACE] == 180


def test_migration_handles_workaround_timeout() -> None:
    """Migration handles entries with temporary workaround timeout (7200s)."""
    # User may have set availability_timeout to 7200 as a workaround
    old_options = {
        "availability_timeout": 7200,
    }

    new_options = dict(old_options)
    new_options.pop(const.LEGACY_AVAILABILITY_TIMEOUT, None)
    new_options[const.CONF_DISCONNECT_GRACE] = const.DEFAULT_DISCONNECT_GRACE_SECONDS

    # Verify migration replaces it with the new default
    assert "availability_timeout" not in new_options
    assert new_options[const.CONF_DISCONNECT_GRACE] == 180


def test_mqtt_keepalive_constant() -> None:
    """Verify MQTT keepalive is configured for quick disconnect detection.

    Reads the source file directly to avoid importing aiomqtt.
    """
    content = (PKG_DIR / "mqtt_client.py").read_text()
    assert "MQTT_KEEPALIVE_SECONDS = 15" in content
    assert "keepalive=MQTT_KEEPALIVE_SECONDS" in content


def test_options_flow_persists_values() -> None:
    """Options flow must persist submitted values, not wipe them.

    Bug fix: async_create_entry(data={}) was wiping options.
    The fix: async_create_entry(data={CONF_DISCONNECT_GRACE: grace}).

    This test verifies the config_flow.py code pattern without HA imports.
    """
    content = (PKG_DIR / "config_flow.py").read_text()

    # Verify options are returned via async_create_entry, not wiped
    assert "async_create_entry(" in content

    # The bug was: async_create_entry(title="", data={})
    # This pattern should NOT exist (empty data wipes options)
    import re

    # Look for the problematic pattern: async_create_entry with empty data={}
    # This regex matches async_create_entry(...data={}) or data = {}
    bad_pattern = r"async_create_entry\([^)]*data\s*=\s*\{\s*\}"
    bad_matches = re.findall(bad_pattern, content)
    assert len(bad_matches) == 0, (
        f"Found async_create_entry with empty data (wipes options): {bad_matches}"
    )

    # Verify the correct pattern exists: async_create_entry with CONF_DISCONNECT_GRACE
    good_pattern = r"async_create_entry\([^)]*data\s*=\s*\{[^}]*CONF_DISCONNECT_GRACE"
    assert re.search(good_pattern, content), (
        "Options flow should return async_create_entry(data={CONF_DISCONNECT_GRACE: ...})"
    )
