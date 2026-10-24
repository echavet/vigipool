# Capture MQTT live

Date : 2026-07-22  
Broker : `192.168.8.162:1883` (sans auth)  
Device : `zelix_8C4B14821190`

Voir aussi `tests/fixtures/mqtt_zelix_sample.txt`.

## Exemples de valeurs

| Topic | Exemple | Signification |
|-------|---------|----------------|
| `…/u16_r/value_temp/value/reported` | `285` | 28,5 °C |
| `…/u16_w/temp_min_off_ely/info/reported` | `150` | 15,0 °C |
| `…/u16_r/current_ely/value/reported` | `32` | 3,2 A |
| `…/u16_w/consigne_orp/info/reported` | `650` | 650 mV |
| `…/u8_w/mode_ely/info/reported` | `2` | Auto |
| `…/u8_r/prod_on/value/reported` | `0`, `1` ou `2` | 0=arrêt, 1=prod. polarité N, 2=inversion (~2 h d’alternance avec 1) |
| `…/u32_r/state/info/reported` | `2147483648` | bitmask statut (`Sn` = bit `n`) ; ici bit 31 seul |
| `…/u32_r/state/value/reported` | `2147483648` | même entier que `info` dans cette capture |
| `…/u8_r/server_on/info/reported` | `1` | brut, sens non confirmé |
| `…/u8_r/model_id/info/reported` | `6` | brut |
| `…/u8_r/hw_vers/info/reported` | `1` | brut |
| `…/s33_r/serial_num/info/reported` | `0601…1190` | hex |
| `…/u8_w/water_hardness/info/reported` | `3` | brut, lecture seule côté HA |
| `…/i8_w/temp_adjust/info/reported` | `0` | brut i8, lecture seule côté HA |
