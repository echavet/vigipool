# Installation — Zelia VP

## Prérequis

- Home Assistant 2024.1 ou plus récent
- [HACS](https://hacs.xyz/) (recommandé)
- Zelia VP joignable en MQTT sur le LAN (port **1883**)
- Identifiant appareil : préfixe `zelix_` + 12 hex (visible dans l’app Vigipool ou via un dump MQTT)

## Via HACS

1. HACS → ⋮ → **Custom repositories**
2. Ajouter `https://github.com/echavet/vigipool` (type **Integration**)
3. Installer **Vigipool Zelia VP**
4. Redémarrer Home Assistant
5. **Paramètres → Appareils et services → Ajouter une intégration → Zelia VP**
6. Renseigner :
   - Host : IP de la Zelia
   - Port : `1883`
   - Device ID : `zelix_XXXXXXXXXXXX` (ou seulement les 12 hex)
   - Nom : libre

## Mise à jour

1. HACS indique *Update available* quand une [release GitHub](https://github.com/echavet/vigipool/releases) est publiée
2. Mettre à jour → redémarrer HA

## Multi-appareils

Répéter *Ajouter une intégration* pour chaque Zelia (host + device_id différents).

## Options

Sur l’entrée d’intégration → **Configurer** :

- Host / port / nom
- Délai d’indisponibilité (secondes sans message MQTT)

## Pare-feu / réseau

- Autoriser HA → Zelia TCP **1883**
- Même VLAN ou routage LAN ; ne **pas** exposer le broker sur Internet
