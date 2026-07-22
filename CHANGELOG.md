# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-22

### Added

- Initial HACS custom integration for CCEI **Zelia VP** (`zelix_*`).
- Direct MQTT connection to the device broker (no HA MQTT bridge required).
- Config Flow + Options Flow (host, port, device_id, name, availability timeout).
- Multi-device support (one config entry per device).
- Sensors: water temperature, chlorine production, voltage/current, durations, conductivity, production state, diagnostics (RSSI, error, firmware, cell type, internal temp).
- Binary sensors: production active, flow, cover.
- Numbers: power, theoretical duration, shock duration, min temperature stop (×10), ORP setpoint.
- Switches: winter mode, shock mode.
- Select: electrolysis mode (Off / Programmed / Auto / Regulated).
- French and English translations.
- Diagnostics dump for troubleshooting.
- Unit tests for MQTT transforms and device_id normalization.

[0.1.0]: https://github.com/echavet/vigipool/releases/tag/v0.1.0
