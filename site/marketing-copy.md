# XBots marketing copy

Working product name **XBots**. Placeholder domain **grokbots.store**. Do not claim **xbots.io** (taken). Domain shortlist is provisional — do not buy from this file.

Brand swap: search `data-brand`, `XBots`, `grokbots.store` in `index.html`, `styles.css`, and this file.

Repo: https://github.com/dadoedo/grok-bot-marketplace-plugin  
Publish: [cursor.directory](https://cursor.directory) (`/plugins/new` after merge)

Product truth: Cursor Open Plugin that **discovers** Grok Bots. Not an installer. Install is `grokbot://` addHref or the marketplace URL only. Not an official x.ai or Cursor product.

## Headlines

- Find your next AI teammate.
- Two feeds. One honest plugin.
- The Grok Bot catalog, plus whatever is spreading on X.
- Discovery for Cursor agents — you still tap Add.
- Marketplace listings. Viral shares. Zero fake APIs.

## Subheads / ledes

- A Cursor Open Plugin with two discovery feeds: the public Grok Bot marketplace catalog, and the templates people actually share on X. Agents return cards. You still open Add yourself.
- Browse official x.ai marketplace bots (real names, shapes, creator photos) and recent X posts that share `grokbot://` templates. Read/search only.
- Skills + CLI. Stdlib Python. Hosted grokbots.store feed; `--offline` uses the bundled snapshot.

## Features (site + directory)

1. **Marketplace catalog** — list / search / compare / refresh from public SSR HTML + `data/catalog.json`. Cards include `name`, `creator`, `description`, `categories`, `addHref`, `marketplaceUrl`.
2. **X viral feed** — recent search for marketplace URLs and `grokbot://` shares. `x-viral` ranks by engagement. `--demo` / `X_DEMO=1` works with no key.
3. **Honest install** — no marketplace REST install API. Open the deep link in Grok Bot or the marketplace page.
4. **Hosted feed** — plugin reads `https://grokbots.store/feed.json`. Operators keep `X_BEARER_TOKEN` on hetzner-prod only. Never commit `.env`.
5. **Agent-ready** — skills `grok-bot-marketplace` and `grok-bot-x-feed`; CLI `python3 scripts/catalog.py`.

## CTAs

- Primary: View the repo → https://github.com/dadoedo/grok-bot-marketplace-plugin
- Secondary: Install via cursor.directory → https://cursor.directory (listing after publish)
- Local: `ln -s "$(pwd)" ~/.cursor/plugins/local/grok-bot-marketplace`

## Honesty / disclaimer

Cursor Open Plugin for discovery — not an installer, not a store, not an official x.ai or Cursor product. Add still means a `grokbot://` deep link or the marketplace URL. Independent MIT project. Working title XBots / grokbots.store is temporary.

## Social blurbs

**OG / Twitter title:** XBots — Find your next AI teammate  
**OG / Twitter description:** Browse the Grok Bot marketplace catalog and viral grokbot:// shares on X. Cursor discovery plugin — not an installer.  
**Image:** `site/assets/og.png` (1280×720)

**X / LinkedIn (short):**  
XBots: a Cursor plugin that finds Grok Bots two ways — the official marketplace catalog, and templates going around on X. Discovery only. You still open Add. github.com/dadoedo/grok-bot-marketplace-plugin

**X (tighter):**  
Two feeds for Grok Bots: marketplace catalog + viral shares on X. No fake install API. XBots (working title) → github.com/dadoedo/grok-bot-marketplace-plugin

## Product Hunt

**Name:** XBots  
**Tagline:** Discover Grok Bots from the marketplace and from X  
**Description:**  
XBots is a Cursor Open Plugin so agents can browse public Grok Bots from grokbots.store (official marketplace catalog + viral shares). It does not install bots — it returns the deep link and marketplace URL. No X API key for users.

**First comment sketch:**  
Built this because there is no public marketplace install API — and inventing one would be a lie. The plugin reads a public grokbots.store feed. Operators refresh marketplace HTML + X on hetzner-prod. Happy to hear which bots you actually want agents to find first.

## Meta

```
title: XBots — Find your next AI teammate
description: XBots is a Cursor Open Plugin for discovering Grok Bots: the official marketplace catalog plus viral template shares on X. Discovery only — not an installer.
```

## Domains (provisional — do not buy)

RDAP-free shortlist (not purchased from this repo):

| Domain | Note |
| --- | --- |
| **grokbots.store** | Default placeholder in copy |
| findxbots.com | |
| grokxbots.com | |
| getxbots.com | |
| findgrokbots.com | |
| xbots.io | **Taken — do not claim** |

Until a domain is locked, ship GitHub Pages and keep `grokbots.store` labeled as a working title.
