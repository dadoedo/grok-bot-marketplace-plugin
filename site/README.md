# Landing site (`site/`)

Static marketing page for the **Grok Bot Marketplace Plugin**.

Working title **XBots** / **xbots.so** is temporary (`xbots.io` is taken — do not claim it). Swap-friendly: search `data-brand`, `.brand-name`, `.brand-domain` in `index.html` / `styles.css`. Copy bank: [`marketing-copy.md`](marketing-copy.md).

Brand files in [`assets/`](assets/): `logo.png`, `hero.png`, `og.png`.

This is a discovery Open Plugin landing page — **not** an installer and **not** an official x.ai product.

## Visual system (mirrors Grok Bot marketplace)

Do **not** restyle this as generic neon SaaS / glassmorphism. Chrome and cards follow [the public marketplace](https://x.ai/bot/marketplace):

- Dark charcoal page, clean sans (Inter), category chips, an **Add** control
- Bot cards use real catalog fields: `name`, `creatorName`, `summary`, `color`, `shape`, `imageUrl` (S3 creator assets on `grok-bot-marketplace-public-assets.s3.amazonaws.com`)
- Avatars are clipped to marketplace **shapes** (`squircle`, `hex`, `pebble`, `teardrop`, `blob`, `tablet`, `cloud`, `wedge`, `dome`, `crystal`, `capsule`, …) via CSS `clip-path` / `border-radius`
- Glow/tint uses the bot’s `color` token (`green`, `violet`, `magenta`, `orange`, `blue`, `cyan`, `gray`, `red`, `black`, `brown`, `yellow`)
- **Catalog avatars win** over generated hero/OG art if they conflict
- Add points at `addHref` (`grokbot://…`) and the name/card at `marketplaceUrl` — never a fake install API

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
Placeholder domain: `xbots.so`

## Brand / asset slots

| Token | Current |
| --- | --- |
| Short name | `XBots` |
| Domain | `xbots.so` (placeholder) |
| Mark | `assets/logo.png` |
| Hero | `assets/hero.png` |
| OG | `assets/og.png` |

## Honesty (do not water down)

- Discovery / browse only
- Install = `grokbot://` addHref or marketplace URL
- Two feeds: marketplace catalog + X viral/shared templates
- No invented install API
- No xAI / Cursor partnership claim
