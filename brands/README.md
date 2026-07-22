# Brand assets — Zelia VP / Vigipool

Source image: [Jeedom market Vigipool icon](https://market.jeedom.com/filestore/market/plugin/images/vigipool_icon.png)  
(CCEI / Vigipool product artwork used for the community plugin icon.)

## Layout for Home Assistant

### Local (HA ≥ 2026.3)

Shipped with the integration:

```text
custom_components/zelia_vp/brand/
  icon.png
  logo.png
  icon@2x.png
  logo@2x.png
```

### Optional: home-assistant/brands

For older HA versions / CDN `brands.home-assistant.io`, open a PR to  
[home-assistant/brands](https://github.com/home-assistant/brands) under:

```text
custom_integrations/zelia_vp/
  icon.png
  logo.png
  icon@2x.png
  logo@2x.png
```

Copy files from this `brands/zelia_vp/` directory (already square 256 / 512 PNG).
