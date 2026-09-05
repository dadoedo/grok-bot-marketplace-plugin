# Site assets

**Catalog avatars win.** Hero/grid faces come from `catalog.json` `imageUrl` values (Grok Bot marketplace S3), clipped to `shape` and tinted with `color`. Do not overlay generated stock characters on that grid.

The squircle **XBots** mark (`brand-icon.png`) is secondary brand art only (favicon / header).

| Filename | Size | Use |
| --- | --- | --- |
| `brand-icon.png` | square | Header / favicon (shipped, placeholder brand) |
| `mark.svg` | square | Legacy SVG mark |
| `favicon.svg` | 32×32 | Fallback favicon |
| **`og.png`** | **1200×630 PNG** | Social share when ready; until then `og:image` uses `brand-icon.png` |
| `hero.png` | 1600×900 | Optional atmosphere only — must not replace catalog cards |
| `hero-slot.svg` / `og-slot.svg` | — | Old slots; ignore if they fight marketplace visuals |

