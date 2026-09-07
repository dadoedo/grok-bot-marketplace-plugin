---
name: grok-bot-marketplace
description: Browse, search, filter, and compare public Grok Bots from the hosted grokbots.store feed (official marketplace catalog). There is no public marketplace REST or install API — return addHref plus the marketplace URL. Users do not need an X API key. For viral shares, use grok-bot-x-feed (also from the hosted feed).
license: MIT
compatibility: Requires Python 3.10+. Default data source is https://grokbots.store/feed.json (override GROKBOTS_FEED_URL). Offline fallback is data/feed.json / data/catalog.json. X_BEARER_TOKEN is not required.
metadata:
  author: dadoedo
  version: "0.4.0"
---

# Grok Bot marketplace catalog

Help the user browse public [Grok Bots](https://x.ai/bot/marketplace) via the **hosted feed** at [grokbots.store/feed.json](https://grokbots.store/feed.json).

For **viral/shared templates**, switch to `grok-bot-x-feed` (same feed’s `xViral` section). Do **not** ask the user to create an X API app.

## Hard rules

1. **No install API.** There is no public Bot marketplace REST API. Do not invent list/install endpoints. Do not POST, PUT, or guess URLs under `x.ai` to install a bot.
2. **Install is a deep link.** Each bot has `addHref` like `grokbot://app/v1/bot-template?id=…`. Return `addHref` and `marketplaceUrl`. Tell the user to open those in Grok Bot (or the marketplace page).
3. **Catalog source.** Default: hosted `https://grokbots.store/feed.json` (`marketplace` object). Fallback: `data/feed.json` then `data/catalog.json`. `--offline` skips the network. `ops/refresh_feed.py` is for hetzner-prod operators, not end users.
4. **Do not search X live from this skill.** Use `grok-bot-x-feed` (hosted `xViral`).
5. **Do not store X API secrets.** The published plugin never needs `X_BEARER_TOKEN`.

## Workflow

Work from the **plugin root** (the directory that contains `plugin.json`).

```bash
python3 scripts/catalog.py list --with-categories
python3 scripts/catalog.py list --category Engineering
python3 scripts/catalog.py search "seo brief"
python3 scripts/catalog.py search "outbound" --format text
python3 scripts/catalog.py categories
python3 scripts/catalog.py show researchy --format text
python3 scripts/catalog.py compare researchy tinkabot
python3 scripts/catalog.py list --offline
```

Default `--format` is `json`. Put `--format text` **after** the subcommand.

If Python cannot run, read `data/feed.json` → `marketplace.bots` (or `data/catalog.json`) and filter it yourself.

## Output contract

Every bot you present MUST include `name`, `creator`, `description`, `categories`, `installCount` (return `0` honestly), `marketplaceUrl`, `addHref`. Also include `id`, `handle`, and `feed: marketplace` when available.

> Install is not an API call. Open `addHref` in Grok Bot, or open `marketplaceUrl` in a browser.
