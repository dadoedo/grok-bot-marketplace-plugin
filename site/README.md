# Landing site (`site/`)

Static marketing page for the **Grok Bot Marketplace Plugin**.

Working title **XBots** is temporary (domain TBD; `xbots.io` is taken). Swap-friendly: search `data-brand`, `.brand-name`, and the `BRAND SWAP` comment in `index.html` / `styles.css`.

This is a discovery Open Plugin landing page — **not** an installer and **not** an official x.ai product.

## Preview locally

From the repo root:

```bash
python3 -m http.server 8080 --directory site
```

Open http://127.0.0.1:8080/

No build step. Vanilla HTML + CSS. Fonts load from Google Fonts.

## GitHub Pages

GitHub’s **Deploy from a branch** UI only offers:

- `/` (repo root) — would mix the plugin tree into the site
- `/docs` — not used here; the site lives in `site/`

**`/site` is not a folder GitHub will serve from that dropdown.** Use Actions instead (workflow shipped at `.github/workflows/pages.yml`):

1. Repo **Settings → Pages**
2. **Source:** GitHub Actions
3. Merge to `main` (or run the workflow manually with **workflow_dispatch**)
4. The Action uploads the `site/` folder

Expected URL: `https://dadoedo.github.io/grok-bot-marketplace-plugin/`

Optional fallback if you refuse Actions: copy `site/*` into `docs/` and set Pages to **Deploy from branch → `/docs`**. Keep one source of truth — do not fork the markup in two folders.

## Brand / asset slots

| Token | Current |
| --- | --- |
| Short name | `XBots` |
| Status | working title |
| Full name | Grok Bot Marketplace Plugin |

When generated art arrives, drop files named in [`assets/README.md`](assets/README.md):

- `assets/hero.png` (1600×900) — replace the CSS collage
- `assets/og.png` (1200×630 PNG) — then retarget `og:image` in `index.html`

## Honesty (do not water down)

Copy on this page must keep:

- Discovery / browse only
- Install = `grokbot://` addHref or marketplace URL
- Two feeds: marketplace catalog + X viral/shared templates
- No invented install API
- No xAI / Cursor partnership claim
