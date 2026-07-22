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
