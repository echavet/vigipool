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
- Code erreur non nul

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
