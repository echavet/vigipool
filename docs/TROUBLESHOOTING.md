# Dépannage

## L’intégration ne se connecte pas

- Vérifier l’IP de la Zelia (ping)
- Port **1883** ouvert depuis le host HA
- Device ID correct (`zelix_` + 12 hex, majuscules normalisées automatiquement)
- Dump rapide :
  ```bash
  mosquitto_sub -h <IP> -t '#' -v
  ```

## Entités *unavailable*

- Appareil éteint / hors Wi‑Fi
- Timeout d’availability trop court (Options → augmenter)
- Reconnect MQTT en cours (regarder les logs)

## Pas de production de chlore alors que le mode n’est pas Off

- Vérifier **Débit détecté** (`flow_on`) — sans débit, pas de production
- Température eau sous le seuil min d’arrêt
- Mode hiver activé
- Code erreur non nul (voir **E14** ci-dessous)

## Code E14 / 16384 — taux de sel trop élevé

Le registre MQTT `error` est un **masque de bits**. `16384` = bit 14 = **E14** dans l’app Vigipool (*Taux de sel trop élevé*).

- Capteur **Code erreur Vigipool** = `E14`
- Attribut `high_salt: true`
- Binary **Défaut** = on

Causes possibles :

1. Taux de sel réellement trop haut (vérifier avec un testeur indépendant ; idéal ~3 g/l à 25 °C)
2. **Faux positif** si la puissance MQTT est baissée trop bas (30–40 %) — le firmware lève E14 alors que le sel est correct. Remonter à ≥ 60–70 %, ou réduire la **durée théorique** plutôt que la puissance.

Les autres bits s’affichent `E{n}` sans libellé tant qu’ils n’ont pas été croisés avec l’app.

## Code S22 — température d'eau trop basse

Le registre MQTT `state` est un **masque de bits**. `Sn` = bit `n` (comme `En` pour `error`).

`2151677952` = `0x80400000` = bit 22 + bit 31. Le bit 22 est **S22** : *Température minimale de l'eau atteinte. Arrêt du traitement* (croisé le 2026-10-24 avec l'app, eau à 13,0 °C sous le seuil 15,0 °C, production arrêtée).

- Capteur **Statut Zelia** = `S22 : …`
- Attribut `raw` = la valeur brute (à garder : c'est elle qui permettra de confirmer un futur code)
- Événement `zelia_vp_status` quand le bit **change** (pas au démarrage, pas au simple reconnect)

Le bit 31 est souvent présent (`S31 (inconnu)`) y compris pendant une production normale. Ne pas le traiter comme un défaut tant qu'il n'a pas été croisé avec l'app.

## Mode / puissance ne changent pas

- Vérifier les logs HA (`zelia_vp`)
- Confirmer qu’un publish `…/desired` apparaît (outil MQTT)
- Certaines valeurs ne bougent qu’avec le débit / cycle filtration

## Après une mise à jour HACS

- Redémarrer Home Assistant
- Les `unique_id` sont stables : les entités ne doivent pas être recréées

## Diagnostics

Sur l’entrée d’intégration → **Télécharger les diagnostics**  
(le host est masqué ; les topics/valeurs MQTT sont inclus pour le support).
