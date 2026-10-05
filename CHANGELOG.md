# Changelog

All notable changes to this project will be documented in this file.

Versioning follows **CalVer** `YYYY.M.D` (date-based, same spirit as Home Assistant Core), e.g. `2026.8.16`.

## [2026.10.5] - 2026-10-05

### Fixed

- **Faux « unavailable » des entités en lecture seule** (flow, production, capteurs…) corrigé.
  - **Cause racine** : la disponibilité était basée sur l'âge du dernier message MQTT avec un timeout de 600 s stocké dans les options. Or le device Zelia ne publie qu'à chaque changement + re-publish périodique (~915 s pompe ON, ~3610 s pompe OFF). Résultat : 5–10 min d'indisponibilité par cycle, ~45 % du temps sur 24 h.
  - **Nouvelle logique** : disponibilité liée à la **session MQTT** (keepalive 15 s) + **grace period** après déconnexion (180 s par défaut, configurable 30–600 s). Les entités restent disponibles tant que le broker répond, même si le device est silencieux pendant des heures.
  - **Migration automatique** : les entrées existantes (V1, option `availability_timeout`) sont migrées vers V2 (`disconnect_grace_seconds`). Aucune action utilisateur requise.

- **Options flow écrasait les options** : `async_create_entry(data={})` dans l'options flow effaçait les options de l'entrée. Corrigé : les options soumises sont maintenant correctement persistées.

### Added

- **Capteur diagnostique MQTT connecté** (`binary_sensor.mqtt_connected`) : indique l'état de la connexion au broker embarqué, toujours disponible (même hors ligne).
- **Capteur diagnostique Dernière communication** (`sensor.last_seen`) : timestamp UTC du dernier message MQTT, avec attribut `age_seconds`.
- Tests unitaires couvrant : silence > ancien timeout conserve available, déconnexion → unavailable après grace, reconnexion restaure, migration V1→V2.

### Changed

- Intervalle du timer de vérification de disponibilité réduit de 60 s à 10 s pour une détection plus réactive.
- Option de configuration renommée : `availability_timeout` → `disconnect_grace_seconds` (plage 30–600 s).

## [2026.10.2] - 2026-10-02

### Fixed

- **Bug critique : les commandes `number.set_value` étaient silencieusement ignorées** (entités « indisponibles »).
  - **Cause** : le timeout de disponibilité par défaut (600 s) était trop court ; le Zelia VP n'envoie qu'environ toutes les ~915 s au repos, provoquant 5 min d'indisponibilité à chaque cycle.
  - **Correction** : timeout par défaut porté à **1800 s** (30 min). Plage configurable étendue à 60–7200 s.
  - Ajout d'un **timer périodique (60 s)** qui met à jour l'état des entités quand la disponibilité change, permettant d'afficher réellement « indisponible » dans l'UI.
  - Les **entités inscriptibles** (number, switch, select) restent désormais disponibles tant que le client MQTT est connecté, même si l'appareil est silencieux — les commandes peuvent toujours être publiées.
  - Les erreurs de publication MQTT sont maintenant loguées en **warning** au lieu de debug.

- **Pas de puissance trop grossier** : `power_ely` (puissance de production) accepte désormais n'importe quel entier 0–100 (`native_step=1`), au lieu de pas de 5. L'appli officielle permet ex. 76 %.
  - Arrondi automatique à l'entier le plus proche pour les registres u8 avant publication.

### Changed

- Documentation ENTITIES.md mise à jour pour refléter le nouveau pas (0–100 / 1).

## [2026.8.16] - 2026-08-16

### Added

- **Error bitmask decoding** for `u32_r/error` (Vigipool app `En` = bit `n`).
  - Field-confirmed: **16384 (`1<<14`) = E14** — *Taux de sel trop élevé* / high current / too much salt (MQTT + app notification, same night as a 40 % power reduction).
  - Sensor **Code erreur Vigipool** (`error_e_codes`): state `none`, `E14`, or `E2+E14` if several bits are set.
  - Attributes on both error sensors: `error_hex`, `error_bits`, `e_codes`, `labels`, `high_salt`.
  - Binary sensor **Défaut** (`fault`, device class `problem`) when the register is non-zero.
  - Raw numeric **Code erreur** unchanged for existing automations.

### Notes

- Other bits are exposed as `En` without a label until independently confirmed.
- E14 can fire as a **false positive** when production power is forced well below ~60 % (current vs expected not scaled in firmware).

## [2026.7.25] - 2026-07-24

### Changed

- **`ely_duration_compensated`** enabled by default (was diagnostic/disabled): target thermoregulated production duration in minutes — useful to detect when the cell should be producing.
- Rename FR/EN labels: current vs target production duration.
- **`couv_on`**: label corrected from “couvercle” to **couverture de piscine** (pool cover/blanket).
- Docs: side power switch **100% / 25% / EXT** explained from official Zelia manual (EXT = external cover dry-contact detection).

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

[2026.10.5]: https://github.com/echavet/vigipool/releases/tag/2026.10.5
[2026.10.2]: https://github.com/echavet/vigipool/releases/tag/2026.10.2
[2026.8.16]: https://github.com/echavet/vigipool/releases/tag/2026.8.16
[2026.7.25]: https://github.com/echavet/vigipool/releases/tag/2026.7.25
[2026.7.24]: https://github.com/echavet/vigipool/releases/tag/2026.7.24
[2026.7.23]: https://github.com/echavet/vigipool/releases/tag/2026.7.23
[2026.7.22]: https://github.com/echavet/vigipool/releases/tag/2026.7.22
[0.2.1]: https://github.com/echavet/vigipool/releases/tag/v0.2.1
[0.2.0]: https://github.com/echavet/vigipool/releases/tag/v0.2.0
[0.1.0]: https://github.com/echavet/vigipool/releases/tag/v0.1.0
