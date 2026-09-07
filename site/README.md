# Landing site (`site/`)

Static marketing page for the **Grok Bot Marketplace Plugin**.

Working title **XBots** / **grokbots.store** is temporary (`xbots.io` is taken — do not claim it). Swap-friendly: search `data-brand`, `.brand-name`, `.brand-domain` in `index.html` / `styles.css`. Copy bank: [`marketing-copy.md`](marketing-copy.md).

This is a discovery Open Plugin landing page — **not** an installer and **not** an official x.ai product.

## Visual system (mirrors Grok Bot marketplace)

Do **not** restyle this as generic neon SaaS. Chrome and cards follow [the public marketplace](https://x.ai/bot/marketplace):

- Ivory page, jet type (Inter), category chips, an **Add** control
- Hero is a **live catalog gallery** (not `hero.png`). Featured tiles come from `catalog.json`
- Bot cards use real catalog fields: `name`, `creatorName`, `summary`, `color`, `shape`, `imageUrl` (S3 creator assets on `grok-bot-marketplace-public-assets.s3.amazonaws.com`)
- Avatars are clipped with CSS `mask-image` + SVG shapes in `assets/shapes/` (`squircle`, `hex`, `pebble`, `teardrop`, `blob`, `tablet`, `cloud`, `wedge`, `dome`, `crystal`, `capsule`, …)
- Color fields use x.ai brand-200 hues (`green`, `violet`, `magenta`, `orange`, `blue`, `cyan`, `gray`, `red`, `black`, `brown`, `yellow`)
- **Do not invent faces.** Catalog `imageUrl` only
- Add points at `addHref` (`grokbot://…`) and the name/portrait at `marketplaceUrl`

Data: `site/catalog.json` (slim copy of `data/catalog.json`). Refresh with:

```bash
python3 scripts/sync-site-catalog.py
```

The page also tries `../data/catalog.json` if you serve the **repo root**.

## Preview locally

```bash
python3 scripts/sync-site-catalog.py
python3 -m http.server 8080 --directory site
```

Open http://127.0.0.1:8080/

No build step. Vanilla HTML + CSS + `app.js`.

## GitHub Pages

GitHub’s **Deploy from a branch** UI only offers `/` or `/docs` — not `/site`. Use Actions (`.github/workflows/pages.yml`):

1. **Settings → Pages → Source: GitHub Actions**
2. Merge to `main` (or **workflow_dispatch**)
3. The workflow runs `sync-site-catalog.py` then uploads `site/`

Expected URL: `https://dadoedo.github.io/grok-bot-marketplace-plugin/`  
Placeholder domain: `grokbots.store`

## Brand / asset slots

| Token | Current |
| --- | --- |
| Short name | `XBots` |
| Domain | `grokbots.store` (placeholder) |
| Mark | `assets/logo.png` (prefer `logo-marketplace.png` if added later) |
| Hero | live `#featured` catalog cards — `hero.png` is not the landing hero |
| OG | `assets/og.png` (real catalog faces on color fields) |

## Honesty (do not water down)

- Discovery / browse only
- Install = `grokbot://` addHref or marketplace URL
- Two feeds: marketplace catalog + X viral/shared templates
- No invented install API
- No xAI / Cursor partnership claim
