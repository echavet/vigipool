"""Unit tests for pure helpers and raw-store interpretation (no Home Assistant)."""

from __future__ import annotations

import importlib.util
import json
import re
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


# =============================================================================
# Vigipool S-codes (u32_r/state) — 2026.10.24
# =============================================================================

# HA diagnostics raw_store, zelix_8C4B14821190, 2026-10-24.
# state leaf only: the coordinator does not keep the full topic.
LIVE_STATE_2026_10_24 = 2151677952  # 0x80400000
LIVE_VALUE_TEMP = 130.0  # 13.0 °C
LIVE_TEMP_MIN_OFF = 150.0  # 15.0 °C
LIVE_PROD_ON = 0.0
# Same device, tests/fixtures/mqtt_zelix_sample.txt, 2026-07-22.
CAPTURE_STATE_2026_07_22 = 2147483648  # 0x80000000, bit 31 only
S22_FR = "Température minimale de l'eau atteinte. Arrêt du traitement"
S22_EN = "Minimum water temperature reached. Treatment stopped"
S22_STATE_FR = f"S22 : {S22_FR}"


def test_live_diag_state_is_s22_plus_bit_31() -> None:
    """The 2026-10-24 register matches bit 22 (S22) and unknown bit 31."""
    assert LIVE_STATE_2026_10_24 == 0x80400000
    assert LIVE_STATE_2026_10_24 == (1 << 22) | (1 << 31)
    assert const.STATUS_BIT_MIN_WATER_TEMP == 22
    # Production was off because water was under the stop threshold.
    assert helpers.apply_read_scale(LIVE_VALUE_TEMP, 0.1) == 13.0
    assert helpers.apply_read_scale(LIVE_TEMP_MIN_OFF, 0.1) == 15.0
    assert LIVE_VALUE_TEMP < LIVE_TEMP_MIN_OFF
    assert helpers.prod_state_from_raw(LIVE_PROD_ON) == "off"
    # July capture, while producing, is bit 31 alone — not S22.
    assert CAPTURE_STATE_2026_07_22 == 1 << 31
    assert helpers.status_u32(float(LIVE_STATE_2026_10_24)) == LIVE_STATE_2026_10_24


def test_fixture_confirms_state_topic_path() -> None:
    """Full topic is not in HA diagnostics; the MQTT capture has it.

    ``state`` is published twice (info and value) with the same payload.
    ``error`` is info-only. The integration keeps one leaf, like every
    other mqtt_name.
    """
    text = (ROOT / "tests" / "fixtures" / "mqtt_zelix_sample.txt").read_text()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    state_lines = [line for line in lines if "/state/" in line]
    assert state_lines == [
        "zelix_8C4B14821190/u32_r/state/info/reported 2147483648",
        "zelix_8C4B14821190/u32_r/state/value/reported 2147483648",
    ]
    assert "zelix_8C4B14821190/u32_r/error/info/reported 0" in lines
    # Leaf name the coordinator stores, for both qualifiers.
    for line in state_lines:
        parsed = helpers.parse_topic(line.split()[0])
        assert parsed is not None
        _device, mqtt_type, name, qualifier, direction = parsed
        assert mqtt_type == "u32_r"
        assert name == "state"
        assert direction == "reported"
        assert qualifier in {"info", "value"}


def test_status_catalog_confirms_only_s22() -> None:
    """Message table is the translation files, and only S22 is confirmed."""
    paths = {
        "fr": PKG_DIR / "translations" / "fr.json",
        "en": PKG_DIR / "translations" / "en.json",
        "strings": PKG_DIR / "strings.json",
    }
    catalogs = {name: json.loads(path.read_text()) for name, path in paths.items()}
    states = {
        name: data["entity"]["sensor"]["zelia_status"]["state"]
        for name, data in catalogs.items()
    }
    for state in states.values():
        s_keys = sorted(key for key in state if re.fullmatch(r"s\d+", key))
        assert s_keys == ["s22"]
        assert "S22" not in state["s22"]
    assert states["fr"]["none"] == "aucun"
    assert states["fr"]["unknown"] == "S{code} (inconnu)"
    assert states["fr"]["s22"] == S22_FR
    assert states["en"]["none"] == "none"
    assert states["en"]["unknown"] == "S{code} (unknown)"
    assert states["en"]["s22"] == S22_EN
    assert states["strings"] == states["en"]
    assert catalogs["fr"]["entity"]["sensor"]["zelia_status"]["name"] == "Statut Zelia"
    assert catalogs["en"]["entity"]["sensor"]["zelia_status"]["name"] == "Zelia status"

    fr = helpers.load_status_catalog("fr")
    en = helpers.load_status_catalog("en")
    assert helpers.load_status_catalog("fr-FR")["s22"] == S22_FR
    assert helpers.status_confirmed_bits(fr) == {22: S22_FR}
    assert helpers.status_confirmed_bits(en) == {22: S22_EN}
    # English fallback if a caller asks for another language.
    assert helpers.load_status_catalog("de")["s22"] == S22_EN


def test_status_state_and_attributes_live_value() -> None:
    fr = helpers.load_status_catalog("fr")
    state = helpers.status_state_from_raw(float(LIVE_STATE_2026_10_24), fr)
    assert state == S22_STATE_FR
    attrs = helpers.status_attributes_from_raw(float(LIVE_STATE_2026_10_24), fr)
    assert attrs == {
        "raw": LIVE_STATE_2026_10_24,
        "hex": "0x80400000",
        "s_codes": ["S22", "S31"],
        "messages": [S22_STATE_FR, "S31 (inconnu)"],
    }
    # Confirmed code stays the headline even when a lower unknown bit is set.
    mixed = (1 << 5) | (1 << 22)
    assert helpers.status_state_from_raw(mixed, fr) == S22_STATE_FR
    mixed_attrs = helpers.status_attributes_from_raw(mixed, fr)
    assert mixed_attrs is not None
    assert mixed_attrs["s_codes"] == ["S5", "S22"]
    assert mixed_attrs["messages"][0] == "S5 (inconnu)"
    # Bit 31 alone (July capture) is unknown, not "aucun".
    assert helpers.status_state_from_raw(CAPTURE_STATE_2026_07_22, fr) == "S31 (inconnu)"
    assert helpers.status_state_from_raw(0, fr) == "aucun"
    zero = helpers.status_attributes_from_raw(0, fr)
    assert zero == {"raw": 0, "hex": "0x0", "s_codes": [], "messages": []}
    en = helpers.load_status_catalog("en")
    assert helpers.status_state_from_raw(0, en) == "none"
    assert helpers.status_state_from_raw(1 << 22, en) == f"S22 : {S22_EN}"
    assert helpers.status_state_from_raw(1 << 7, en) == "S7 (unknown)"
    assert helpers.status_state_from_raw(None, fr) is None
    assert helpers.status_attributes_from_raw(None, fr) is None
    # Strict register: no silent truncation, no sign wrap (unlike error).
    assert helpers.status_u32(1.5) is None
    assert helpers.status_u32(-1) is None
    assert helpers.status_u32(float("nan")) is None
    assert helpers.status_u32(0x1_0000_0000) is None


def test_status_events_skip_baseline_replay_and_invalid() -> None:
    """No events on startup, identical replay, or unavailable-style gaps.

    A real edge after the baseline still emits one payload per flipped bit.
    """
    catalog = helpers.load_status_catalog("fr")
    device = "zelix_8C4B14821190"
    tracker = helpers.StatusEdgeTracker()

    # Startup / retained snapshot, including S22 already active: silence.
    assert tracker.observe(float(LIVE_STATE_2026_10_24), catalog, device) == []
    assert tracker.raw == LIVE_STATE_2026_10_24

    # Reconnect replay and the duplicate info/value topic: silence.
    assert tracker.observe(LIVE_STATE_2026_10_24, catalog, device) == []
    assert tracker.observe(float(LIVE_STATE_2026_10_24), catalog, device) == []

    # Invalid payloads must not clear the baseline (would fake falling edges).
    assert tracker.observe(None, catalog, device) == []
    assert tracker.observe(1.5, catalog, device) == []
    assert tracker.observe(-1, catalog, device) == []
    assert tracker.raw == LIVE_STATE_2026_10_24

    # S22 clears, bit 31 stays. One falling edge, not a startup burst.
    cleared = tracker.observe(CAPTURE_STATE_2026_07_22, catalog, device)
    assert cleared == [
        {
            "device_id": device,
            "code": "S22",
            "message": S22_STATE_FR,
            "active": False,
            "raw": CAPTURE_STATE_2026_07_22,
        }
    ]

    # Gap with no sample (disconnect / unavailable) does not move the tracker.
    assert tracker.raw == CAPTURE_STATE_2026_07_22
    assert tracker.observe(CAPTURE_STATE_2026_07_22, catalog, device) == []

    # Real rising edges after that, lowest bit first.
    risen = tracker.observe((1 << 5) | (1 << 22) | (1 << 31), catalog, device)
    assert [item["code"] for item in risen] == ["S5", "S22"]
    assert [item["active"] for item in risen] == [True, True]
    assert risen[1]["message"] == S22_STATE_FR
    assert risen[0]["message"] == "S5 (inconnu)"
    assert all(item["raw"] == (1 << 5) | (1 << 22) | (1 << 31) for item in risen)


def test_status_edge_source_ignores_availability_and_reconnect() -> None:
    """The coordinator must not reset or emit from availability / MQTT session."""
    source = (PKG_DIR / "coordinator.py").read_text()

    def body(name: str, nxt: str) -> str:
        start = source.index(f"def {name}")
        end = source.index(f"def {nxt}", start)
        return source[start:end]

    availability = body("_check_availability", "_handle_connection_change")
    connection = body("_handle_connection_change", "get_raw")
    handle = body("_handle_message", "_emit_status_edges")
    assert "self._status_edges" not in availability
    assert "self._status_edges" not in connection
    assert 'mqtt_name == "state"' in handle
    assert "raw_num is not None" in handle
    assert "EVENT_ZELIA_STATUS" in source
    assert "StatusEdgeTracker" in source


def test_diagnostic_leaves_are_read_only_and_disabled() -> None:
    """Unmapped leaves are disabled diagnostic sensors and cannot be published."""
    content = (PKG_DIR / "models.py").read_text()

    def block(key: str) -> str:
        start = content.index(f'key="{key}"')
        end = content.find("ZeliaSensorEntityDescription(", start + 1)
        if end == -1:
            end = content.find("BINARY_SENSOR_DESCRIPTIONS", start)
        return content[start:end]

    status = block("zelia_status")
    assert 'mqtt_type="u32_r"' in status
    assert 'mqtt_name="state"' in status
    assert 'qualifier="info"' in status
    assert 'value_kind="status_s"' in status
    assert "entity_registry_enabled_default=False" not in status

    expected = {
        "server_on": ('mqtt_type="u8_r"', "int_min=SERVER_ON_RANGE[0]"),
        "model_id": ('mqtt_type="u8_r"', "int_min=MODEL_ID_RANGE[0]"),
        "hw_vers": ('mqtt_type="u8_r"', "int_min=HW_VERS_RANGE[0]"),
        "serial_num": ('mqtt_type="s33_r"', 'value_kind="serial"'),
        "water_hardness": ('mqtt_type="u8_w"', "int_min=WATER_HARDNESS_RANGE[0]"),
        "temp_adjust": ('mqtt_type="i8_w"', "int_min=TEMP_ADJUST_RANGE[0]"),
    }
    for key, snippets in expected.items():
        chunk = block(key)
        assert "entity_registry_enabled_default=False" in chunk
        assert "EntityCategory.DIAGNOSTIC" in chunk
        for snippet in snippets:
            assert snippet in chunk, f"{key} missing {snippet}"

    writable = content[content.index("WRITABLE_DESCRIPTIONS") :]
    assert "SENSOR_DESCRIPTIONS" not in writable
    assert "*NUMBER_DESCRIPTIONS, *SWITCH_DESCRIPTIONS, *SELECT_DESCRIPTIONS" in writable


def test_diagnostic_leaf_sanity_checks() -> None:
    """Out-of-range or non-integer leaves stay unknown; live values pass."""
    assert helpers.bounded_int(1, *const.SERVER_ON_RANGE) == 1
    assert helpers.bounded_int(0, *const.SERVER_ON_RANGE) == 0
    assert helpers.bounded_int(2, *const.SERVER_ON_RANGE) is None
    assert helpers.bounded_int(1.5, *const.SERVER_ON_RANGE) is None
    assert helpers.bounded_int(6, *const.MODEL_ID_RANGE) == 6
    assert helpers.bounded_int(256, *const.MODEL_ID_RANGE) is None
    assert helpers.bounded_int(1, *const.HW_VERS_RANGE) == 1
    assert helpers.bounded_int(3, *const.WATER_HARDNESS_RANGE) == 3
    assert helpers.bounded_int(-1, *const.WATER_HARDNESS_RANGE) is None
    assert helpers.bounded_int(5, *const.TEMP_ADJUST_RANGE) == 5
    assert helpers.bounded_int(-1, *const.TEMP_ADJUST_RANGE) == -1
    assert helpers.bounded_int(128, *const.TEMP_ADJUST_RANGE) is None
    assert helpers.bounded_int(-129, *const.TEMP_ADJUST_RANGE) is None
    assert helpers.bounded_int(float("nan"), *const.TEMP_ADJUST_RANGE) is None
    serial = "060101000000000000008C4B14821190"
    assert helpers.serial_from_raw(serial) == serial
    assert helpers.serial_from_raw(f"  {serial}  ") == serial
    assert helpers.serial_from_raw("") is None
    assert helpers.serial_from_raw(" ") is None
    assert helpers.serial_from_raw("ZZ") is None
    assert helpers.serial_from_raw("A" * 33) is None
    # A numeric store would mean the hex was lost; do not display it.
    assert helpers.serial_from_raw(6010100000000000000) is None


def test_manifest_calver_matches_changelog() -> None:
    manifest = json.loads((PKG_DIR / "manifest.json").read_text())
    assert manifest["version"] == "2026.10.24"
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "## [2026.10.24] - 2026-10-24" in changelog
