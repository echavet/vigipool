"""Unit tests for topic building and value transforms (no Home Assistant required)."""

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


def test_parse_and_scale_from_live_capture() -> None:
    assert helpers.apply_scale(helpers.parse_numeric("285"), 0.1) == 28.5
    assert helpers.apply_scale(helpers.parse_numeric("150"), 0.1) == 15.0
    assert helpers.apply_scale(helpers.parse_numeric("32"), 0.1) == 3.2
    assert helpers.apply_scale(helpers.parse_numeric("650"), 1.0) == 650.0
    assert 15.0 * 10.0 == 150.0


def test_prod_state_map() -> None:
    assert helpers.prod_state_value(0) == "stopped"
    assert helpers.prod_state_value(1) == "requested"
    assert helpers.prod_state_value(2) == "running"
    assert helpers.prod_state_value(9) == "unknown_9"
    assert set(const.PROD_STATE_MAP) == {0, 1, 2}


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
