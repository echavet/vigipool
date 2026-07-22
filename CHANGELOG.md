# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-22

### Changed

- **Architecture refactor** (behavior-preserving, clearer design):
  - Coordinator stores **raw MQTT values only** (`mqtt_name → number|str`).
  - Entities apply scale / maps / binary logic from declarative descriptions.
  - Single writable registry derived from descriptions (no hand-maintained key list).
  - MQTT client lifecycle simplified (context manager owns disconnect; same event loop).
  - Availability = last message within timeout (no permanent “available with empty state”).
  - Options flow relies on config entry update listener (no double reload).
  - Mode change publishes `mode_choc=0` first, then `mode_ely`.
- Unknown `prod_on` values map to `None` (valid enum options only).

### Removed

- Dual semantic/raw store and special-case parse fan-out in the coordinator.
- Dead entity firmware no-op and identity `value_fn` helpers.

## [0.1.0] - 2026-07-22

### Added

- Initial HACS custom integration for CCEI **Zelia VP** (`zelix_*`).
- Direct MQTT connection to the device broker (no HA MQTT bridge required).
- Config Flow + Options Flow (host, port, device_id, name, availability timeout).
- Multi-device support (one config entry per device).
- Sensors, binary sensors, numbers, switches, select (electrolysis mode).
- French and English translations.
- Diagnostics dump for troubleshooting.
- Unit tests for MQTT transforms and device_id normalization.

[0.2.0]: https://github.com/echavet/vigipool/releases/tag/v0.2.0
[0.1.0]: https://github.com/echavet/vigipool/releases/tag/v0.1.0
