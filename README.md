# Vigipool Zelia VP — Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Intégration Home Assistant pour l’électrolyseur de sel **CCEI Zelia VP** (univers Vigipool).

- Connexion **MQTT directe** au broker embarqué de l’appareil (pas besoin de bridge Mosquitto)
- **Config Flow** UI, multi-appareils
- Modes Off / Programmé / Auto / Régulé / Choc
- Lecture + commande (puissance, durée, température min, ORP…)
- Distribution **HACS** avec versions et mises à jour
- Versionnement **CalVer** `YYYY.M.D` (ex. `2026.7.22`), lisible et aligné avec l’esprit HA

## Installation (HACS — recommandé)

1. Installer [HACS](https://hacs.xyz/) si ce n’est pas déjà fait.
2. HACS → **⋮** → *Custom repositories*
3. URL : `https://github.com/echavet/vigipool`  
   Catégorie : **Integration**
4. HACS → Integrations → rechercher **Vigipool Zelia VP** → Download
5. **Redémarrer** Home Assistant
6. *Paramètres → Appareils et services → Ajouter une intégration* → **Zelia VP**

### Mise à jour

HACS notifie les nouvelles versions (tags / GitHub Releases au format `YYYY.M.D`).  
Update en un clic → redémarrer HA.

Si la MàJ n’apparaît pas : HACS → ⋮ → *Reload*, ou réinstaller depuis le custom repository.

## Installation manuelle

1. Copier `custom_components/zelia_vp` dans le dossier `config/custom_components/` de Home Assistant
2. Redémarrer HA
3. Ajouter l’intégration **Zelia VP**

## Configuration

| Champ | Description | Exemple |
|-------|-------------|---------|
| Host | IP / hostname de la Zelia | `192.168.8.162` |
| Port | Port MQTT | `1883` |
| Device ID | Préfixe MQTT | `zelix_8C4B14821190` |
| Name | Nom affiché | `Zelia VP` |

IP fixe (DHCP reservation) recommandée.  
Pas d’authentification MQTT sur le firmware observé.

## Entités principales

| Type | Entités |
|------|---------|
| Select | Mode électrolyse (Arrêt / Programmé / Auto / Régulé) |
| Switch | Mode hiver, Mode choc |
| Number | Puissance, durée théorique, durée choc, temp. min arrêt, consigne ORP |
| Sensor | Temp. eau, prod. chlore, état production, conductivité, diag. |
| Binary | Production active, débit, couvercle |

Détails : [docs/ENTITIES.md](docs/ENTITIES.md)

## Notes fonctionnelles

- La production ne se fait que s’il y a du **débit** (`flow_on`).
- La durée théorique est un **budget journalier** d’heures d’équivalent pleine puissance.
- L’**inversion de polarité** est gérée en interne par la Zelia — jamais pilotée par cette intégration.
- Mode **Choc** : production forcée (puissance jusqu’à 125 % côté appareil).

## Développement

```bash
# Tests unitaires (helpers, pas besoin de HA complet)
python -m pytest tests/ -q
```

## Licence

MIT — voir [LICENSE](LICENSE).

Protocole MQTT Vigipool documenté à partir de captures locales et de plugins CCEI publics (Jeedom / templates).  
Code original ; pas une copie des sources CCEI.
