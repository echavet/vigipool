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
| Puissance | `u8_w/power_ely/info/*` | 0–100 / 1 | — |
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
| Erreur | `u32_r/error/info/reported` | bitmask brut | — |
| Code erreur Vigipool | `u32_r/error/info/reported` | bits → `En` | `none` / `E14` / `E2+E14` |
| Statut Zelia | `u32_r/state/info/reported` | bits → `Sn` | voir ci-dessous |
| Firmware | `u16_r/sw_vers/info/reported` | str | — |
| Type cellule | `u8_r/cell_type/value/reported` | — | — (désactivé par défaut) |
| Serveur (`server_on`) | `u8_r/server_on/info/reported` | brut 0/1 | diagnostic, désactivé |
| Modèle (`model_id`) | `u8_r/model_id/info/reported` | brut 0–255 | diagnostic, désactivé |
| Version matérielle | `u8_r/hw_vers/info/reported` | brut 0–255 | diagnostic, désactivé |
| Numéro de série | `s33_r/serial_num/info/reported` | hex, 1–32 car. | diagnostic, désactivé |
| Dureté de l'eau | `u8_w/water_hardness/info/reported` | brut 0–255, **lecture seule** | diagnostic, désactivé |
| Ajustement température | `i8_w/temp_adjust/info/reported` | brut −128–127, **lecture seule** | diagnostic, désactivé |

**prod_on (confirmé en conditions réelles) :**

| Code | État HA | Signification |
|------|---------|----------------|
| `0` | Arrêtée | Pas de production |
| `1` | En production | Polarité « avant » — production active (`prod_chlore`, courant, tension) |
| `2` | Inversion de polarité | Auto-nettoyage des électrodes ; **toujours de la production**. Alternance régulière **~2 h** avec le code `1` (observation terrain). |

Jeedom n’expose que 0/1 ; le CDC « Demandée / En cours » était incorrect.

Le binary sensor **Production active** reste `prod_on > 0` (codes 1 et 2).  
L’enum expose aussi l’attribut `prod_on_code` (et un capteur diagnostic dédié).

### Registre d’erreur (`u32_r/error`)

Masque 32 bits. **Code application Vigipool `En` = bit `n`.**

| Valeur MQTT | Bit | Code app | Signification | Confirmé |
|-------------|-----|----------|---------------|----------|
| `0` | — | `none` | Pas de défaut | oui |
| `16384` (`0x4000`) | 14 | **E14** | Courant trop fort / **taux de sel trop élevé** | **oui** (2026-08-16 : MQTT + notification app simultanée) |

Bits non listés : l’état affiche quand même `En` (ex. `E2`), attributs `labels` vides, `high_salt: false`.

Attributs (`error` et `error_e_codes`) :

| Attribut | Exemple (E14) |
|----------|----------------|
| `error_hex` | `0x4000` |
| `error_bits` | `[14]` |
| `e_codes` | `["E14"]` |
| `labels` | `["high_salt"]` |
| `high_salt` | `true` |

Le binary sensor **Défaut** est `on` dès que le registre ≠ 0.

**Note :** une puissance MQTT forcée trop basse (ex. 30–40 %) peut déclencher un **faux E14** (le firmware compare le courant à un seuil non proportionnel).

### Registre de statut (`u32_r/state`)

Masque 32 bits. **Code application Vigipool `Sn` = bit `n`**, comme `En` pour `error`.

Chemin vérifié dans `tests/fixtures/mqtt_zelix_sample.txt` (2026-07-22, même `zelix_8C4B14821190`) :

| Topic | Exemple |
|-------|---------|
| `u32_r/state/info/reported` | `2147483648` |
| `u32_r/state/value/reported` | `2147483648` |

Les deux qualificateurs portent le même entier dans cette capture. Le coordinator indexe par le nom de feuille (`state`) : la dernière valeur `reported` gagne. Le capteur décrit le topic `info`, comme `error`. Le diagnostic HA ne conserve pas le topic complet, seulement la feuille — la valeur du 2026-10-24 (`2151677952`) est donc celle qui a été stockée, quel que soit le qualificateur arrivé en dernier.

| Valeur MQTT | Bits | État affiché | Confirmé |
|-------------|------|--------------|----------|
| `0` | — | `aucun` (EN : `none`) | convention |
| `2151677952` (`0x80400000`) | 22 et 31 | **S22** : Température minimale de l'eau atteinte. Arrêt du traitement | **oui** pour le bit 22 (2026-10-24 : eau 13,0 °C < seuil 15,0 °C, `prod_on=0`, notification app « Code S22 ») |
| `2147483648` (`0x80000000`) | 31 | `S31 (inconnu)` | bit 31 **non** confirmé (présent aussi le 2026-07-22 alors que la production tournait) |

Le **code principal** (état du capteur) est le bit confirmé le plus bas s'il y en a un, sinon le bit le plus bas. Les autres codes restent dans les attributs. Un bit sans texte confirmé s'affiche `S{n} (inconnu)` (EN : `S{n} (unknown)`). La table de messages ne contient que des textes croisés avec l'app — aujourd'hui **S22** seulement. L'anglais est la traduction de la phrase française confirmée, pas une seconde capture.

Attributs (enregistrés avec l'historique du capteur, pour confirmer un futur code) :

| Attribut | Exemple (S22 + bit 31) |
|----------|------------------------|
| `raw` | `2151677952` |
| `hex` | `0x80400000` |
| `s_codes` | `["S22", "S31"]` |
| `messages` | `["S22 : Température minimale de l'eau atteinte. Arrêt du traitement", "S31 (inconnu)"]` |

Si un bit inconnu s'ajoute sans changer le code principal, l'état texte peut rester identique : `raw` / `s_codes` / `messages` changent et Home Assistant enregistre quand même la mise à jour.

#### Événement `zelia_vp_status`

Un événement par bit qui **passe** à 1 ou à 0 :

| Champ | Exemple |
|-------|---------|
| `device_id` | `zelix_8C4B14821190` |
| `code` | `S22` |
| `message` | `S22 : Température minimale de l'eau atteinte. Arrêt du traitement` |
| `active` | `true` (montée) ou `false` (descente) |
| `raw` | registre complet après le changement |

Pas d'événement parasite :

- Le **premier** échantillon valide du processus (démarrage, rechargement de l'entrée, message retenu à la souscription) fixe la référence et **n'émet rien**. Un S22 déjà actif est visible sur le capteur ; les automatisations qui ont besoin de l'état courant lisent le capteur, pas seulement l'événement.
- La déconnexion MQTT et le passage *unavailable* **ne remettent pas** la référence à zéro et ne synthétisent pas d'extinctions. Le contrôle périodique de disponibilité ne relit pas le registre.
- Une reconnexion qui rejoue **la même** valeur (message retenu, ou les deux qualificateurs `info` et `value`) n'émet rien.
- Une valeur **réellement différente** après la coupure émet les fronts manqués : ce sont de vrais changements, pas un replay.
- Un payload non entier, négatif ou hors `0 … 0xFFFFFFFF` est ignoré et ne déplace pas la référence.

Les codes `En` (`error`) ne sont pas concernés : aucun événement n'est ajouté sur ce registre.

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
| Défaut | `error` | > 0 |
