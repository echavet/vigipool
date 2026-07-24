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
| Durée production actuelle | `u16_r/ely_duration_in_minut/value/reported` | — | min (déjà produit / en cours) |
| Durée production cible (thermorégulée) | `u16_r/ely_duration_compensated/value/reported` | — | min (objectif journalier après compensation temp., ex. 1482 ≈ 24 h 42) |
| Conductivité | `u16_r/value_cond/value/reported` | — | mS/cm |
| Temp. interne | `u16_r/value_temp_int/value/reported` | ÷10 | °C |
| État production | `u8_r/prod_on/value/reported` | 0→off, 1→on, 2→reverse | enum |
| Code production | `u8_r/prod_on/value/reported` | brut 0/1/2 | diagnostic |
| RSSI | `i8_r/rssi/info/reported` | — | dBm |
| Erreur | `u32_r/error/info/reported` | — | — |
| Firmware | `u16_r/sw_vers/info/reported` | str | — |
| Type cellule | `u8_r/cell_type/value/reported` | — | — |

**prod_on (confirmé en conditions réelles) :**

| Code | État HA | Signification |
|------|---------|----------------|
| `0` | Arrêtée | Pas de production |
| `1` | En production | Polarité « avant » — production active (`prod_chlore`, courant, tension) |
| `2` | Inversion de polarité | Auto-nettoyage des électrodes ; **toujours de la production**. Alternance régulière **~2 h** avec le code `1` (observation terrain). |

Jeedom n’expose que 0/1 ; le CDC « Demandée / En cours » était incorrect.

Le binary sensor **Production active** reste `prod_on > 0` (codes 1 et 2).  
L’enum expose aussi l’attribut `prod_on_code` (et un capteur diagnostic dédié).

### Durées d’électrolyse

| Capteur | Sens |
|---------|------|
| **Durée de production actuelle** (`ely_duration_in_minut`) | Temps d’électrolyse déjà réalisé / en cours (minutes) |
| **Durée de production cible** (`ely_duration_compensated`) | Objectif journalier **thermorégulé** en minutes (durée théorique modulée par la température de l’eau). Utile pour détecter une cellule qui **devrait** produire mais ne le fait pas (ex. comparer avec production actuelle, `flow_on`, `prod_on`, mode). |
| **Durée théorique** (number, heures) | Consigne utilisateur 1–24 h avant compensation température |

### Interrupteur latéral du boîtier d’alimentation (doc Zelia)

| Position | Signification |
|----------|----------------|
| **100 %** | Production nominale **forcée** — ignore l’état couverture / contact volet |
| **25 %** | Production réduite à **1/4** (mode couverture manuel) — ignore aussi le contact si présent |
| **EXT** | **Externe** : lit le **contact sec de couverture automatique** (et/ou asservissement RedOx en mode PA). Le coffret détecte alors volet fermé/ouvert pour réduire ou non la production. |

Sans contact câblé, on peut simuler « bassin couvert » en mettant **25 %**, puis repasser manuellement en **100 %**.

## Binary sensors

| Entité | Topic | On si |
|--------|-------|-------|
| Production active | `prod_on` | > 0 |
| Débit | `flow_on` | == 1 |
| Couverture de piscine | `couv_on` | == 1 (bassin couvert) |
