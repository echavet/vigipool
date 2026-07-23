# Changelog

All notable changes to this project will be documented in this file.

Versioning follows **CalVer** `YYYY.M.D` (date-based, same spirit as Home Assistant Core), e.g. `2026.7.24`.

## [2026.7.24] - 2026-07-23

### Changed

- **`prod_on` value 2 confirmed as polarity reverse** after ~24 h field use: regular alternation **~2 h** between codes `1` (forward production) and `2` (reverse / electrode self-clean). Labels and docs no longer mark this as a hypothesis.

## [2026.7.23] - 2026-07-22

### Added

- **Brand logo / icon** from the official-looking Jeedom market Vigipool artwork  
  ([vigipool_icon.png](https://market.jeedom.com/filestore/market/plugin/images/vigipool_icon.png)).
- Local HA brand assets (`custom_components/zelia_vp/brand/`) for Home Assistant **2026.3+**.
- Square 256×256 and 512×512 PNG exports in `brands/zelia_vp/` for optional [home-assistant/brands](https://github.com/home-assistant/brands) PR.

## [2026.7.22] - 2026-07-22

### Changed

- Switch release numbering from semver (`0.x.y`) to **CalVer `YYYY.M.D`** for clearer, date-based versions in HACS / HA.

### Notes

- Functionally equivalent to **0.2.1** (prod_on mapping fix included):
  - `prod_on`: `0=off`, `1=on` (producing), `2=reverse` (polarity reverse; later field-confirmed)
  - Diagnostic sensor + attribute for raw `prod_on` code
  - Raw MQTT store architecture from 0.2.0

## [0.2.1] - 2026-07-22

### Fixed

- **Production state (`prod_on`)** mapping was wrong (CDC “0/1/2 = Arrêtée/Demandée/En cours”).
  - Live check: `prod_on=1` with `prod_chlore=19` and cell current → **producing**, not “requested”.
  - Jeedom only maps `0=stopped`, `1=on` (never “requested”).
  - New mapping: `0=off`, `1=on`, `2=reverse` (polarity reverse / self-clean; field-confirmed in 2026.7.24).
- Added diagnostic sensor **Production code** (`prod_on` raw 0/1/2) and attribute `prod_on_code` on the state enum.
- Binary **Production active** unchanged (`prod_on > 0`).

## [0.2.0] - 2026-07-22

### Changed

- **Architecture refactor** (behavior-preserving, clearer design):
  - Coordinator stores **raw MQTT values only** (`mqtt_name → number|str`).
  - Entities apply scale / maps / binary logic from declarative descriptions.
  - Single writable registry derived from descriptions.
  - MQTT client lifecycle simplified.
  - Availability = last message within timeout.
  - Options flow relies on config entry update listener.
  - Mode change publishes `mode_choc=0` first, then `mode_ely`.
- Unknown `prod_on` values map to `None` (enum stays strict).

### Removed

- Dual semantic/raw store and special-case parse fan-out in the coordinator.
- Dead entity firmware no-op and identity `value_fn` helpers.

## [0.1.0] - 2026-07-22

### Added

- Initial HACS custom integration for CCEI **Zelia VP** (`zelix_*`).
- Direct MQTT connection to the device broker.
- Config Flow + Options Flow, multi-device support.
- Sensors, binary sensors, numbers, switches, select (electrolysis mode).
- French and English translations, diagnostics, unit tests.

[2026.7.24]: https://github.com/echavet/vigipool/releases/tag/2026.7.24
[2026.7.23]: https://github.com/echavet/vigipool/releases/tag/2026.7.23
[2026.7.22]: https://github.com/echavet/vigipool/releases/tag/2026.7.22
[0.2.1]: https://github.com/echavet/vigipool/releases/tag/v0.2.1
[0.2.0]: https://github.com/echavet/vigipool/releases/tag/v0.2.0
[0.1.0]: https://github.com/echavet/vigipool/releases/tag/v0.1.0
