# Entités — Zelia VP

Préfixe MQTT : `{device_id}/…` (ex. `zelix_8C4B14821190`)

## Select

| Entité | Topic | Valeurs |
|--------|-------|---------|
| Mode électrolyse | `u8_w/mode_ely/info/*` | 0 Off, 1 Programmé, 2 Auto, 3 Régulé |

Écriture d’un mode « normal » : publie aussi `mode_choc=0`.

## Switches

| Entité | Topic |
|--------|-------|
| Mode hiver | `u8_w/winter_mode/info/*` |
| Mode choc | `u8_w/mode_choc/info/*` |

## Numbers

| Entité | Topic | Plage | Transform |
|---------|-------|-------|-----------|
| Puissance | `u8_w/power_ely/info/*` | 0–100 / 5 | — |
| Durée théorique | `u8_w/ely_duration_theo/info/*` | 1–24 h | — |
| Durée choc | `u8_w/choc_duration/info/*` | 1–24 | — |
| Temp. min arrêt | `u16_w/temp_min_off_ely/info/*` | 10–25 °C / 0.5 | read ÷10, write ×10 |
| Consigne ORP | `u16_w/consigne_orp/info/*` | 500–800 mV / 10 | — (disabled by default) |

## Sensors

| Entité | Topic | Transform | Unité |
|---------|-------|-----------|-------|
| Température eau | `u16_r/value_temp/value/reported` | ÷10 | °C |
| Production chlore | `u8_r/prod_chlore/value/reported` | — | g/h |
| Tension | `u16_r/voltage_ely/value/reported` | — | V |
| Courant | `u16_r/current_ely/value/reported` | ÷10 | A |
| Durée production | `u16_r/ely_duration_in_minut/value/reported` | — | min |
| Durée compensée | `u16_r/ely_duration_compensated/value/reported` | — | min |
| Conductivité | `u16_r/value_cond/value/reported` | — | mS/cm |
| Temp. interne | `u16_r/value_temp_int/value/reported` | ÷10 | °C |
| État production | `u8_r/prod_on/value/reported` | 0→off, 1→on, 2→reverse* | enum |
| Code production | `u8_r/prod_on/value/reported` | brut 0/1/2 | diagnostic |
| RSSI | `i8_r/rssi/info/reported` | — | dBm |
| Erreur | `u32_r/error/info/reported` | — | — |
| Firmware | `u16_r/sw_vers/info/reported` | str | — |
| Type cellule | `u8_r/cell_type/value/reported` | — | — |

**prod_on (corrigé vs CDC initial) :**

| Code | État HA | Signification |
|------|---------|----------------|
| `0` | Arrêtée | Pas de production (Jeedom + captures) |
| `1` | En production | Production active — confirmé live (`prod_chlore` / courant / tension non nuls) |
| `2` | Inversion de polarité | Production électrique aussi observée ; **hypothèse** cycle d’auto-nettoyage des électrodes (non documenté CCEI). Jeedom n’expose que 0/1. |

Le binary sensor **Production active** reste `prod_on > 0`.  
L’enum expose aussi l’attribut `prod_on_code` (et un capteur diagnostic dédié).

## Binary sensors

| Entité | Topic | On si |
|--------|-------|-------|
| Production active | `prod_on` | > 0 |
| Débit | `flow_on` | == 1 |
| Couvercle | `couv_on` | == 1 |
